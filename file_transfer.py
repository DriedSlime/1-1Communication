# file_transfer.py
import os
import json
import cv2
import time
import matplotlib.pyplot as plt
import numpy as np

from tkinter import filedialog, messagebox
from extra import compute_psnr, compute_ssim_y

from config import (
    TYPE_FILE_HDR, TYPE_FILE_CHUNK, TYPE_FILE_END,
    TYPE_IMAGE, TYPE_VIDEO, TYPE_VIDEO_H263
)
from utils import imread_unicode, encode_h263
from network import send_packet


class FileTransfer:
    def __init__(self, app):
        self.app = app
        self.incoming = None


    # -------------------------------------------------------
    # 파일 헤더 수신
    # -------------------------------------------------------
    def handle_file_header(self, payload: bytes):
        try:
            meta = json.loads(payload.decode("utf-8"))
            fname = meta.get("filename", "received.bin")
            codec = meta.get("codec")

            if codec == "h263":
                root, ext = os.path.splitext(fname)
                save_name = f"recv_{root}.avi"     
                self.incoming = {
                    "name": save_name,
                    "size": meta.get("filesize"),
                    "received": 0,
                    "fp": open(save_name, "wb"),
                    "codec": "h263",
                }
                self.app.system_msg(f"[수신 시작] H.263 비디오: {save_name}")

            else:
                save_name = f"recv_{fname}"
                self.incoming = {
                    "name": save_name,
                    "size": meta.get("filesize"),
                    "received": 0,
                    "fp": open(save_name, "wb"),
                    "codec": None,
                }
                self.app.system_msg(f"[수신 시작] 파일: {save_name}")

        except Exception as e:
            print("file header parse error:", e)


    # -------------------------------------------------------
    # JPEG 이미지 또는 일반 파일 CHUNK 수신
    # -------------------------------------------------------
    def handle_file_chunk(self, payload: bytes):
        if not self.incoming:
            return

        info = self.incoming

        # 파일 쓰기
        info["fp"].write(payload)
        info["received"] += len(payload)

        # 완료 여부 확인
        if info["size"] is not None and info["received"] >= info["size"]:
            info["fp"].close()
            name = info["name"]
            self.incoming = None
            self.app.system_msg(f"[수신 완료] {name}")

            # 이미지면 화면 표시
            if name.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")):
                img = imread_unicode(name)
                if img is not None:
                    self.app.show_remote_from_bgr(img)


    # -------------------------------------------------------
    # H.263 chunk 수신
    # -------------------------------------------------------
    def handle_h263_chunk(self, payload: bytes):
        if not self.incoming or self.incoming["codec"] != "h263":
            return

        info = self.incoming
        info["fp"].write(payload)
        info["received"] += len(payload)


    # -------------------------------------------------------
    # H.263 종료
    # -------------------------------------------------------
    def handle_file_end(self):
        if self.incoming:
            name = self.incoming["name"]
            try:
                self.incoming["fp"].close()
            except:
                pass

            self.incoming = None
            self.app.system_msg(f"[수신 종료] {name}")


    # -------------------------------------------------------
    # 이미지(JPEG) 전송
    # -------------------------------------------------------
    def compress_and_send_with_quality(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image", "*.jpg *.jpeg *.png *.bmp *.webp")]
        )
        if not path:
            return

        import time
        import matplotlib.pyplot as plt

        Q = self.app.compression_quality

        # 1) 원본 이미지 로드
        original = imread_unicode(path)
        if original is None:
            messagebox.showerror("Error", "이미지 로드 실패")
            return

        self.app.show_local(original.copy())

        # 2) JPEG 압축
        ok, encoded = cv2.imencode(".jpg", original, [cv2.IMWRITE_JPEG_QUALITY, Q])
        if not ok:
            messagebox.showerror("Error", "이미지 압축 실패")
            return

        jpeg_bytes = encoded.tobytes()
        compressed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)

        # 3) PSNR, SSIM 계산
        try:
            psnr_val = compute_psnr(original, compressed)
            ssim_val = compute_ssim_y(original, compressed)
        except Exception:
            psnr_val = ssim_val = 0.0

        # 4) 파일 크기 비교
        original_size = os.path.getsize(path)
        compressed_size = len(jpeg_bytes)

        # 5) 서버 연결 여부 확인
        if not self.app.sock:
            messagebox.showwarning("Not connected", "서버 연결 후 다시 시도하세요.")
            return

        # 전송률을 위한 변수
        timestamps = []
        mbps_log = []

        sent = 0
        CHUNK = 4096
        start_time = time.time()

        # 6) 헤더 전송
        meta = {"filename": os.path.basename(path), "filesize": compressed_size}
        send_packet(self.app.sock, TYPE_FILE_HDR, json.dumps(meta).encode("utf-8"))

        # 7) 실제 파일 전송 (chunk 단위)
        for i in range(0, compressed_size, CHUNK):
            chunk = jpeg_bytes[i:i+CHUNK]
            send_packet(self.app.sock, TYPE_FILE_CHUNK, chunk)
            sent += len(chunk)

            # Mbps 계산
            t = time.time() - start_time
            mbps = (sent * 8 / 1_000_000) / max(t, 0.0001)

            timestamps.append(t)
            mbps_log.append(mbps)

        # 종료 신호
        send_packet(self.app.sock, TYPE_FILE_END, b"")

        # 수신측 화면에도 바로 표시
        send_packet(self.app.sock, TYPE_IMAGE, jpeg_bytes)

        self.app.system_msg(
            f"[전송 완료] 이미지(Q={Q}) {compressed_size} bytes\n"
            f"PSNR={psnr_val:.2f}, SSIM={ssim_val:.4f}"
        )

        fig, axs = plt.subplots(1, 2, figsize=(10, 5))

        # 파일 크기 + PSNR/SSIM
        axs[0].bar(["Original", "Compressed"], [original_size, compressed_size], color=["blue", "orange"])
        axs[0].set_title(
            f"Image Compression (Q={Q})\nPSNR={psnr_val:.2f} dB / SSIM={ssim_val:.4f}",
            fontsize=12
        )
        axs[0].set_ylabel("Bytes")
        axs[0].grid(axis="y", linestyle="--", alpha=0.5)

        # 전송 속도(Mbps)
        axs[1].plot(timestamps, mbps_log, marker='o', color="green")
        axs[1].set_title("Transfer Speed (Mbps)", fontsize=12)
        axs[1].set_xlabel("Time (seconds)")
        axs[1].set_ylabel("Mbps")
        axs[1].grid(True)

        axs[1].set_xlim(left=0)
        plt.tight_layout()
        plt.show()

    # -------------------------------------------------------
    # H.263 비디오 전송
    # -------------------------------------------------------
    def send_h263_video(self):
        path = filedialog.askopenfilename(
            filetypes=[("Video", "*.mp4 *.avi *.mkv *.mov")]
        )
        if not path:
            return

        if not self.app.sock:
            messagebox.showwarning("Not connected", "서버 연결 후 다시 시도하세요.")
            return

        import time
        import matplotlib.pyplot as plt

        # 1) 출력 파일 경로
        compressed_path = path + ".h263.avi"

        # 2) ffmpeg 변환
        ok = encode_h263(path, compressed_path)
        if not ok:
            messagebox.showerror("Error", "H.263 인코딩 실패")
            return

        # 3) 파일 크기 비교
        original_size = os.path.getsize(path)
        compressed_size = os.path.getsize(compressed_path)

        # 4) PSNR / SSIM 계산 (10프레임 샘플링)

        cap_orig = cv2.VideoCapture(path)
        cap_cmp = cv2.VideoCapture(compressed_path)

        total_frames = int(cap_orig.get(cv2.CAP_PROP_FRAME_COUNT))
        sample_indices = np.linspace(0, total_frames - 1, 10).astype(int)

        psnr_list = []
        ssim_list = []

        for idx in sample_indices:
            cap_orig.set(cv2.CAP_PROP_POS_FRAMES, idx)
            cap_cmp.set(cv2.CAP_PROP_POS_FRAMES, idx)

            ret1, f1 = cap_orig.read()
            ret2, f2 = cap_cmp.read()
            if not ret1 or not ret2:
                continue

            psnr_list.append(compute_psnr(f1, f2))
            ssim_list.append(compute_ssim_y(f1, f2))

        cap_orig.release()
        cap_cmp.release()

        mean_psnr = np.mean(psnr_list) if psnr_list else 0
        mean_ssim = np.mean(ssim_list) if ssim_list else 0

        # -----------------------------------------
        # 5) 서버에 메타데이터 전송
        # -----------------------------------------
        meta = {
            "filename": os.path.basename(compressed_path),
            "filesize": compressed_size,
            "codec": "h263",
            "psnr": float(mean_psnr),
            "ssim": float(mean_ssim)
        }
        send_packet(self.app.sock, TYPE_FILE_HDR, json.dumps(meta).encode("utf-8"))

        # -----------------------------------------
        # 6) 파일 CHUNK 전송 + 전송률 로그 저장
        # -----------------------------------------
        CHUNK = 4096
        sent = 0
        timestamps = []
        mbps_log = []

        start_time = time.time()

        with open(compressed_path, "rb") as f:
            while True:
                chunk = f.read(CHUNK)
                if not chunk:
                    break

                send_packet(self.app.sock, TYPE_FILE_CHUNK, chunk)
                sent += len(chunk)

                elapsed = time.time() - start_time
                mbps = (sent * 8 / 1_000_000) / max(elapsed, 0.0001)

                timestamps.append(elapsed)
                mbps_log.append(mbps)

        send_packet(self.app.sock, TYPE_FILE_END, b"")

        self.app.system_msg(
            f"[H.263 전송 완료] {os.path.basename(compressed_path)}\n"
            f"원본 {original_size/1024/1024:.2f}MB → 압축 {compressed_size/1024/1024:.2f}MB\n"
            f"PSNR={mean_psnr:.2f}, SSIM={mean_ssim:.4f}"
        )

        # 7) 그래프 시각화 

        fig, axs = plt.subplots(1, 2, figsize=(10, 5))

        # 파일 크기 + PSNR/SSIM
        axs[0].bar(["Original", "H.263"], [original_size, compressed_size], color=["blue", "orange"])
        axs[0].set_title(
            f"Video Compression (H.263)\nPSNR={mean_psnr:.2f} dB / SSIM={mean_ssim:.4f}",
            fontsize=12
        )
        axs[0].set_ylabel("Bytes")
        axs[0].grid(axis="y", linestyle="--", alpha=0.5)

        # 전송 속도(Mbps)
        axs[1].plot(timestamps, mbps_log, marker='o', color="green")
        axs[1].set_title("H.263 Transfer Speed (Mbps)", fontsize=12)
        axs[1].set_xlabel("Time (seconds)")
        axs[1].set_ylabel("Mbps")
        axs[1].grid(True)

        axs[1].set_xlim(left=0)
        plt.tight_layout()
        plt.show()