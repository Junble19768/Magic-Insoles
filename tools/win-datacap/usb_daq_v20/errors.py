"""Structured errors for USB-DAQ V20 operations."""

from __future__ import annotations

from enum import Enum
from typing import Optional


class ErrorCode(Enum):
    NOT_OPENED = "NOT_OPENED"
    DEVICE_NOT_FOUND = "DEVICE_NOT_FOUND"
    NO_DAQ_DEVICE = "NO_DAQ_DEVICE"
    DUPLICATE_CARD_ID = "DUPLICATE_CARD_ID"
    OPEN_FAILED = "OPEN_FAILED"
    CLAIM_FAILED = "CLAIM_FAILED"
    INIT_FAILED = "INIT_FAILED"
    ENUMERATE_FAILED = "ENUMERATE_FAILED"
    CARD_ID_READ_FAILED = "CARD_ID_READ_FAILED"
    IO_SHORT_WRITE = "IO_SHORT_WRITE"
    IO_SHORT_READ = "IO_SHORT_READ"
    USB_IO = "USB_IO"
    INVALID_PARAM = "INVALID_PARAM"
    PROTOCOL = "PROTOCOL"
    RESET_FAILED = "RESET_FAILED"


_LIBUSB_HINTS = {
    -1: "USB 通信异常 (IO)，检查线缆/Hub/设备是否掉线",
    -2: "无效参数 (INVALID_PARAM)",
    -3: "权限或驱动不足 (ACCESS)，Windows 请用 Zadig 绑定 WinUSB",
    -4: "设备不存在 (NO_DEVICE)，可能已断开",
    -5: "未找到设备 (NOT_FOUND)",
    -6: "接口已被占用 (BUSY)，请关闭其他占用进程",
    -7: "操作超时 (TIMEOUT)",
    -11: "内存不足 (NO_MEM)",
    -12: "不支持的操作 (NOT_SUPPORTED)",
    -99: "其他 USB 错误 (OTHER)",
}


def libusb_hint(errno: Optional[int]) -> str:
    if errno is None:
        return ""
    return _LIBUSB_HINTS.get(errno, f"libusb errno={errno}")


class DaqError(Exception):
    """Raised when a USB-DAQ operation fails."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        stage: str = "",
        card_id: Optional[int] = None,
        usb_errno: Optional[int] = None,
        endpoint: Optional[int] = None,
        bus: Optional[int] = None,
        address: Optional[int] = None,
        expected: Optional[int] = None,
        actual: Optional[int] = None,
    ):
        self.code = code
        self.stage = stage
        self.message = message
        self.card_id = card_id
        self.usb_errno = usb_errno
        self.endpoint = endpoint
        self.bus = bus
        self.address = address
        self.expected = expected
        self.actual = actual
        super().__init__(self.__str__())

    def __str__(self) -> str:
        parts = [f"[DaqError {self.code.value}]"]
        if self.stage:
            parts[0] += f" stage={self.stage}"
        loc = []
        if self.card_id is not None:
            loc.append(f"CardID=0x{self.card_id:08X}")
        if self.bus is not None:
            loc.append(f"bus={self.bus}")
        if self.address is not None:
            loc.append(f"addr={self.address}")
        if loc:
            parts.append(" ".join(loc) + ":")
        parts.append(self.message)
        if self.usb_errno is not None:
            hint = libusb_hint(self.usb_errno)
            if hint:
                parts.append(f"({hint})")
        if self.endpoint is not None:
            parts.append(f"[EP=0x{self.endpoint:02X}]")
        if self.expected is not None and self.actual is not None:
            parts.append(f"[expected={self.expected} actual={self.actual}]")
        return " ".join(parts)
