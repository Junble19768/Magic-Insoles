#!/usr/bin/env python3
"""
Modbus RTU 压力传感器 WebSocket 发布服务。

轮询串口力传感器（与 serial_test.py 相同协议），向所有已连接客户端
广播 JSON 帧，供 FSR 标定客户端订阅。
"""

import asyncio
import json
import struct
import time
import traceback

import serial
import websockets

import modbus_rtu as mb

# ── Modbus 配置（与 serial_test.py 一致）────────────────
PORT = "COM4"
BAUDRATE = 9600
SLAVE_ADDR = 0x01
REG_START = 0x0000
REG_COUNT = 0x000D

CHANNELS = [
    (0, "Ch0_Reg0-1"),
    (4, "Ch1_Reg2-3"),
    (8, "Ch2_Reg4-5"),
    (12, "Ch3_Reg6-7"),
    (16, "Ch4_Reg8-9"),
    (20, "Ch5_Reg10-11"),
]
STATUS_OFFSET = 24

POLL_INTERVAL_S = 0.05

# ── WebSocket 配置 ───────────────────────────────────────
WS_HOST = "127.0.0.1"
WS_PORT = 8765

_clients: set = set()


def _parse_modbus_frame(full_frame: bytes) -> dict | None:
    """解析一帧 Modbus 03 响应，失败返回 None。"""
    if len(full_frame) < 3:
        return None

    func = full_frame[1]
    if func != 0x03:
        return None

    if not mb.verify_frame(full_frame):
        return None

    byte_count = full_frame[2]
    registers_raw = full_frame[3 : 3 + byte_count]

    values = [
        struct.unpack(">f", registers_raw[off : off + 4])[0]
        for off, _ in CHANNELS
    ]
    status = struct.unpack(
        ">H", registers_raw[STATUS_OFFSET : STATUS_OFFSET + 2]
    )[0]

    return {
        "timestamp": time.time(),
        "values": values,
        "channels": [{"name": name, "value": val} for (_, name), val in zip(CHANNELS, values)],
        "status": status,
    }


def _read_force_sample(ser: serial.Serial, tx_cmd: bytes) -> dict | None:
    """发送 Modbus 请求并读取一帧力值。"""
    ser.reset_input_buffer()
    ser.write(tx_cmd)
    ser.flush()

    header = ser.read(3)
    if len(header) < 3:
        return None

    byte_count = header[2]
    remaining = ser.read(byte_count + 2)
    if len(remaining) < byte_count + 2:
        return None

    return _parse_modbus_frame(header + remaining)


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
        except Exception:
            err_count += 1
            traceback.print_exc()

        await asyncio.sleep(POLL_INTERVAL_S)


async def main():
    tx_cmd = mb.read_holding_registers(SLAVE_ADDR, REG_START, REG_COUNT)

    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=0.05)
    except Exception as e:
        print(f"串口打开失败 ({PORT}): {e}")
        return

    print(f"串口 {PORT} @ {BAUDRATE} bps")
    print(f"WebSocket 监听 ws://{WS_HOST}:{WS_PORT}")

    async with websockets.serve(_register_client, WS_HOST, WS_PORT):
        await _poll_loop(ser, tx_cmd)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n已停止。")
