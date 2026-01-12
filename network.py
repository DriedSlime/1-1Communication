# network.py
import socket
from struct import pack, unpack
from typing import Tuple, Optional

from config import HEADER_FMT, HEADER_SIZE

def safe_send_all(sock: socket.socket, data: bytes) -> bool:
    try:
        sock.sendall(data)
        return True
    except Exception as e:
        print("Send failed:", e)
        return False

def send_packet(sock: socket.socket, ttype: bytes, payload: bytes) -> bool:
    if not sock:
        return False
    header = pack(HEADER_FMT, ttype, len(payload))
    return safe_send_all(sock, header + payload)

def recv_all(sock: socket.socket, n: int) -> Optional[bytes]:
    data = b''
    while len(data) < n:
        try:
            packet = sock.recv(n - len(data))
        except Exception as e:
            print("recv error:", e)
            return None
        if not packet:
            return None
        data += packet
    return data

def recv_packet(sock: socket.socket) -> Tuple[Optional[bytes], Optional[bytes]]:
    """
    한 번에 (ttype, payload)를 리턴.
    연결 끊기면 (None, None)
    """
    header = recv_all(sock, HEADER_SIZE)
    if not header:
        return None, None
    ttype, size = unpack(HEADER_FMT, header)
    payload = recv_all(sock, size)
    if payload is None:
        return None, None
    return ttype, payload
