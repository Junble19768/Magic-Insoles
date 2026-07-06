"""Device binary frame: CRC16-Modbus and TCP stream parser."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import Enum, auto

SOF_1 = 0xA5
SOF_2 = 0x5A
HEADER_SIZE = 8  # SOF(2) + seq(2) + data_type(2) + data_length(2)


def crc16_modbus(data: bytes) -> int:
    """CRC16-Modbus over *data* (same algorithm as serial_bridge_sample)."""
    crc16 = 0xFFFF
    for byte in data:
        crc16 ^= byte
        for _ in range(8):
            if crc16 & 0x01:
                crc16 = (crc16 >> 1) ^ 0xA001
            else:
                crc16 >>= 1
    return crc16 & 0xFFFF


@dataclass(frozen=True)
class DeviceFrame:
    seq: int
    data_type: int
    payload: bytes


class ParserState(Enum):
    WAIT_SOF1 = auto()
    WAIT_SOF2 = auto()
    HEADER = auto()
    PAYLOAD = auto()
    CRC = auto()


class FrameParser:
    """Incremental TCP stream parser with sticky/split packet handling."""

    def __init__(self, max_frame_bytes: int = 8192) -> None:
        self._max_frame_bytes = max_frame_bytes
        self._state = ParserState.WAIT_SOF1
        self._header_buf = bytearray()
        self._payload_buf = bytearray()
        self._expected_payload_len = 0
        self._crc_buf = bytearray()

    def feed(self, chunk: bytes) -> list[DeviceFrame]:
        frames: list[DeviceFrame] = []
        for byte in chunk:
            frame = self._feed_byte(byte)
            if frame is not None:
                frames.append(frame)
        return frames

    def _feed_byte(self, byte: int) -> DeviceFrame | None:
        if self._state == ParserState.WAIT_SOF1:
            if byte == SOF_1:
                self._header_buf = bytearray([byte])
                self._state = ParserState.WAIT_SOF2
            return None

        if self._state == ParserState.WAIT_SOF2:
            if byte == SOF_2:
                self._header_buf.append(byte)
                self._state = ParserState.HEADER
            elif byte == SOF_1:
                self._header_buf = bytearray([SOF_1])
            else:
                self._state = ParserState.WAIT_SOF1
            return None

        if self._state == ParserState.HEADER:
            self._header_buf.append(byte)
            if len(self._header_buf) == HEADER_SIZE:
                _, _, data_length = struct.unpack_from("<HHH", self._header_buf, 2)
                if data_length > self._max_frame_bytes:
                    self._reset()
                    return None
                self._expected_payload_len = data_length
                self._payload_buf = bytearray()
                self._state = (
                    ParserState.PAYLOAD if data_length > 0 else ParserState.CRC
                )
            return None

        if self._state == ParserState.PAYLOAD:
            self._payload_buf.append(byte)
            if len(self._payload_buf) >= self._expected_payload_len:
                self._crc_buf = bytearray()
                self._state = ParserState.CRC
            return None

        if self._state == ParserState.CRC:
            self._crc_buf.append(byte)
            if len(self._crc_buf) < 2:
                return None

            wire_crc = (self._crc_buf[0] << 8) | self._crc_buf[1]
            frame_bytes = bytes(self._header_buf) + bytes(self._payload_buf)
            expected_crc = crc16_modbus(frame_bytes)

            seq, data_type, _ = struct.unpack_from("<HHH", self._header_buf, 2)
            payload = bytes(self._payload_buf)
            self._reset()

            if wire_crc != expected_crc:
                return None

            return DeviceFrame(seq=seq, data_type=data_type, payload=payload)

        return None

    def _reset(self) -> None:
        self._state = ParserState.WAIT_SOF1
        self._header_buf = bytearray()
        self._payload_buf = bytearray()
        self._crc_buf = bytearray()
        self._expected_payload_len = 0


def build_frame(seq: int, data_type: int, payload: bytes) -> bytes:
    """Serialize a device frame (for tests and simulate_ingest)."""
    header = struct.pack(
        "<BBHHH",
        SOF_1,
        SOF_2,
        seq & 0xFFFF,
        data_type & 0xFFFF,
        len(payload) & 0xFFFF,
    )
    body = header + payload
    crc = crc16_modbus(body)
    return body + bytes([(crc >> 8) & 0xFF, crc & 0xFF])
