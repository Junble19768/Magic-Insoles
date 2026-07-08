"""
Python port of usb-daq-v20 (USB bulk DAQ library).

All device operations are indexed by CardID instead of dev index.
"""

from __future__ import annotations

from typing import Sequence

from .device import DeviceInfo, get_manager, probe_devices
from .errors import DaqError, ErrorCode
from .list_cards import (
    format_devices_table,
    list_connected_devices,
    print_connected_devices,
)
from . import protocol

__all__ = [
    "DaqError",
    "ErrorCode",
    "DeviceInfo",
    "list_connected_devices",
    "format_devices_table",
    "print_connected_devices",
    "open_all",
    "close_all",
    "list_devices",
    "list_card_ids",
    "get_device_count",
    "get_card_id",
    "reset_device",
    "ad_single",
    "ad_continu",
    "mad_continu",
    "da_single_out",
    "da_data_send",
    "da_scan_out",
    "pwm_out_set",
    "pwm_in_set",
    "pwm_in_read",
    "count_set",
    "count_read",
    "do_set",
    "di_read",
]


def open_all() -> list[DeviceInfo]:
    return get_manager().open_all()


def close_all() -> None:
    get_manager().close_all()


def list_devices(*, probe: bool = False) -> list[DeviceInfo]:
    if probe:
        return probe_devices()
    return get_manager().list_devices()


def list_card_ids(*, probe: bool = False) -> list[int]:
    return [d.card_id for d in list_devices(probe=probe)]


def get_device_count() -> int:
    return get_manager().get_device_count()


def get_card_id(card_id: int) -> int:
    return get_manager().get_card_id(card_id)


def reset_device(card_id: int) -> None:
    get_manager().reset_device(card_id)


def _session(card_id: int):
    return get_manager().resolve(card_id)


def ad_single(card_id: int, chan: int) -> float:
    return protocol.ad_single(_session(card_id), chan)


def ad_continu(card_id: int, chan: int, num_sample: int, frequency: int) -> list[float]:
    return protocol.ad_continu(_session(card_id), chan, num_sample, frequency)


def mad_continu(
    card_id: int,
    chan_first: int,
    chan_last: int,
    num_sample: int,
    frequency: int,
) -> list[float]:
    return protocol.mad_continu(
        _session(card_id), chan_first, chan_last, num_sample, frequency
    )


def da_single_out(card_id: int, chan: int, value: int) -> None:
    protocol.da_single_out(_session(card_id), chan, value)


def da_data_send(card_id: int, chan: int, num: int, databuf: Sequence[int]) -> None:
    protocol.da_data_send(_session(card_id), chan, num, databuf)


def da_scan_out(card_id: int, chan: int, freq: int, scan_num: int) -> None:
    protocol.da_scan_out(_session(card_id), chan, freq, scan_num)


def pwm_out_set(card_id: int, chan: int, freq: int, duty_cycle: float) -> None:
    protocol.pwm_out_set(_session(card_id), chan, freq, duty_cycle)


def pwm_in_set(card_id: int, mod: int) -> None:
    protocol.pwm_in_set(_session(card_id), mod)


def pwm_in_read(card_id: int) -> tuple[float, int]:
    return protocol.pwm_in_read(_session(card_id))


def count_set(card_id: int, mod: int) -> None:
    protocol.count_set(_session(card_id), mod)


def count_read(card_id: int) -> int:
    return protocol.count_read(_session(card_id))


def do_set(card_id: int, chan: int, state: int) -> None:
    protocol.do_set(_session(card_id), chan, state)


def di_read(card_id: int) -> int:
    return protocol.di_read(_session(card_id))
