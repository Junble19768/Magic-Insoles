"""Asyncio TCP server for device binary frames."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from config import settings
from database import SessionLocal
from protocol.device_frame import FrameParser
from services.ingest import ingest_frame

logger = logging.getLogger(__name__)

_server: asyncio.AbstractServer | None = None


async def _handle_client(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    peer = writer.get_extra_info("peername")
    logger.info("Device TCP connected: %s", peer)
    parser = FrameParser(max_frame_bytes=settings.device_max_frame_bytes)

    try:
        while True:
            chunk = await reader.read(4096)
            if not chunk:
                break

            frames = parser.feed(chunk)
            if not frames:
                continue

            await asyncio.to_thread(_ingest_frames_sync, frames)
    except ConnectionResetError:
        logger.info("Device TCP reset: %s", peer)
    except Exception:
        logger.exception("Device TCP handler error: %s", peer)
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        logger.info("Device TCP disconnected: %s", peer)


def _ingest_frames_sync(frames: list[Any]) -> None:
    db = SessionLocal()
    try:
        for frame in frames:
            ingest_frame(frame, db)
    finally:
        db.close()


async def start_tcp_server() -> asyncio.AbstractServer:
    global _server
    _server = await asyncio.start_server(
        _handle_client,
        host=settings.device_tcp_host,
        port=settings.device_tcp_port,
    )
    sockets = ", ".join(str(sock.getsockname()) for sock in _server.sockets or [])
    logger.info("Device TCP server listening on %s", sockets)
    return _server


async def stop_tcp_server() -> None:
    global _server
    if _server is not None:
        _server.close()
        await _server.wait_closed()
        _server = None
        logger.info("Device TCP server stopped")
