"""Unified ingest service for TCP and HTTP paths."""

from __future__ import annotations

import logging
import struct
import time
from typing import Any

from sqlalchemy.orm import Session

from database import (
    DeviceEvent,
    DeviceStatusRow,
    ForceBatch,
    GpsPoint,
    IngestFrame,
    samples_to_json,
)
from protocol.device_frame import DeviceFrame
from protocol.payloads import (
    DATA_TYPE_DEVICE_STATUS,
    DATA_TYPE_EVENT,
    DATA_TYPE_FORCE,
    DATA_TYPE_GPS,
    DATA_TYPE_IMU,
    parse_device_status,
    parse_event,
    parse_force,
    parse_gps,
    parse_imu,
)

logger = logging.getLogger(__name__)


def ingest_frame(frame: DeviceFrame, db: Session) -> None:
    receive_time = time.time()
    try:
        if frame.data_type == DATA_TYPE_FORCE:
            _ingest_force(frame, db, receive_time)
        elif frame.data_type == DATA_TYPE_GPS:
            _ingest_gps(frame, db, receive_time)
        elif frame.data_type == DATA_TYPE_DEVICE_STATUS:
            _ingest_device_status(frame, db, receive_time)
        elif frame.data_type == DATA_TYPE_EVENT:
            _ingest_event(frame, db, receive_time)
        elif frame.data_type == DATA_TYPE_IMU:
            parse_imu(frame.payload)
            logger.debug("IMU frame received but not stored (reserved)")
        else:
            logger.warning("Unknown data_type 0x%04X, frame dropped", frame.data_type)
    except ValueError as exc:
        logger.warning("Payload parse error for 0x%04X: %s", frame.data_type, exc)


def _ingest_force(frame: DeviceFrame, db: Session, receive_time: float) -> None:
    parsed = parse_force(frame.payload)
    row = ForceBatch(
        seq=frame.seq,
        start_stamp=parsed.start_stamp,
        receive_time=receive_time,
        samplecount=parsed.samplecount,
        samples_json=samples_to_json(parsed.samples),
    )
    db.add(row)
    db.commit()


def _ingest_gps(frame: DeviceFrame, db: Session, receive_time: float) -> None:
    parsed = parse_gps(frame.payload)
    row = GpsPoint(
        seq=frame.seq,
        timestamp=parsed.timestamp,
        receive_time=receive_time,
        latitude=parsed.latitude,
        longitude=parsed.longitude,
        altitude=parsed.altitude,
        speed=parsed.speed,
        heading=parsed.heading,
        accuracy=parsed.accuracy,
        fix_type=parsed.fix_type,
        satellite_count=parsed.satellite_count,
    )
    db.add(row)
    db.commit()


def _ingest_device_status(
    frame: DeviceFrame, db: Session, receive_time: float
) -> None:
    parsed = parse_device_status(frame.payload)
    row = DeviceStatusRow(
        seq=frame.seq,
        receive_time=receive_time,
        battery=parsed.battery,
        device_link=parsed.device_link,
    )
    db.add(row)
    db.commit()


def _ingest_event(frame: DeviceFrame, db: Session, receive_time: float) -> None:
    parsed = parse_event(frame.payload)
    for event in parsed.events:
        row = DeviceEvent(
            seq=frame.seq,
            receive_time=receive_time,
            event_id=event.event_id,
            stamp=event.stamp,
            reserved=event.reserved,
        )
        db.add(row)
    db.commit()


def ingest_http_frames(frames: list[IngestFrame], db: Session) -> int:
    """Debug/simulation path: one HTTP frame -> one synthetic Force batch."""
    receive_time = time.time()
    for index, frame in enumerate(frames):
        sample = [max(0, min(65535, p)) for p in frame.pressures]
        row = ForceBatch(
            seq=index,
            start_stamp=int(frame.timestamp * 1000),
            receive_time=receive_time,
            samplecount=1,
            samples_json=samples_to_json([sample]),
        )
        db.add(row)
    db.commit()
    return len(frames)


def build_force_payload(
    start_stamp: int, samplecount: int, samples: list[list[int]]
) -> bytes:
    """Build Force payload bytes (for tests/simulation)."""
    header = struct.pack("<QH", start_stamp, samplecount)
    body = bytearray(header)
    for row in samples:
        body.extend(struct.pack(f"<{len(row)}H", *row))
    return bytes(body)
