"""Enumerate connected USB-DAQ devices and print Card ID table."""

from __future__ import annotations

import sys
from typing import TextIO

from .constants import PID, VID
from .device import DeviceInfo, probe_devices
from .errors import DaqError


def list_connected_devices() -> list[DeviceInfo]:
    """Probe all connected DAQ cards and return their CardID / bus / address."""
    return probe_devices()


def format_devices_table(devices: list[DeviceInfo]) -> str:
    """Format device list as a human-readable table string."""
    if not devices:
        return f"未找到 USB-DAQ 设备 (VID=0x{VID:04X}, PID=0x{PID:04X})"

    lines = [
        f"共发现 {len(devices)} 张采集卡 (VID=0x{VID:04X}, PID=0x{PID:04X})",
        "",
        f"{'序号':<6}{'Bus':<6}{'Address':<10}{'Card ID (dec)':<16}{'Card ID (hex)'}",
        "-" * 52,
    ]
    for idx, info in enumerate(devices):
        lines.append(
            f"{idx:<6}{info.bus:<6}{info.address:<10}"
            f"{info.card_id:<16}0x{info.card_id:08X}"
        )
    return "\n".join(lines)


def print_connected_devices(*, file: TextIO | None = None) -> list[DeviceInfo]:
    """Probe devices, print table to stdout (or file), return device list."""
    if file is None:
        file = sys.stdout
    devices = list_connected_devices()
    print(format_devices_table(devices), file=file)
    return devices


def main(argv: list[str] | None = None) -> int:
    """CLI entry: list Card IDs of all connected USB-DAQ devices."""
    try:
        devices = print_connected_devices()
    except DaqError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    if not devices:
        return 1
    return 0
