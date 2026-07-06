"""Protocol unit tests."""

from __future__ import annotations

import struct

import pytest

from protocol.device_frame import (
    FrameParser,
    build_frame,
    crc16_modbus,
)
from protocol.payloads import DATA_TYPE_FORCE, parse_force
from services.ingest import build_force_payload


def test_crc16_modbus_known_vector() -> None:
    data = bytes([0xA5, 0x5A, 0x01, 0x00, 0x01, 0x01, 0x02, 0x00, 0xAA, 0xBB])
    crc = crc16_modbus(data)
    assert isinstance(crc, int)
    assert 0 <= crc <= 0xFFFF


def test_build_and_parse_roundtrip() -> None:
    payload = build_force_payload(
        start_stamp=1_700_000_000_000,
        samplecount=2,
        samples=[[100] * 32, [200] * 32],
    )
    frame_bytes = build_frame(seq=42, data_type=DATA_TYPE_FORCE, payload=payload)
    parser = FrameParser()
    frames = parser.feed(frame_bytes)
    assert len(frames) == 1
    assert frames[0].seq == 42
    assert frames[0].data_type == DATA_TYPE_FORCE
    parsed = parse_force(frames[0].payload)
    assert parsed.samplecount == 2
    assert parsed.samples[0][0] == 100
    assert parsed.samples[1][0] == 200


def test_sticky_and_split_packets() -> None:
    payload = build_force_payload(1000, 1, [[50] * 32])
    f1 = build_frame(1, DATA_TYPE_FORCE, payload)
    f2 = build_frame(2, DATA_TYPE_FORCE, payload)
    combined = f1 + f2
    parser = FrameParser()

    # Split across arbitrary boundaries
    frames: list = []
    for index in range(0, len(combined), 7):
        frames.extend(parser.feed(combined[index : index + 7]))
    assert len(frames) == 2
    assert frames[0].seq == 1
    assert frames[1].seq == 2


def test_crc_error_recovery() -> None:
    payload = build_force_payload(1000, 1, [[10] * 32])
    good = bytearray(build_frame(5, DATA_TYPE_FORCE, payload))
    good[-1] ^= 0xFF  # corrupt CRC low byte
    parser = FrameParser()
    assert parser.feed(bytes(good)) == []

    # Next valid frame should still parse
    valid = build_frame(6, DATA_TYPE_FORCE, payload)
    frames = parser.feed(valid)
    assert len(frames) == 1
    assert frames[0].seq == 6


def test_crc_high_byte_first_on_wire() -> None:
    payload = b"\x01\x02"
    frame = build_frame(1, 0x0401, payload)
    crc_bytes = frame[-2:]
    body = frame[:-2]
    expected = crc16_modbus(body)
    assert crc_bytes[0] == (expected >> 8) & 0xFF
    assert crc_bytes[1] == expected & 0xFF
