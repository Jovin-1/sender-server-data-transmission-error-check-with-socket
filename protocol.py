# protocol.py
"""
Utilities for message framing, sending/receiving JSON over TCP,
and CRC‑32 calculation.
"""
import json
import struct
import zlib
from typing import Any, Dict

# ----------------------------------------------------------------------
# Framing helpers (4‑byte big‑endian length header)
# ----------------------------------------------------------------------
def send_message(sock, message: Dict[str, Any]) -> None:
    """Serialize *message* to JSON, prefix with length, and send."""
    data = json.dumps(message).encode("utf-8")
    length = struct.pack("!I", len(data))
    sock.sendall(length + data)


def recv_all(sock, n: int) -> bytes:
    """Receive exactly *n* bytes from *sock*."""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Socket closed while receiving data")
        buf += chunk
    return buf


def receive_message(sock) -> Dict[str, Any]:
    """Read a length‑prefixed JSON message from *sock*."""
    header = recv_all(sock, 4)
    (msg_len,) = struct.unpack("!I", header)
    payload = recv_all(sock, msg_len)
    return json.loads(payload.decode("utf-8"))

# ----------------------------------------------------------------------
# CRC‑32 helper
# ----------------------------------------------------------------------
def crc32(data: str) -> int:
    """Return CRC‑32 of the UTF‑8 encoded *data*."""
    return zlib.crc32(data.encode("utf-8")) & 0xffffffff
