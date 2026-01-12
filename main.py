# main.py
import socket
import threading
import sys
import json
import numpy as np
import shutil

from ui import AppUI
from network import send_packet, recv_packet
from video_stream import VideoStream
from video_decoder import decode_h263_bytes_to_bgr
from audio_player import AudioPlayer
from file_transfer import FileTransfer
from chat import ChatManager

from config import (
    SERVER_PORT,
    TYPE_VIDEO, TYPE_TEXT, TYPE_IMAGE,
    TYPE_FILE_HDR, TYPE_FILE_CHUNK, TYPE_FILE_END,
    TYPE_AUDIO
)
from config import ffmpeg_available


# ffmpeg 확인용 콘솔 출력
if shutil.which("ffmpeg") is None:
    print("⚠ ffmpeg not found in PATH")
else:
    print("ffmpeg OK:", shutil.which("ffmpeg"))


class App:
    def __init__(self):
        # 상태
        self.sock = None
        self.running = False
        self.recv_thread = None

        # 품질 / 필터
        self.compression_quality = 50
        self.filter_mode = "None"
        self.use_h263 = ffmpeg_available()

        # UI
        self.ui = AppUI(self)

        # 서브 모듈
        self.video = VideoStream(self)
        self.audio_player = AudioPlayer()
        self.file_transfer = FileTransfer(self)
        self.chat = ChatManager(self)

        if not self.use_h263:
            self.chat.append_system("ffmpeg not found — falling back to MJPEG (JPEG) transport.")

    # -----------------------
    # UI 헬퍼
    # -----------------------
    def show_local(self, frame):
        self.ui.root.after(0, self.ui.show_local_bgr, frame.copy())

    def clear_local(self):
        self.ui.root.after(0, self.ui.clear_local)

    def show_remote_from_bgr(self, frame_bgr):
        import cv2
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        ok, jpg = cv2.imencode(".jpg", rgb)
        if ok:
            self.ui.root.after(0, self.ui.show_remote_jpeg, jpg.tobytes())

    def show_remote_jpeg(self, jpeg_bytes: bytes):
        self.ui.root.after(0, self.ui.show_remote_jpeg, jpeg_bytes)

    def system_msg(self, text: str):
        self.chat.append_system(text)

    def show_error(self, title, msg):
        from tkinter import messagebox
        messagebox.showerror(title, msg)

    def update_transfer_status(self, pct, sent_bytes, total_bytes, speed_mbps):
        def _update():
            self.ui.transfer_label.config(
                text=f"[{pct:.1f}%]  {sent_bytes/1024/1024:.2f} MB / "
                    f"{total_bytes/1024/1024:.2f} MB  ({speed_mbps:.2f} MB/s)"
            )
        self.ui.root.after(0, _update)

    # -----------------------
    # Network
    # -----------------------
    def connect_server(self):
        ip = self.ui.ip_entry.get().strip()
        if not ip:
            from tkinter import messagebox
            messagebox.showwarning("Input", "서버 IP를 입력하세요.")
            return
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((ip, SERVER_PORT))
            self.sock.settimeout(None)
            self.system_msg(f"Connected to {ip}:{SERVER_PORT}")
            self.running = True
            self.recv_thread = threading.Thread(target=self.recv_loop, daemon=True)
            self.recv_thread.start()
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Connect failed", str(e))
            self.sock = None

    def disconnect_server(self):
        self.system_msg("Disconnecting...")
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

    def send_bytes(self, ttype, payload: bytes):
        if not self.sock:
            return False
        return send_packet(self.sock, ttype, payload)

    def recv_loop(self):
        try:
            while self.running and self.sock:
                ttype, payload = recv_packet(self.sock)
                if not ttype:
                    break

                if ttype == TYPE_VIDEO:
                    # 스트리밍 비디오 수신
                    self.show_remote_jpeg(payload)

                elif ttype == TYPE_TEXT:
                    text = payload.decode("utf-8", errors="replace")
                    self.chat.handle_incoming(text)

                elif ttype == TYPE_IMAGE:
                    # 이미지 파일 수신 표시
                    self.show_remote_jpeg(payload)

                elif ttype == TYPE_FILE_HDR:
                    self.file_transfer.handle_file_header(payload)

                elif ttype == TYPE_FILE_CHUNK:
                    self.file_transfer.handle_file_chunk(payload)

                elif ttype == TYPE_FILE_END:
                    self.file_transfer.handle_file_end()

                elif ttype == TYPE_AUDIO:
                    self.audio_player.play(payload)

        except Exception as e:
            print("Receive loop error:", e)
        finally:
            print("Receiver exiting")
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass
                self.sock = None
            self.running = False
            self.system_msg("Disconnected from server")

    # Camera / Audio / File / Chat / UI 콜백
    def start_camera(self):
        self.video.start_camera()

    def stop_camera(self):
        self.video.stop_camera()
    
    def start_audio(self):
        self.video.audio.start()

    def stop_audio(self):
        self.video.audio.stop()


    def load_file(self):
        """
        load_file → 로컬 표시 + 원격 표시
        Image → 즉시 화면 표시
        Video → broadcast(로컬 재생 + 원격 스트리밍)
        """
        mode = self.ui.combo_mode.get()
        from tkinter import filedialog, messagebox
        import cv2, os, numpy as np

        # IMAGE FILE
        if mode == "Image File":
            path = filedialog.askopenfilename(
                filetypes=[("Image", "*.jpg *.jpeg *.png *.bmp *.webp")]
            )
            if not path:
                return

            try:
                with open(path, "rb") as f:
                    img_bytes = f.read()
                arr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            except Exception as e:
                messagebox.showerror("Error", f"이미지 로드 실패\n{e}")
                return

            if img is None:
                messagebox.showerror("Error", "이미지 디코딩 실패")
                return

            # --- LOCAL 표시 ---
            self.show_local(img)

            # --- REMOTE 전송 ---
            if self.sock:
                ok, jpg = cv2.imencode(
                    ".jpg", img,
                    [cv2.IMWRITE_JPEG_QUALITY, self.compression_quality]
                )
                if ok:
                    self.send_bytes(TYPE_IMAGE, jpg.tobytes())

            self.system_msg(f"이미지 로드 완료: {os.path.basename(path)}")
            return

        # VIDEO FILE → BROADCAST (local + remote)
        elif mode == "Video File":
            path = filedialog.askopenfilename(
                filetypes=[("Video", "*.mp4 *.avi *.mkv *.mov")]
            )
            if not path:
                return

            self.video.play_video_file_broadcast(path)
            return

        else:
            messagebox.showinfo("Load File", "Image File 또는 Video File 모드를 선택하세요.")
            return

    def compress_and_send_with_quality(self):
        self.file_transfer.compress_and_send_with_quality()

    def compress_and_send_h263_video(self):
        self.file_transfer.send_h263_video()

    # Chat
    def send_chat(self):
        text = self.ui.chat_entry.get().strip()
        self.chat.send(text)

    def on_enter_pressed(self, event):
        self.send_chat()
        return "break"

    # UI callbacks
    def on_quality_progress_changed(self, *args):
        try:
            val = int(self.ui.progress_var.get())
            val = max(10, min(val, 95))
            self.compression_quality = val
            self.ui.scale_quality.set(val)
            self.ui.status_bar.config(text=f"Quality set to {val}")
        except Exception as e:
            print("progress update error:", e)

    def update_quality(self, val):
        try:
            self.compression_quality = int(val)
            self.ui.status_bar.config(text=f"Quality set to {self.compression_quality}")
        except:
            pass

    def change_filter(self, event):
        self.filter_mode = self.ui.combo_filter.get()

    def close(self):
        self.system_msg("Closing application...")
        self.running = False
        try:
            if self.video.capture_thread and self.video.capture_thread.is_alive():
                self.video.capture_thread.join(timeout=0.5)
        except:
            pass
        try:
            if self.recv_thread and self.recv_thread.is_alive():
                self.recv_thread.join(timeout=0.5)
        except:
            pass
        try:
            self.video.stop_camera()
        except:
            pass
        try:
            if self.sock:
                self.sock.close()
        except:
            pass
        try:
            self.ui.root.destroy()
        except:
            pass
        sys.exit(0)


if __name__ == '__main__':
    app = App()
    app.ui.root.mainloop()
