"""USB bulk transfer helpers and V20 protocol commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

import usb.core

from .constants import (
    AD_VOLTAGE_SCALE,
    CMD_DO_SET,
    EP_IN1,
    EP_IN2,
    EP_OUT1,
    PACKET_TIMEOUT_MS,
)
from .errors import DaqError, ErrorCode

if TYPE_CHECKING:
    from .device import DeviceSession


def _usb_errno(exc: usb.core.USBError) -> int | None:
    return getattr(exc, "errno", None)


def bulk_write(
    session: DeviceSession,
    endpoint: int,
    data: bytes | bytearray,
    expected_len: int | None = None,
) -> None:
    if expected_len is None:
        expected_len = len(data)
    try:
        written = session.dev.write(endpoint, data, timeout=PACKET_TIMEOUT_MS)
    except usb.core.USBError as e:
        raise DaqError(
            ErrorCode.USB_IO,
            f"USB 写入失败",
            stage="bulk_write",
            card_id=session.card_id,
            usb_errno=_usb_errno(e),
            endpoint=endpoint,
            bus=session.bus,
            address=session.address,
        ) from e
    if written != expected_len:
        raise DaqError(
            ErrorCode.IO_SHORT_WRITE,
            "USB 写入字节数不符",
            stage="bulk_write",
            card_id=session.card_id,
            endpoint=endpoint,
            bus=session.bus,
            address=session.address,
            expected=expected_len,
            actual=written,
        )


def bulk_read(
    session: DeviceSession,
    endpoint: int,
    length: int,
    timeout_ms: int | None = None,
) -> bytes:
    if timeout_ms is None:
        timeout_ms = PACKET_TIMEOUT_MS
    try:
        data = bytes(session.dev.read(endpoint, length, timeout=timeout_ms))
    except usb.core.USBError as e:
        raise DaqError(
            ErrorCode.USB_IO,
            "USB 读取失败",
            stage="bulk_read",
            card_id=session.card_id,
            usb_errno=_usb_errno(e),
            endpoint=endpoint,
            bus=session.bus,
            address=session.address,
        ) from e
    if len(data) != length:
        raise DaqError(
            ErrorCode.IO_SHORT_READ,
            "USB 读取字节数不符",
            stage="bulk_read",
            card_id=session.card_id,
            endpoint=endpoint,
            bus=session.bus,
            address=session.address,
            expected=length,
            actual=len(data),
        )
    return data


def _adc_raw_to_voltage(raw: int) -> float:
    return raw * AD_VOLTAGE_SCALE


def _parse_adc_sample(lo: int, hi: int) -> float:
    return _adc_raw_to_voltage((hi << 8) + lo)


# ─── AD ───────────────────────────────────────────────────────────────────


def ad_single(session: DeviceSession, chan: int) -> float:
    bulk_write(session, EP_OUT1, bytes([0, 0]), 2)
    bulk_write(session, EP_OUT1, bytes([2, chan & 0x0F, 0]), 3)
    bulk_write(session, EP_OUT1, bytes([1, 1]), 2)
    inbuf = bulk_read(session, EP_IN2, 2, PACKET_TIMEOUT_MS * 2)
    return _parse_adc_sample(inbuf[0], inbuf[1])


def ad_continu(
    session: DeviceSession,
    chan: int,
    num_sample: int,
    frequency: int,
) -> list[float]:
    num_sample = num_sample - num_sample % 32
    if num_sample < 0:
        num_sample = 0

    bulk_write(session, EP_OUT1, bytes([0, 1]), 2)
    bulk_write(session, EP_OUT1, bytes([2, chan & 0x0F, 0]), 3)
    bulk_write(
        session,
        EP_OUT1,
        bytes([3, frequency & 0xFF, (frequency >> 8) & 0xFF, (frequency >> 16) & 0xFF, (frequency >> 24) & 0xFF]),
        5,
    )
    bulk_write(
        session,
        EP_OUT1,
        bytes([4, num_sample & 0xFF, (num_sample >> 8) & 0xFF, (num_sample >> 16) & 0xFF, (num_sample >> 24) & 0xFF]),
        5,
    )
    bulk_write(session, EP_OUT1, bytes([1, 1]), 2)

    timeout_ms = 1000 * 1024 // frequency + 5 if frequency > 0 else PACKET_TIMEOUT_MS * 2
    inbuf = bulk_read(session, EP_IN2, 2, timeout_ms)
    if not (inbuf[0] == 0x55 and inbuf[1] == 0xAA):
        inbuf = bulk_read(session, EP_IN2, 2, timeout_ms)
        if not (inbuf[0] == 0x55 and inbuf[1] == 0xAA):
            raise DaqError(
                ErrorCode.PROTOCOL,
                "连续 AD 握手失败，未收到 0x55 0xAA",
                stage="parse",
                card_id=session.card_id,
                bus=session.bus,
                address=session.address,
            )

    results: list[float] = []
    for _ in range(num_sample // 512):
        block = bulk_read(session, EP_IN2, 1024, timeout_ms)
        for i in range(512):
            lo = block[i * 2]
            hi = block[i * 2 + 1]
            results.append(_parse_adc_sample(lo, hi))
    return results


def mad_continu(
    session: DeviceSession,
    chan_first: int,
    chan_last: int,
    num_sample: int,
    frequency: int,
) -> list[float]:
    if chan_last < chan_first or chan_first < 0 or chan_last < 0 or chan_first > 15 or chan_last > 15:
        raise DaqError(
            ErrorCode.INVALID_PARAM,
            f"通道范围无效: chan_first={chan_first}, chan_last={chan_last}",
            stage="validate",
            card_id=session.card_id,
        )

    num_sample = num_sample - num_sample % 32
    if num_sample < 0:
        num_sample = 0

    bulk_write(session, EP_OUT1, bytes([0, 2]), 2)
    bulk_write(session, EP_OUT1, bytes([2, chan_first & 0x0F, chan_last & 0x0F]), 3)
    bulk_write(
        session,
        EP_OUT1,
        bytes([3, frequency & 0xFF, (frequency >> 8) & 0xFF, (frequency >> 16) & 0xFF, (frequency >> 24) & 0xFF]),
        5,
    )
    bulk_write(
        session,
        EP_OUT1,
        bytes([4, num_sample & 0xFF, (num_sample >> 8) & 0xFF, (num_sample >> 16) & 0xFF, (num_sample >> 24) & 0xFF]),
        5,
    )
    bulk_write(session, EP_OUT1, bytes([1, 1]), 2)

    timeout_ms = 1000 * 1024 // frequency + 5 if frequency > 0 else PACKET_TIMEOUT_MS * 2
    inbuf = bulk_read(session, EP_IN2, 2, timeout_ms)
    if not (inbuf[0] == 0x55 and inbuf[1] == 0xAA):
        inbuf = bulk_read(session, EP_IN2, 2, timeout_ms)
        if not (inbuf[0] == 0x55 and inbuf[1] == 0xAA):
            raise DaqError(
                ErrorCode.PROTOCOL,
                "多通道连续 AD 握手失败，未收到 0x55 0xAA",
                stage="parse",
                card_id=session.card_id,
                bus=session.bus,
                address=session.address,
            )

    results: list[float] = []
    for _ in range(num_sample // 512):
        block = bulk_read(session, EP_IN2, 1024, timeout_ms)
        for i in range(512):
            lo = block[i * 2]
            hi = block[i * 2 + 1]
            results.append(_parse_adc_sample(lo, hi))
    return results


# ─── DA ───────────────────────────────────────────────────────────────────


def da_single_out(session: DeviceSession, chan: int, value: int) -> None:
    cmd = 7 if chan == 1 else 8
    buf = bytearray(10)
    buf[0] = cmd
    buf[8] = value & 0xFF
    buf[9] = (value >> 8) & 0xFF
    bulk_write(session, EP_OUT1, buf, 10)


def da_data_send(session: DeviceSession, chan: int, num: int, databuf: Sequence[int]) -> None:
    if num > 512:
        num = 512
    aa = num // 30
    bb = num % 30
    buf2 = bytearray(64)

    if aa > 0:
        for i in range(aa):
            if chan == 1:
                buf2[2] = (i * 30) & 0xFF
                buf2[3] = ((i * 30) >> 8) & 0xFF
            else:
                buf2[2] = (i * 30 + 512) & 0xFF
                buf2[3] = ((i * 30 + 512) >> 8) & 0xFF
            for j in range(30):
                val = databuf[i * 30 + j]
                buf2[(j << 1) + 4] = val & 0xFF
                buf2[(j << 1) + 5] = (val >> 8) & 0xFF
            buf2[0] = 32
            buf2[1] = 0
            bulk_write(session, EP_OUT1, buf2, 64)

    if bb > 0:
        if chan == 1:
            buf2[2] = (aa * 30) & 0xFF
            buf2[3] = ((aa * 30) >> 8) & 0xFF
        else:
            buf2[2] = (aa * 30 + 512) & 0xFF
            buf2[3] = ((aa * 30 + 512) >> 8) & 0xFF
        for j in range(bb):
            val = databuf[aa * 30 + j]
            buf2[(j << 1) + 4] = val & 0xFF
            buf2[(j << 1) + 5] = (val >> 8) & 0xFF
        buf2[0] = 32
        buf2[1] = 0
        send_len = (bb << 1) + 4
        bulk_write(session, EP_OUT1, bytes(buf2[:send_len]), send_len)


def da_scan_out(session: DeviceSession, chan: int, freq: int, scan_num: int) -> None:
    cmd = 7 if chan == 1 else 8
    buf = bytearray(10)
    buf[0] = cmd
    buf[1] = 1
    buf[2] = scan_num & 0xFF
    buf[3] = (scan_num >> 8) & 0xFF
    buf[4] = freq & 0xFF
    buf[5] = (freq >> 8) & 0xFF
    buf[6] = (freq >> 16) & 0xFF
    buf[7] = (freq >> 24) & 0xFF
    bulk_write(session, EP_OUT1, buf, 10)


# ─── PWM / Count / DO / DI ────────────────────────────────────────────────


def pwm_out_set(session: DeviceSession, chan: int, freq: int, duty_cycle: float) -> None:
    duty_cycle_ = int(duty_cycle * 100)
    cmd = 9 if chan == 1 else 10
    buf = bytes([
        cmd,
        1,
        duty_cycle_ & 0xFF,
        (duty_cycle_ >> 8) & 0xFF,
        freq & 0xFF,
        (freq >> 8) & 0xFF,
        (freq >> 16) & 0xFF,
        (freq >> 24) & 0xFF,
    ])
    bulk_write(session, EP_OUT1, buf, 8)


def pwm_in_set(session: DeviceSession, mod: int) -> None:
    bulk_write(session, EP_OUT1, bytes([11, mod]), 2)


def pwm_in_read(session: DeviceSession) -> tuple[float, int]:
    inbuf = bulk_read(session, EP_IN1, 16)
    inbuf = bulk_read(session, EP_IN1, 16)
    duty = inbuf[1] + (inbuf[2] << 8)
    freq1 = inbuf[3] + (inbuf[4] << 8) + (inbuf[5] << 16) + (inbuf[6] << 24)
    return float(freq1) / 10.0, duty


def count_set(session: DeviceSession, mod: int) -> None:
    bulk_write(session, EP_OUT1, bytes([12, mod]), 2)


def count_read(session: DeviceSession) -> int:
    inbuf = bulk_read(session, EP_IN1, 16)
    inbuf = bulk_read(session, EP_IN1, 16)
    return inbuf[7] + (inbuf[8] << 8) + (inbuf[9] << 16) + (inbuf[10] << 24)


def do_set(session: DeviceSession, chan: int, state: int) -> None:
    bulk_write(session, EP_OUT1, bytes([CMD_DO_SET, chan & 0xFF, state & 0xFF]), 3)


def di_read(session: DeviceSession) -> int:
    inbuf = bulk_read(session, EP_IN1, 16)
    inbuf = bulk_read(session, EP_IN1, 16)
    return inbuf[0]
