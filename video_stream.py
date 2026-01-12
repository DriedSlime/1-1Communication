# video_stream.py
import cv2
import time
import threading
import pyaudio

from config import TYPE_VIDEO, TYPE_AUDIO
from utils import safe_fps, apply_filter

# 오디오 설정
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

# AudioStream : 마이크 캡처 + 서버 전송
class AudioStream:
    def __init__(self, app):
        self.app = app
        self.running = False

        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.thread = None

    def start(self):
        """오디오 스트리밍 시작"""
        if self.running:
            return

        try:
            self.stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
            )
        except Exception as e:
            self.app.system_msg(f"Audio start failed: {e}")
            return

        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        self.app.system_msg("Audio streaming started")

    def _loop(self):
        while self.running:
            try:
                data = self.stream.read(CHUNK, exception_on_overflow=False)
                if self.app.sock:
                    self.app.send_bytes(TYPE_AUDIO, data)
            except Exception as e:
                print("Audio stream error:", e)
                # 오류가 나도 loop를 종료하지만 stop()은 호출하지 않음
                break

        print("Audio loop ended")

    def stop(self):
        """오디오 스트리밍 종료"""
        self.running = False

        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
        except:
            pass

        self.stream = None
        self.app.system_msg("Audio streaming stopped")

    def __del__(self):
        """PyAudio 리소스 해제"""
        try:
            self.audio.terminate()
        except:
            pass

# VideoStream : 카메라 / 비디오 파일 재생 + 송출
class VideoStream:
    def __init__(self, app):
        self.app = app

        self.cap = None
        self.sending = False
        self.thread = None

        self.audio = AudioStream(app)   # 오디오 객체 포함
        self.lock = threading.Lock()

    # 카메라 시작
    def start_camera(self):
        with self.lock:
            if self.cap:
                return

            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.app.show_error("Camera error", "카메라를 열 수 없습니다.")
                self.cap = None
                return

            self.sending = True
            self.thread = threading.Thread(target=self._camera_loop, daemon=True)
            self.thread.start()

            self.app.system_msg("Camera started")

    def _camera_loop(self):
        """카메라 프레임 캡처 + 전송"""
        while self.sending and self.cap:
            ret, frame = self.cap.read()
            if not ret:
                break

            frame = apply_filter(frame, self.app.filter_mode)

            self.app.show_local(frame)
            self._send_frame(frame)

            time.sleep(1 / 20)

        self.stop_camera()

    # 카메라 종료
    def stop_camera(self):
        with self.lock:
            self.sending = False

            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
                self.cap = None

            self.app.clear_local()
            self.app.system_msg("Camera stopped")

    # 비디오 파일 로컬 재생
    def play_video_file_local(self, path):
        with self.lock:
            if self.cap:
                self.stop_camera()

            self.cap = cv2.VideoCapture(path)
            if not self.cap.isOpened():
                self.app.show_error("Error", "비디오 파일을 열 수 없습니다.")
                return

            self.sending = True
            self.thread = threading.Thread(target=self._video_local_loop, daemon=True)
            self.thread.start()

            self.app.system_msg(f"[LOCAL PLAY] {path}")

    def _video_local_loop(self):
        while self.sending and self.cap:
            ret, frame = self.cap.read()
            if not ret:
                break

            self.app.show_local(frame)

            fps = safe_fps(self.cap.get(cv2.CAP_PROP_FPS))
            time.sleep(1 / fps if fps > 0 else 1 / 30)

        self.stop_camera()

    # 비디오 파일 방송 (로컬 + 원격)
    def play_video_file_broadcast(self, path):
        with self.lock:
            if self.cap:
                self.stop_camera()

            self.cap = cv2.VideoCapture(path)
            if not self.cap.isOpened():
                self.app.show_error("Error", "비디오 파일을 열 수 없습니다.")
                return

            self.sending = True
            self.thread = threading.Thread(
                target=self._video_broadcast_loop, daemon=True
            )
            self.thread.start()

            self.app.system_msg(f"[BROADCAST] {path}")

    def _video_broadcast_loop(self):
        while self.sending and self.cap:
            ret, frame = self.cap.read()
            if not ret:
                break

            self.app.show_local(frame)
            self._send_frame(frame)

            time.sleep(1 / 20)

        self.stop_camera()

    # 프레임을 JPEG로 인코딩하여 서버로 전송
    def _send_frame(self, frame):
        if not self.app.sock:
            return

        ok, jpg = cv2.imencode(
            ".jpg", frame,
            [cv2.IMWRITE_JPEG_QUALITY, self.app.compression_quality]
        )

        if ok:
            self.app.send_bytes(TYPE_VIDEO, jpg.tobytes())
