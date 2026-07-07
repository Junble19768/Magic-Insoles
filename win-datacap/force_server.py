#!/usr/bin/env python3
"""
Modbus RTU 压力传感器 WebSocket 发布服务。

轮询串口力传感器（Ch0 推拉力），向所有已连接客户端广播 JSON 帧，
供 FSR 标定客户端订阅。
"""

import asyncio
import json
import struct
import time
import traceback

import serial
import websockets

import modbus_rtu as mb

# ── Modbus 配置 ─────────────────────────────────────────
PORT = "COM4"
BAUDRATE = 9600
SLAVE_ADDR = 0x01
REG_START = 0x0000
REG_COUNT = 0x0002  # Ch0 推拉力 (Reg0-1, float32)

CHANNELS = [
    (0, "Ch0_Reg0-1"),
]

REG_BYTE_COUNT = REG_COUNT * 2
RESP_FRAME_LEN = 3 + REG_BYTE_COUNT + 2
READ_TIMEOUT_S = 0.03
POLL_SLEEP_S = 0.001  # 节流查询频率，避免快于传感器内部刷新导致重复值

# ── WebSocket 配置 ───────────────────────────────────────
WS_HOST = "127.0.0.1"
WS_PORT = 8765

_clients: set = set()


def _parse_modbus_frame(full_frame: bytes) -> dict | None:
    """解析一帧 Modbus 03 响应，失败返回 None。"""
    parsed = mb.parse_read_response(full_frame)
    if parsed is None:
        return None

    registers_raw = parsed["registers_raw"]
    values = [
        struct.unpack(">f", registers_raw[off : off + 4])[0]
        for off, _ in CHANNELS
    ]

    return {
        "timestamp": time.time(),
        "values": values,
        "channels": [{"name": name, "value": val} for (_, name), val in zip(CHANNELS, values)],
    }


def _read_force_sample(ser: serial.Serial, tx_cmd: bytes) -> dict | None:
    """发送 Modbus 请求并读取一帧力值（定长收包，失步时 reset）。"""
    ser.write(tx_cmd)
    ser.flush()

    frame = ser.read(RESP_FRAME_LEN)
    if len(frame) != RESP_FRAME_LEN:
        ser.reset_input_buffer()
        return None

    if (
        frame[0] != SLAVE_ADDR
        or frame[1] != 0x03
        or frame[2] != REG_BYTE_COUNT
    ):
        ser.reset_input_buffer()
        return None

    if not mb.verify_frame(frame):
        ser.reset_input_buffer()
        return None

    return _parse_modbus_frame(frame)


async def _register_client(websocket):
    _clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        _clients.discard(websocket)


async def _broadcast(payload: dict):
    if not _clients:
        return

    msg = json.dumps(payload)
    dead = []
    for ws in list(_clients):
        try:
            await ws.send(msg)
        except websockets.ConnectionClosed:
            dead.append(ws)
    for ws in dead:
        _clients.discard(ws)


async def _poll_loop(ser: serial.Serial, tx_cmd: bytes):
    loop = asyncio.get_running_loop()
    frame_count = 0
    err_count = 0
    fps_count = 0
    last_fps_report = time.monotonic()

    while True:
        try:
            sample = await loop.run_in_executor(
                None, _read_force_sample, ser, tx_cmd
            )
            if sample is None:
                err_count += 1
            else:
                frame_count += 1
                sample["frame"] = frame_count
                sample["errors"] = err_count
                await _broadcast(sample)
                if _clients:
                    fps_count += 1
        except Exception:
            err_count += 1
            traceback.print_exc()

        now = time.monotonic()
        if _clients and now - last_fps_report >= 1.0:
            elapsed = now - last_fps_report
            print(
                f"FPS: {fps_count / elapsed:.1f} "
                f"({fps_count} frames, {len(_clients)} client(s))"
            )
            fps_count = 0
            last_fps_report = now

        await asyncio.sleep(POLL_SLEEP_S)


async def main():
    tx_cmd = mb.read_holding_registers(SLAVE_ADDR, REG_START, REG_COUNT)

    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=READ_TIMEOUT_S)
    except Exception as e:
        print(f"串口打开失败 ({PORT}): {e}")
        return

    ser.reset_input_buffer()
    print(f"串口 {PORT} @ {BAUDRATE} bps")
    print(f"WebSocket 监听 ws://{WS_HOST}:{WS_PORT}")
    print(f"Modbus 读 {REG_COUNT} 寄存器 (Ch0), 请求帧: {tx_cmd.hex(' ').upper()}")

    async with websockets.serve(_register_client, WS_HOST, WS_PORT):
        await _poll_loop(ser, tx_cmd)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n已停止。")
