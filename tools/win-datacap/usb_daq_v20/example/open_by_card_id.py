#!/usr/bin/env python3
"""Example: probe devices, then open and use a specific CardID."""

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import usb_daq_v20
from usb_daq_v20 import DaqError


def parse_card_id(value: str) -> int:
    return int(value, 0)


def main() -> int:
    parser = argparse.ArgumentParser(description="按 CardID 打开 USB-DAQ 并读取 AD[0]")
    parser.add_argument(
        "card_id",
        nargs="?",
        help="CardID（十进制或 0x 十六进制）；省略则使用 probe 结果中的第一张",
    )
    args = parser.parse_args()

    try:
        print("=== 已连接设备 ===")
        usb_daq_v20.print_connected_devices()
        print()

        devices = usb_daq_v20.open_all()
        if args.card_id is not None:
            card_id = parse_card_id(args.card_id)
        else:
            card_id = devices[0].card_id
            print(f"未指定 CardID，使用首张卡 0x{card_id:08X}\n")

        # 验证 CardID 在 registry 中
        usb_daq_v20.get_card_id(card_id)

        usb_daq_v20.do_set(card_id, chan=0, state=0)
        for ch in range(4):
            v = usb_daq_v20.ad_single(card_id, ch)
            print(f"  AD[{ch}] = {v:.4f} V")

        print(f"\nCardID=0x{card_id:08X} 操作成功")
        return 0

    except DaqError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    finally:
        usb_daq_v20.close_all()


if __name__ == "__main__":
    sys.exit(main())
