import asyncio
import json
import socket
import struct
import threading
import time

import numpy as np

from .config import FORCE_SIGN, FORCE_WS_URL, FSR_HOST, FSR_PACKET_SIZE, FSR_PORT

try:
    import websockets
except ImportError as exc:
    raise SystemExit("请先安装 websockets: pip install websockets") from exc


def fsr_reader(hub, pipeline, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((FSR_HOST, FSR_PORT))
            sock.settimeout(1.0)
            print(f"FSR 已连接 {FSR_HOST}:{FSR_PORT}")
            buf = b""
            while not stop_event.is_set():
                try:
                    chunk = sock.recv(FSR_PACKET_SIZE - len(buf))
                except socket.timeout:
                    continue
                if not chunk:
                    break
                buf += chunk
                if len(buf) < FSR_PACKET_SIZE:
                    continue
                packet, buf = buf[:FSR_PACKET_SIZE], buf[FSR_PACKET_SIZE:]
                values = struct.unpack("40d", packet)
                fsr_data = np.array(values[:32], dtype=float)
                fsr_stamp = values[32]
                hub.set_fsr(fsr_data, fsr_stamp)
                pipeline.enqueue_fsr(fsr_stamp, fsr_data)
        except OSError as exc:
            hub.set_fsr_disconnected()
            print(f"FSR 连接失败，1 秒后重试: {exc}")
            time.sleep(1.0)
        finally:
            sock.close()


async def _force_ws_loop(hub, pipeline, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            async with websockets.connect(FORCE_WS_URL) as ws:
                print(f"压力传感器已连接 {FORCE_WS_URL}")
                async for msg in ws:
                    if stop_event.is_set():
                        break
                    try:
                        payload = json.loads(msg)
                        values = payload.get("values", [])
                        if not values:
                            continue
                        stamp = float(payload.get("timestamp", time.time()))
                        value = FORCE_SIGN * float(values[0])
                        hub.set_force([value], stamp)
                        pipeline.update_force(stamp, value)
                    except Exception:
                        continue
        except Exception as exc:
            hub.set_force_disconnected()
            print(f"压力 WebSocket 断开，1 秒后重试: {exc}")
            await asyncio.sleep(1.0)


def force_reader_thread(hub, pipeline, stop_event: threading.Event) -> None:
    asyncio.run(_force_ws_loop(hub, pipeline, stop_event))
