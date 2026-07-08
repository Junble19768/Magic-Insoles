#!/usr/bin/env python3
"""
Python port of server.cpp: USB DAQ (libusb-bulk) tactile-data TCP server.

Matches the wire protocol byte-for-byte with client.py (40 native-endian doubles,
320 bytes: 32 sensor values + 1 timestamp + 7 padding zeros).

Live mode reads USB-DAQ hardware; playback mode replays FSR rows from a
calibration CSV over the same TCP protocol.
"""

from __future__ import annotations

import argparse
import csv
import os
import socket
import struct
import time
import traceback
from collections.abc import Callable
from pathlib import Path

import usb_daq_v20
from usb_daq_v20 import DaqError

# ─── TCP server config ──────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 6543
SEND_SIZE = 320  # 40 doubles

# Optional: select device by CardID (hex or decimal). Default: first opened card.
CARD_ID_ENV = "DAQ_CARD_ID"

FSR_COLUMNS = [f"fsr_{i:02d}" for i in range(32)]


def _resolve_card_id() -> int:
    env_val = os.environ.get(CARD_ID_ENV, "").strip()
    if env_val:
        return int(env_val, 0)
    ids = usb_daq_v20.list_card_ids()
    if not ids:
        raise DaqError(
            usb_daq_v20.ErrorCode.NO_DAQ_DEVICE,
            "open_all 后未找到任何 CardID",
            stage="lookup",
        )
    return ids[0]


class Tactile:
    def __init__(self):
        self._init = False
        self.card_id: int | None = None

        self.ad_chan_s = 0
        self.ad_chan_t = 7
        self.out_chan_s = 0
        self.out_chan_t = 5
        self.ON = 1
        self.OFF = 0

        self.data_x = [
            0, 0, 0, 0, 1, 1, 1, 2, 2, 3, 3, 4, 5, 5, 5, 5,
            0, 0, 0, 0, 1, 1, 1, 2, 2, 3, 3, 4, 5, 5, 5, 5,
        ]
        self.data_y = [
            0, 1, 2, 3, 1, 2, 3, 1, 2, 1, 2, 3, 0, 1, 2, 3,
            4, 5, 6, 7, 5, 6, 7, 5, 6, 5, 6, 7, 4, 5, 6, 7,
        ]

        self.raw_data = [[0.0] * 8 for _ in range(6)]

    def init(self) -> bool:
        try:
            devices = usb_daq_v20.open_all()
            print(f"opened {len(devices)} device(s):")
            for info in devices:
                print(f"  CardID=0x{info.card_id:08X} bus={info.bus} addr={info.address}")

            self.card_id = _resolve_card_id()
            print(f"using CardID=0x{self.card_id:08X}")

            for i in range(8):
                usb_daq_v20.do_set(self.card_id, i, 0)
                print(f"Dout_chan {i} test set success.")

            for i in range(12):
                usb_daq_v20.ad_single(self.card_id, i)
                print(f"AD_chan {i} test read success.")

        except DaqError as e:
            print(f"usb device open fail: {e}")
            usb_daq_v20.close_all()
            return False

        self._init = True
        print("usb device open ok.")
        return True

    def read(self) -> list[float]:
        if not self._init or self.card_id is None:
            raise RuntimeError("Tactile uninitialized")

        for row in range(self.out_chan_t - self.out_chan_s + 1):
            for col in range(self.ad_chan_t - self.ad_chan_s + 1):
                self.raw_data[row][col] = 0.0

        for row in range(self.out_chan_s, self.out_chan_t + 1):
            try:
                usb_daq_v20.do_set(self.card_id, row, self.ON)
            except DaqError as e:
                print(f"DoSetV20 ON row={row}: {e}")

            for col in range(self.ad_chan_s, self.ad_chan_t + 1):
                try:
                    self.raw_data[row][col] = usb_daq_v20.ad_single(self.card_id, col)
                except DaqError as e:
                    print(f"ADSingleV20 error at row={row}, col={col}: {e}")

            try:
                usb_daq_v20.do_set(self.card_id, row, self.OFF)
            except DaqError as e:
                print(f"DoSetV20 OFF row={row}: {e}")

        data = [0.0] * 32
        for i in range(32):
            data[i] = self.raw_data[self.data_x[i]][self.data_y[i]]
        return data

    def close(self):
        usb_daq_v20.close_all()
        self._init = False
        self.card_id = None

    def reset(self):
        if self.card_id is not None:
            try:
                usb_daq_v20.reset_device(self.card_id)
            except DaqError as e:
                print(f"reset failed: {e}")
        self._init = False
        self.card_id = None


