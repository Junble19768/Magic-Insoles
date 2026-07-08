#!/usr/bin/env python3
"""
FSR 标定采集入口（ADC 折线图 + CSV 录制）。

另见：
  fsr_calibrate_reference.py — 标定结果参考（同轴压力 + 残差）
  fsr_visualize.py           — 脚型热力图 + 重心 (COP)
"""

from fsr_calibrate.main import main


if __name__ == "__main__":
    main()
