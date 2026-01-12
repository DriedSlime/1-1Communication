# video_encoder.py
import subprocess
import threading

from config import ffmpeg_available

class H263Encoder:
    """
    ffmpeg 프로세스를 띄워서 raw BGR frame -> H.263 bitstream 로 인코딩.
    한 번 start() 후 여러 프레임 encode() 가능.
    """

    def __init__(self):
        self.proc = None
        self.read_thread = None
        self.out_buffer = bytearray()
        self.buf_cond = threading.Condition()

    def start(self, width: int, height: int, fps: int = 20) -> bool:
        if not ffmpeg_available():
            return False
        if self.proc:
            return True

        cmd = [
            "ffmpeg",
            "-loglevel", "error",
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-s", f"{width}x{height}",
            "-r", str(fps),
            "-i", "pipe:0",
            "-c:v", "h263",
            "-f", "h263",
            "pipe:1"
        ]
        try:
            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
        except Exception as e:
            print("Failed to start ffmpeg:", e)
            self.proc = None
            return False

        def reader():
            try:
                while True:
                    data = self.proc.stdout.read(4096)
                    if not data:
                        break
                    with self.buf_cond:
                        self.out_buffer.extend(data)
                        self.buf_cond.notify_all()
            except Exception as e:
                print("h263 stdout reader error:", e)

        self.read_thread = threading.Thread(target=reader, daemon=True)
        self.read_thread.start()
        return True

    def encode(self, frame):
        if not self.proc:
            return None
        try:
            self.proc.stdin.write(frame.tobytes())
            self.proc.stdin.flush()
        except Exception as e:
            print("ffmpeg-write error:", e)
            return None

        with self.buf_cond:
            self.buf_cond.wait(timeout=0.1)
            if not self.out_buffer:
                return None
            data = bytes(self.out_buffer)
            self.out_buffer.clear()
            return data

    def stop(self):
        if not self.proc:
            return
        try:
            try:
                self.proc.stdin.close()
            except Exception:
                pass
            self.proc.terminate()
            self.proc.wait(timeout=1)
        except Exception:
            pass
        self.proc = None
        with self.buf_cond:
            self.out_buffer.clear()
