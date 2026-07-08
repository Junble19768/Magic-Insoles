#!/usr/bin/env python3
"""Example: list Card IDs of all connected USB-DAQ devices."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from usb_daq_v20.list_cards import main

if __name__ == "__main__":
    sys.exit(main())
