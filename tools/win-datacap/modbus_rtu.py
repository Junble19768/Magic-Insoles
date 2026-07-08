"""Modbus RTU 中间层 — CRC / 帧构建 / 响应校验 (纯标准库)"""

import struct

# ═══════════════════════════════════════════════════════════
#  CRC-16/MODBUS (查表法，多项式 0xA001)
# ═══════════════════════════════════════════════════════════

_CRC_TABLE = []
for _i in range(256):
    _crc = _i
    for _ in range(8):
        if _crc & 1:
            _crc = (_crc >> 1) ^ 0xA001
        else:
            _crc >>= 1
    _CRC_TABLE.append(_crc)
del _i, _crc


def crc16(data: bytes) -> int:
    """计算 Modbus CRC-16

    Args:
        data: 待校验字节序列（不含 CRC 字段）

    Returns:
        16-bit 无符号整数 (lsw-byte-first 格式，插入帧时写为 [crc&0xFF, crc>>8])
    """
    crc = 0xFFFF
    for b in data:
        crc = (crc >> 8) ^ _CRC_TABLE[(crc ^ b) & 0xFF]
    return crc


# ═══════════════════════════════════════════════════════════
#  帧构建
# ═══════════════════════════════════════════════════════════

def read_holding_registers(
    slave: int, start_addr: int, count: int
) -> bytes:
    """构建功能码 03 (读保持寄存器) 帧

    Args:
        slave:      从站地址 (1-247)
        start_addr: 起始寄存器地址
        count:      读取寄存器数量

    Returns:
        完整 Modbus RTU 帧 (含 CRC)

    Example:
        >>> read_holding_registers(0x01, 0x0000, 0x000D).hex(' ')
        '01 03 00 00 00 0d 84 0f'
    """
    pdu = bytes([slave, 0x03, start_addr >> 8, start_addr & 0xFF, count >> 8, count & 0xFF])
    c = crc16(pdu)
    return pdu + bytes([c & 0xFF, c >> 8])


def write_single_register(slave: int, addr: int, value: int) -> bytes:
    """构建功能码 06 (写单个寄存器) 帧"""
    pdu = bytes([slave, 0x06, addr >> 8, addr & 0xFF, value >> 8, value & 0xFF])
    c = crc16(pdu)
    return pdu + bytes([c & 0xFF, c >> 8])


# ═══════════════════════════════════════════════════════════
#  帧校验 & 解析
# ═══════════════════════════════════════════════════════════

def verify_frame(frame: bytes) -> bool:
    """校验完整 Modbus 帧的 CRC

    帧格式: [slave, func, ...data..., crc_l, crc_h]

    Returns:
        True 表示 CRC 正确
    """
    if len(frame) < 4:
        return False
    expected = struct.unpack("<H", frame[-2:])[0]
    return crc16(frame[:-2]) == expected


def parse_read_response(data: bytes) -> dict | None:
    """解析 功能码 03 响应帧

    响应格式: [slave, 0x03, byte_count, registers..., crc_l, crc_h]

    Returns:
        {
            'slave': int,
            'func': int (0x03),
            'byte_count': int,
            'registers_raw': bytes,   # 原始寄存器数据 (不含头尾)
        }
        帧不完整或 CRC 错误时返回 None
    """
    if len(data) < 5:
        return None

    if not verify_frame(data):
        return None

    slave = data[0]
    func = data[1]
    byte_count = data[2]

    if func != 0x03:
        return None
    if len(data) != 3 + byte_count + 2:
        return None

    registers_raw = data[3 : 3 + byte_count]

    return {
        "slave": slave,
        "func": func,
        "byte_count": byte_count,
        "registers_raw": registers_raw,
    }


# ═══════════════════════════════════════════════════════════
#  高级解析器（应用无关）
# ═══════════════════════════════════════════════════════════

def unpack_registers(raw: bytes, fmt: str) -> tuple:
    """从原始寄存器字节中按格式解包

    Args:
        raw: parse_read_response() 返回的 registers_raw
        fmt: struct.unpack 格式 (默认大端 ">" 前缀)

    Examples:
        >>> raw = b'\\x43\\x48\\x00\\x00'
        >>> unpack_registers(raw, ">f")
        (200.0,)

        >>> raw = b'\\x00\\x0d'
        >>> unpack_registers(raw, ">H")
        (13,)
    """
    if not fmt.startswith((">", "<", "!", "@", "=")):
        fmt = ">" + fmt
    return struct.unpack(fmt, raw)
