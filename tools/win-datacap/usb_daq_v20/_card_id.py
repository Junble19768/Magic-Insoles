"""Read and parse Card ID from EP_IN1 (GetCardIdV20)."""

from __future__ import annotations

import usb.core

from .constants import CARD_ID_READ_SIZE, EP_IN1, PACKET_TIMEOUT_MS
from .errors import DaqError, ErrorCode


def parse_card_id(inbuf: bytes) -> int:
    if len(inbuf) < CARD_ID_READ_SIZE:
        raise DaqError(
            ErrorCode.CARD_ID_READ_FAILED,
            f"Card ID 响应长度不足: {len(inbuf)} < {CARD_ID_READ_SIZE}",
            stage="parse",
        )
    return (
        inbuf[12]
        | (inbuf[13] << 8)
        | (inbuf[14] << 16)
        | (inbuf[15] << 24)
    )


def read_card_id(dev: usb.core.Device) -> int:
    """Read Card ID from an open, claimed device."""
    try:
        inbuf = bytes(dev.read(EP_IN1, CARD_ID_READ_SIZE, timeout=PACKET_TIMEOUT_MS))
    except usb.core.USBError as e:
        raise DaqError(
            ErrorCode.CARD_ID_READ_FAILED,
            "读取 Card ID 失败",
            stage="bulk_read",
            usb_errno=getattr(e, "errno", None),
            endpoint=EP_IN1,
        ) from e
    return parse_card_id(inbuf)
