#!/usr/bin/env python3
"""
Python port of server.cpp: USB DAQ (libusb-bulk) tactile-data TCP server.

Matches the wire protocol byte-for-byte with client.py (40 native-endian doubles,
320 bytes: 32 sensor values + 1 timestamp + 7 padding zeros).
"""

import os
import socket
import struct
import time
import traceback

import usb_daq_v20
from usb_daq_v20 import DaqError

# ─── TCP server config ──────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 6543
SEND_SIZE = 320  # 40 doubles

# Optional: select device by CardID (hex or decimal). Default: first opened card.
CARD_ID_ENV = "DAQ_CARD_ID"


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


def pack_data(tac_data, stamp):
    return struct.pack("40d", *tac_data, stamp, *([0.0] * 7))


def main():
    print(f"Listening on {HOST}:{PORT} ...")

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

        try:
            client_sock, addr = server_sock.accept()
        except OSError:
            server_sock.close()
            tac.close()
            continue

        server_sock.close()
        print("client connected.")

        send_cnt = 0
        t1 = time.time()

        try:
            while True:
                tac_data = tac.read()
                stamp = time.time()
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

        tac.close()
        print("client disconnected.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception:
        traceback.print_exc()
    finally:
        print("Done.")
