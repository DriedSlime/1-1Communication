# utils.py
import os
import cv2
import numpy as np
import subprocess

# 한글/공백 경로에서도 안전하게 이미지 읽기
def imread_unicode(path: str):
    try:
        with open(path, "rb") as f:
            data = f.read()
        arr = np.frombuffer(data, np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        return None

# h.263 인코딩
def encode_h263(input_path, output_path, fps=30, resolution="704x576"):
    command = [
        "./ffmpeg/ffmpeg", "-y",
        "-r", str(fps),
        "-i", input_path,
        "-s", resolution,
        "-c:v", "h263",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    try:
        completed = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print("H.263 인코딩 완료:", output_path)
        return True
    except subprocess.CalledProcessError as e:
        print("FFmpeg 인코딩 오류:", e.stderr)
        return False
    except FileNotFoundError:
        print("⚠ ffmpeg 실행 파일을 찾을 수 없습니다. path 확인 필요.")
        return False


# FPS 값이 0이거나 말이 안 되면 기본값 30으로
def safe_fps(raw_fps) -> float:
    try:
        v = float(raw_fps)
        if v < 1 or v > 120:
            return 30.0
        return v
    except Exception:
        return 30.0

# 필터 적용 (원래 VideoChatClient.apply_filter -> 함수로 분리)
def apply_filter(frame, mode: str):
    try:
        if mode == "Gray":
            g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
        elif mode == "Canny(Edge)":
            g = cv2.Canny(frame, 50, 150)
            return cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
        elif mode == "Inverse":
            return cv2.bitwise_not(frame)
        elif mode == "Blur":
            return cv2.GaussianBlur(frame, (15, 15), 0)
        elif mode == "Face Detect":
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, "User", (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                            (0, 255, 0), 2)
            return frame
    except Exception as e:
        print("Filter error:", e)
    return frame
