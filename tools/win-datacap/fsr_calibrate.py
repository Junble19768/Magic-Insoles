#!/usr/bin/env python3
"""
FSR 标定客户端入口。

保持 `python fsr_calibrate.py` 原有启动方式不变，实际实现已拆分到
`fsr_calibrate/` 包中，便于维护。
"""

from fsr_calibrate.main import main


if __name__ == "__main__":
    main()
