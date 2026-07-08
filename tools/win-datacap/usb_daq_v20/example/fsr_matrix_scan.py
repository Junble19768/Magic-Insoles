#!/usr/bin/env python3
"""
Example: FSR insole 32-point matrix scan (same logic as server.py Tactile.read).

Uses DO rows 0-5 to select FSR rows and AD cols 0-7 to read voltages,
then remaps to 32 sensor indices.
"""

import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import usb_daq_v20
from usb_daq_v20 import DaqError

# Remap table (same as server.cpp / server.py)
DATA_X = [
    0, 0, 0, 0, 1, 1, 1, 2, 2, 3, 3, 4, 5, 5, 5, 5,
    0, 0, 0, 0, 1, 1, 1, 2, 2, 3, 3, 4, 5, 5, 5, 5,
]
DATA_Y = [
    0, 1, 2, 3, 1, 2, 3, 1, 2, 1, 2, 3, 0, 1, 2, 3,
    4, 5, 6, 7, 5, 6, 7, 5, 6, 5, 6, 7, 4, 5, 6, 7,
]

AD_CHAN_S, AD_CHAN_T = 0, 7
OUT_CHAN_S, OUT_CHAN_T = 0, 5
ON, OFF = 1, 0


def scan_matrix(card_id: int) -> list[float]:
    raw = [[0.0] * 8 for _ in range(6)]

    for row in range(OUT_CHAN_S, OUT_CHAN_T + 1):
        usb_daq_v20.do_set(card_id, row, ON)
        for col in range(AD_CHAN_S, AD_CHAN_T + 1):
            raw[row][col] = usb_daq_v20.ad_single(card_id, col)
        usb_daq_v20.do_set(card_id, row, OFF)

    return [raw[DATA_X[i]][DATA_Y[i]] for i in range(32)]


def main() -> int:
    try:
        devices = usb_daq_v20.open_all()
        card_id = devices[0].card_id
        print(f"FSR 矩阵扫描  CardID=0x{card_id:08X}  按 Ctrl+C 停止\n")

        while True:
            data = scan_matrix(card_id)
            # 左脚 16 点 + 右脚 16 点
            left = " ".join(f"{v:.3f}" for v in data[:16])
            right = " ".join(f"{v:.3f}" for v in data[16:])
            print(f"左: {left}")
            print(f"右: {right}\n")
            time.sleep(0.2)

    except KeyboardInterrupt:
        print("已停止")
        return 0
    except DaqError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    finally:
        usb_daq_v20.close_all()


if __name__ == "__main__":
    sys.exit(main())
