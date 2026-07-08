"""Payload parsers for device data types."""

from __future__ import annotations

import struct
from dataclasses import dataclass

from pygcj.pygcj import GCJProj
trans = GCJProj()

FORCE_CHANNEL_COUNT = 32
EVENT_BATCH_MAX = 50
EVENT_ID_HEARTBEAT = 0x00000000

DATA_TYPE_FORCE = 0x0101
DATA_TYPE_IMU = 0x0201
DATA_TYPE_GPS = 0x0301
DATA_TYPE_DEVICE_STATUS = 0x0401
DATA_TYPE_EVENT = 0x0501


@dataclass(frozen=True)
class ForcePayload:
    start_stamp: int
    samplecount: int
    samples: list[list[int]]


@dataclass(frozen=True)
class GpsPayload:
    timestamp: int
    latitude: float
    longitude: float
    altitude: float
    speed: float
    heading: float
    accuracy: float
    fix_type: int
    satellite_count: int


@dataclass(frozen=True)
class DeviceStatusPayload:
    battery: int
    device_link: int


@dataclass(frozen=True)
class EventSample:
    event_id: int
    stamp: int
    reserved: int


@dataclass(frozen=True)
class EventPayload:
    samplecount: int
    events: list[EventSample]


def parse_force(payload: bytes) -> ForcePayload:
    if len(payload) < 10:
        raise ValueError("Force payload too short")
    start_stamp = struct.unpack_from("<Q", payload, 0)[0]
    samplecount = struct.unpack_from("<H", payload, 8)[0]
    expected = 10 + samplecount * FORCE_CHANNEL_COUNT * 2
    if len(payload) < expected:
        raise ValueError("Force payload truncated")

    samples: list[list[int]] = []
    offset = 10
    for _ in range(samplecount):
        row = list(
            struct.unpack_from(f"<{FORCE_CHANNEL_COUNT}H", payload, offset)
        )
        samples.append(row)
        offset += FORCE_CHANNEL_COUNT * 2

    return ForcePayload(
        start_stamp=start_stamp,
        samplecount=samplecount,
        samples=samples,
    )


def parse_gps(payload: bytes) -> GpsPayload:
    if len(payload) < 42:
        raise ValueError("GPS payload too short")
    (
        timestamp,
        latitude,
        longitude,
        altitude,
        speed,
        heading,
        accuracy,
        fix_type,
        satellite_count,
    ) = struct.unpack_from("<QddffffBB", payload, 0)
    # Transform WGS84 Coordinates to GCJ02
    gcj_lat, gcj_lon = trans.wgs_to_gcj(latitude, longitude)
    
    return GpsPayload(
        timestamp=timestamp,
        latitude=gcj_lat,
        longitude=gcj_lon,
        altitude=altitude,
        speed=speed,
        heading=heading,
        accuracy=accuracy,
        fix_type=fix_type,
        satellite_count=satellite_count,
    )


def parse_device_status(payload: bytes) -> DeviceStatusPayload:
    if len(payload) < 4:
        raise ValueError("DeviceStatus payload too short")
    battery, _reserved, device_link = struct.unpack_from("<BBH", payload, 0)
    return DeviceStatusPayload(battery=battery, device_link=device_link)


def parse_event(payload: bytes) -> EventPayload:
    if len(payload) < 2:
        raise ValueError("Event payload too short")
    samplecount = struct.unpack_from("<H", payload, 0)[0]
    if samplecount < 1 or samplecount > EVENT_BATCH_MAX:
        raise ValueError("Event samplecount out of range")

    expected = 2 + samplecount * 20
    if len(payload) < expected:
        raise ValueError("Event payload truncated")

    events: list[EventSample] = []
    offset = 2
    for _ in range(samplecount):
        event_id, stamp, reserved = struct.unpack_from("<IQQ", payload, offset)
        events.append(
            EventSample(event_id=event_id, stamp=stamp, reserved=reserved)
        )
        offset += 20

    return EventPayload(samplecount=samplecount, events=events)


def parse_imu(_payload: bytes) -> None:
    """IMU 0x0201 reserved — not sent in current firmware version."""
    return None
