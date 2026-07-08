#!/usr/bin/env python3
"""Example: open first DAQ card and read AD channels 0-7."""

import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import usb_daq_v20
from usb_daq_v20 import DaqError

CHANNELS = 8
INTERVAL_S = 0.5


def main() -> int:
    try:
        devices = usb_daq_v20.open_all()
        if not devices:
            print("未找到设备")
            return 1

        card_id = devices[0].card_id
        print(f"使用 CardID=0x{card_id:08X}，按 Ctrl+C 停止\n")

        while True:
            values = []
            for ch in range(CHANNELS):
                values.append(usb_daq_v20.ad_single(card_id, ch))
            line = "  ".join(f"AD[{i}]={v:.4f}V" for i, v in enumerate(values))
            print(line)
            time.sleep(INTERVAL_S)

    except KeyboardInterrupt:
        print("\n已停止")
        return 0
    except DaqError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    finally:
        usb_daq_v20.close_all()


if __name__ == "__main__":
    sys.exit(main())
