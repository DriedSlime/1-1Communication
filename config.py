# config.py
import struct
import shutil

# -----------------------
# 기본 설정
# -----------------------
DEFAULT_SERVER_HOST = '192.168.50.176'
SERVER_PORT = 9999

# -----------------------
# 패킷 헤더
# -----------------------
HEADER_FMT = '!4sQ'
HEADER_SIZE = struct.calcsize(HEADER_FMT)

# -----------------------
# 패킷 타입(Constant)
# -----------------------
TYPE_VIDEO      = b'VID0'
TYPE_VIDEO_H263 = b'VH26'
TYPE_FILE_HDR   = b'FHD0'
TYPE_FILE_CHUNK = b'FCH0'
TYPE_FILE_END   = b'FEND'
TYPE_TEXT       = b'TEX0'
TYPE_IMAGE      = b'IMG0'
TYPE_AUDIO      = b'AUD0'

# -----------------------
# ffmpeg 체크
# -----------------------
def ffmpeg_available():
    return shutil.which("ffmpeg") is not None


