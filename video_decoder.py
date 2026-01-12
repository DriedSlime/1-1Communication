# video_decoder.py
import subprocess
import numpy as np
import cv2

from config import ffmpeg_available

def decode_h263_bytes_to_bgr(data_bytes):
    """
    H.263 bitstream을 단일 BGR frame으로 디코딩.
    원래 client.py의 decode_h263_bytes_to_bgr 그대로 분리.
    """
    if not ffmpeg_available():
        return None
    try:
        proc = subprocess.Popen(
            [
                "ffmpeg", "-loglevel", "error",
                "-f", "h263", "-i", "pipe:0",
                "-f", "rawvideo", "-pix_fmt", "bgr24", "pipe:1"
            ],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        out, err = proc.communicate(input=data_bytes, timeout=1.0)
        if not out:
            return None

        for w, h in [(640, 480), (320, 240), (1280, 720), (480, 360)]:
            if len(out) == w * h * 3:
                arr = np.frombuffer(out, dtype=np.uint8).reshape((h, w, 3))
                return arr

        return None
    except Exception as e:
        print("decode_h263 error:", e)
        return None
