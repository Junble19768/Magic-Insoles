#!/usr/bin/env python3
"""Simulate device TCP ingest and optional report generation."""

from __future__ import annotations

import argparse
import asyncio
import struct
import time

import httpx

from protocol.device_frame import build_frame
from protocol.payloads import (
    DATA_TYPE_DEVICE_STATUS,
    DATA_TYPE_EVENT,
    DATA_TYPE_FORCE,
    DATA_TYPE_GPS,
    EVENT_ID_HEARTBEAT,
)
from services.ingest import build_force_payload

DEFAULT_API_KEY = "dev-magic-insoles-key"


def build_gps_payload() -> bytes:
    return struct.pack(
        "<QddffffBB",
        int(time.time() * 1000),
        40.02,
        116.39,
        50.0,
        1.5,
        180.0,
        4.0,
        3,
        10,
    )


def build_status_payload() -> bytes:
    return struct.pack("<BBH", 85, 0, 0b11)


def build_event_payload() -> bytes:
    stamp = int(time.time() * 1000)
    events = struct.pack("<IQQ", 10, stamp, 0)
    return struct.pack("<H", 1) + events


def build_heartbeat_payload() -> bytes:
    stamp = int(time.time() * 1000)
    events = struct.pack("<IQQ", EVENT_ID_HEARTBEAT, stamp, 0)
    return struct.pack("<H", 1) + events


async def send_tcp(host: str, port: int) -> None:
    force_payload = build_force_payload(
        int(time.time() * 1000),
        2,
        [[100 + i for i in range(32)], [200 + i for i in range(32)]],
    )
    frames = [
        build_frame(1, DATA_TYPE_FORCE, force_payload),
        build_frame(2, DATA_TYPE_GPS, build_gps_payload()),
        build_frame(3, DATA_TYPE_DEVICE_STATUS, build_status_payload()),
        build_frame(4, DATA_TYPE_EVENT, build_event_payload()),
        build_frame(5, DATA_TYPE_EVENT, build_heartbeat_payload()),
    ]

    # Sticky packet: concatenate first two frames
    sticky = frames[0] + frames[1]
    split_tail = frames[2]
    bad_crc = bytearray(frames[3])
    bad_crc[-1] ^= 0xAA

    reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write(sticky[: len(sticky) // 2])
        await writer.drain()
        await asyncio.sleep(0.05)
        writer.write(sticky[len(sticky) // 2 :])
        await writer.drain()
        writer.write(split_tail)
        await writer.drain()
        writer.write(bytes(bad_crc))
        await writer.drain()
        writer.write(frames[4])
        await writer.drain()
        print(f"Sent {len(frames)} logical frames (sticky/split/bad-crc mix)")
    finally:
        writer.close()
        await writer.wait_closed()


def post_http_ingest(base_url: str, api_key: str) -> None:
    payload = {
        "frames": [
            {
                "timestamp": time.time(),
                "pressures": [50] * 32,
                "gait_state": 1,
                "ml_class": 0,
                "ml_conf": 0.92,
                "step_count": 5,
            }
        ]
    }
    response = httpx.post(
        f"{base_url}/api/ingest",
        json=payload,
        headers={"X-API-Key": api_key},
        timeout=30.0,
    )
    response.raise_for_status()
    print("HTTP ingest:", response.json())


def generate_report(base_url: str, api_key: str) -> None:
    response = httpx.post(
        f"{base_url}/api/report/generate",
        headers={"X-API-Key": api_key},
        timeout=60.0,
    )
    response.raise_for_status()
    print("Report generate:", response.json())


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate magic-insoles device ingest")
    parser.add_argument("--tcp-host", default="127.0.0.1")
    parser.add_argument("--tcp-port", type=int, default=9000)
    parser.add_argument("--api-base", default="http://127.0.0.1:8001")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY)
    parser.add_argument("--http-ingest", action="store_true")
    parser.add_argument("--generate-report", action="store_true")
    args = parser.parse_args()

    asyncio.run(send_tcp(args.tcp_host, args.tcp_port))

    if args.http_ingest:
        post_http_ingest(args.api_base, args.api_key)
    if args.generate_report:
        generate_report(args.api_base, args.api_key)


if __name__ == "__main__":
    main()