class CsvPlayback:
    """Replay FSR rows from a calibration CSV over the live TCP wire format."""

    def __init__(self, path: Path, *, loop: bool = False, speed: float = 1.0) -> None:
        self._path = path
        self._loop = loop
        self._speed = speed
        self._rows = self._load_rows(path)
        self._index = 0
        self._prev_stamp: float | None = None

    @staticmethod
    def _load_rows(path: Path) -> list[tuple[float, list[float]]]:
        if not path.is_file():
            raise FileNotFoundError(f"录制文件不存在: {path}")

        required = {"timestamp", *FSR_COLUMNS}
        rows: list[tuple[float, list[float]]] = []

        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                raise ValueError(f"CSV 无表头: {path}")

            columns = {name.strip() for name in reader.fieldnames}
            missing = required - columns
            if missing:
                missing_list = ", ".join(sorted(missing))
                raise ValueError(f"CSV 缺少列 ({missing_list}): {path}")

            for line_no, raw_row in enumerate(reader, start=2):
                row = {key.strip(): value for key, value in raw_row.items() if key is not None}
                try:
                    stamp = float(row["timestamp"])
                    data = [float(row[col]) for col in FSR_COLUMNS]
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f"CSV 第 {line_no} 行解析失败: {path}") from exc
                rows.append((stamp, data))

        if not rows:
            raise ValueError(f"CSV 无数据行: {path}")

        return rows

    @property
    def row_count(self) -> int:
        return len(self._rows)

    def rewind(self) -> None:
        self._index = 0
        self._prev_stamp = None

    def read(self) -> tuple[list[float], float]:
        if self._index >= len(self._rows):
            if not self._loop:
                raise StopIteration
            self.rewind()
            print(f"playback loop: restarting {self._path.name}")

        stamp, data = self._rows[self._index]
        if self._prev_stamp is not None and self._speed > 0:
            delta = (stamp - self._prev_stamp) / self._speed
            if delta > 0:
                time.sleep(delta)

        self._prev_stamp = stamp
        self._index += 1
        return data, stamp


def pack_data(tac_data, stamp):
    return struct.pack("40d", *tac_data, stamp, *([0.0] * 7))


ReadFrame = Callable[[], tuple[list[float], float]]


def serve_client(client_sock: socket.socket, read_frame: ReadFrame) -> int:
    """Stream frames to a connected client. Returns frames sent."""
    send_cnt = 0
    t1 = time.time()

    try:
        while True:
            try:
                tac_data, stamp = read_frame()
            except StopIteration:
                print("playback finished.")
                break

            packed = pack_data(tac_data, stamp)
            try:
                client_sock.sendall(packed)
            except OSError as e:
                print(f"ERROR: {e}")
                break

            send_cnt += 1
            t2 = time.time()
            if t2 - t1 >= 1.0:
                t1 = t2
                print(f"sent {send_cnt} msgs.")
    finally:
        try:
            client_sock.close()
        except OSError:
            pass

    return send_cnt


def _accept_client(server_sock: socket.socket) -> socket.socket | None:
    try:
        client_sock, _addr = server_sock.accept()
    except OSError:
        return None
    return client_sock


def _run_live_server() -> None:
    print(f"Listening on {HOST}:{PORT} (live) ...")

    while True:
        tac = Tactile()
        if not tac.init():
            print("tac_init failed. resetting device, sleep 1 second ...")
            tac.reset()
            tac.close()
            time.sleep(1)
            continue

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, PORT))
        server_sock.listen(1)
        print("listening...")

        client_sock = _accept_client(server_sock)
        server_sock.close()
        if client_sock is None:
            tac.close()
            continue

        print("client connected.")

        def read_frame() -> tuple[list[float], float]:
            return tac.read(), time.time()

        try:
            serve_client(client_sock, read_frame)
        finally:
            tac.close()
            print("client disconnected.")


def _run_playback_server(playback: CsvPlayback) -> None:
    print(
        f"Playback {playback._path} ({playback.row_count} rows) "
        f"on {HOST}:{PORT} (speed={playback._speed}, loop={playback._loop}) ..."
    )

    while True:
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, PORT))
        server_sock.listen(1)
        print("listening...")

        client_sock = _accept_client(server_sock)
        server_sock.close()
        if client_sock is None:
            continue

        print("client connected.")
        playback.rewind()
        serve_client(client_sock, playback.read)
        print("client disconnected.")

        if not playback._loop:
            break


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FSR tactile-data TCP server")
    parser.add_argument(
        "--playback",
        metavar="CSV",
        type=Path,
        help="从标定录制 CSV 回放 FSR 数据（无需 USB-DAQ）",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="回放倍速（默认 1.0；与 --fast 互斥时 --fast 优先）",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="尽快推送，不按 CSV 时间间隔 sleep",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="播放到文件末尾后从头循环",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_arg_parser().parse_args(argv)

    if args.playback is not None:
        speed = 0.0 if args.fast else args.speed
        if speed < 0:
            raise SystemExit("--speed 不能为负数")
        playback = CsvPlayback(args.playback, loop=args.loop, speed=speed)
        _run_playback_server(playback)
        return

    _run_live_server()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception:
        traceback.print_exc()
    finally:
        print("Done.")
