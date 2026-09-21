"""
error_detection.py
==================
Error Detection Module
Implements VRC, LRC, and CRC algorithms used during data transmission.

Author : Systems Architecture Simulation
Purpose: Provide pluggable error-detection strategies for the Middleman
         to validate data integrity upon receipt.
"""

from __future__ import annotations
import functools
from enum import Enum, auto


# ---------------------------------------------------------------------------
# Enum: Supported error-detection schemes
# ---------------------------------------------------------------------------
class EDCScheme(Enum):
    VRC = auto()   # Vertical Redundancy Check  (per-byte even parity)
    LRC = auto()   # Longitudinal Redundancy Check (row parity byte)
    CRC = auto()   # Cyclic Redundancy Check (CRC-32 polynomial)


# ===========================================================================
# VRC – Vertical Redundancy Check
# ===========================================================================
class VRC:
    """
    Vertical Redundancy Check (even parity per byte).

    For every byte in the payload, count the number of 1-bits.
    If odd → set parity bit to 1 (making total 1-bits even).
    Appends one parity byte per data byte.

    Transmission format: [b0, p0, b1, p1, ..., bn, pn]
    """

    @staticmethod
    def compute_parity_byte(byte: int) -> int:
        """Return 0x00 or 0x01 so that byte XOR parity has even parity."""
        ones = bin(byte).count("1")
        return 0 if ones % 2 == 0 else 1

    @staticmethod
    def encode(data: bytes) -> bytes:
        """Interleave each data byte with its VRC parity byte."""
        result = bytearray()
        for b in data:
            result.append(b)
            result.append(VRC.compute_parity_byte(b))
        return bytes(result)

    @staticmethod
    def verify(frame: bytes) -> tuple[bool, bytes]:
        """
        Verify the VRC-encoded frame.

        Returns (is_valid, recovered_data).
        is_valid = True iff every (data_byte XOR parity_byte) has even parity.
        """
        if len(frame) % 2 != 0:
            return False, b""

        recovered = bytearray()
        for i in range(0, len(frame), 2):
            data_byte   = frame[i]
            parity_byte = frame[i + 1]
            total_ones  = bin(data_byte).count("1") + bin(parity_byte).count("1")
            if total_ones % 2 != 0:
                return False, b""
            recovered.append(data_byte)
        return True, bytes(recovered)


# ===========================================================================
# LRC – Longitudinal Redundancy Check
# ===========================================================================
class LRC:
    """
    Longitudinal Redundancy Check.

    Treats the payload as rows of fixed block_size bytes.
    XORs all rows column-wise to produce a single parity row.
    Appends that parity row at the end of the frame.

    Transmission format: [data_bytes ... | lrc_block (block_size bytes)]
    """

    DEFAULT_BLOCK = 8   # bytes per row (configurable)

    @staticmethod
    def encode(data: bytes, block_size: int = DEFAULT_BLOCK) -> bytes:
        """Pad data to a multiple of block_size, compute LRC row, append it."""
        # Pad with zeros if needed
        rem  = len(data) % block_size
        padded = data + b"\x00" * (block_size - rem if rem else 0)

        lrc_block = bytearray(block_size)
        for i in range(0, len(padded), block_size):
            row = padded[i:i + block_size]
            for j in range(block_size):
                lrc_block[j] ^= row[j]

        return padded + bytes(lrc_block)

    @staticmethod
    def verify(frame: bytes, block_size: int = DEFAULT_BLOCK) -> tuple[bool, bytes]:
        """
        Verify LRC frame.

        Returns (is_valid, recovered_data_without_padding_and_lrc).
        """
        if len(frame) < block_size or len(frame) % block_size != 0:
            return False, b""

        payload   = frame[:-block_size]
        recv_lrc  = frame[-block_size:]

        # Re-compute LRC over payload
        computed = bytearray(block_size)
        for i in range(0, len(payload), block_size):
            row = payload[i:i + block_size].ljust(block_size, b"\x00")
            for j in range(block_size):
                computed[j] ^= row[j]

        is_valid = (bytes(computed) == recv_lrc)
        return is_valid, payload.rstrip(b"\x00") if is_valid else b""


# ===========================================================================
# CRC – Cyclic Redundancy Check (CRC-32)
# ===========================================================================
class CRC:
    """
    CRC-32 (IEEE 802.3 polynomial: 0xEDB88320 reflected).

    Appends 4-byte CRC checksum (big-endian) at the end of the frame.

    Transmission format: [data_bytes ... | 4-byte CRC]
    """

    POLYNOMIAL = 0xEDB88320   # Reflected CRC-32 polynomial

    # Pre-compute lookup table (256 entries)
    _TABLE: list[int] = []

    @classmethod
    def _build_table(cls) -> None:
        if cls._TABLE:
            return
        for i in range(256):
            crc = i
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ cls.POLYNOMIAL
                else:
                    crc >>= 1
            cls._TABLE.append(crc)

    @classmethod
    def compute(cls, data: bytes) -> int:
        """Return CRC-32 integer for the given bytes."""
        cls._build_table()
        crc = 0xFFFFFFFF
        for byte in data:
            idx = (crc ^ byte) & 0xFF
            crc = (crc >> 8) ^ cls._TABLE[idx]
        return crc ^ 0xFFFFFFFF

    @classmethod
    def encode(cls, data: bytes) -> bytes:
        """Append 4-byte CRC to data."""
        crc_val = cls.compute(data)
        crc_bytes = crc_val.to_bytes(4, byteorder="big")
        return data + crc_bytes

    @classmethod
    def verify(cls, frame: bytes) -> tuple[bool, bytes]:
        """
        Verify CRC-32 frame.

        Returns (is_valid, original_data_without_crc).
        """
        if len(frame) < 4:
            return False, b""

        payload  = frame[:-4]
        recv_crc = int.from_bytes(frame[-4:], byteorder="big")
        calc_crc = cls.compute(payload)

        is_valid = (calc_crc == recv_crc)
        return is_valid, payload if is_valid else b""


# ===========================================================================
# Factory – resolve scheme name to encoder/decoder pair
# ===========================================================================
def get_codec(scheme: EDCScheme):
    """Return (encode_fn, verify_fn) for the requested EDC scheme."""
    mapping = {
        EDCScheme.VRC: (VRC.encode, VRC.verify),
        EDCScheme.LRC: (LRC.encode, LRC.verify),
        EDCScheme.CRC: (CRC.encode, CRC.verify),
    }
    return mapping[scheme]
