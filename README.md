# 1-1Communication

이 프로젝트는 한림대학교 멀티미디어개론 수업에서 진행한 **실시간 멀티미디어 스트리밍 시스템**입니다.
카메라 영상, 이미지, 비디오 파일, 그리고 마이크 오디오를 네트워크를 통해 송수신할 수 있는 간단한 클라이언트 애플리케이션입니다.

---

## 주요 기능

* **카메라 실시간 스트리밍 (JPEG 기반)**
* **비디오 파일 재생 (로컬 / 원격 송출)**
* **이미지 파일 전송 + 압축 품질 분석(PSNR / SSIM)**
* **비디오 파일 전송 (H.263 인코딩)**
* **실시간 마이크 오디오 스트리밍 (PCM, PyAudio)**
* **TCP 기반 커스텀 패킷 프로토콜**
* **텍스트 채팅**
* **Tkinter 기반 GUI**

---

## 프로젝트 구조

```
Project/
├── main.py            # 애플리케이션 핵심 컨트롤러, 수신 루프
├── server.py          # TCP 멀티 클라이언트 중계 서버
├── network.py         # 커스텀 패킷 송수신 로직
├── config.py          # 프로토콜 정의 및 상수
├── ui.py              # Tkinter GUI
├── chat.py            # 텍스트 채팅 처리
├── file_transfer.py   # 이미지/비디오/파일 전송
├── video_stream.py    # 카메라/비디오 스트리밍 + 오디오 캡처
├── video_encoder.py   # H.263 비디오 인코딩
├── video_decoder.py   # 비디오 디코딩
├── audio_player.py    # 수신 오디오 재생
├── utils.py           # 공용 유틸리티
├── extra.py           # 보조/실험용 기능
```

---

## 커스텀 패킷 프로토콜 구조

```text
[ Type (4 bytes) ][ Payload Size (8 bytes) ][ Payload ]
```
```python
HEADER_FMT = '!4sQ'
```

### 패킷 타입 (config.py)

```python
| `TYPE_VIDEO`      | JPEG 영상 프레임 |
| `TYPE_AUDIO`      | PCM 오디오 데이터 |
| `TYPE_IMAGE`      | 이미지 파일      |
| `TYPE_FILE_HDR`   | 파일 메타데이터    |
| `TYPE_FILE_CHUNK` | 파일 데이터      |
| `TYPE_FILE_END`   | 파일 종료       |
| `TYPE_TEXT`       | 채팅 메시지      |
```

---

## 오디오 스트리밍 방식

* PyAudio 기반 마이크 캡처
* PCM 16bit / Mono / 16kHz
* Chunk 단위 TCP 전송
* 수신 즉시 재생 (Low Latency)

---

## 📷 비디오 스트리밍 방식

* 실시간 스트리밍
* OpenCV 캡처
* JPEG 인코딩
* 프레임 단위 전송
* 파일 전송
* ffmpeg 기반 H.263 인코딩
* 파일 크기 비교
* PSNR / SSIM 계산

```python
cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, Q])
```

---

### 1. 필수 라이브러리 설치

```bash
pip install opencv-python pyaudio numpy
```

---

### 2. 서버 주소 설정

`config.py`

```python
DEFAULT_SERVER_HOST = '서버 IP'
SERVER_PORT = 9999
```

---

### 3. 서버 실행

```bash
python server.py
```

---

### 3. 클라이언 실행

```bash
python main.py
```
동일한 네트워크 환경에서 config.py의 서버 IP를 맞춰야 함.
---

## 주의사항

* 하나의 **카메라는 동시에 하나의 프로세스만 사용 가능**
* 동일 PC에서 2개 클라이언트 실행 시 카메라 충돌 발생 가능
* 오디오/비디오는 TCP 기반 → 지연(latency) 발생 가능

---

### 실행 화면

<img src="https://github.com/user-attachments/assets/4879949d-ba36-4b8b-b7fe-a7f95a272c7e" />


