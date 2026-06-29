"""COM4 力传感器实时折线图 — pyqtgraph + Modbus RTU 中间层"""
import struct
from collections import deque

import numpy as np
import serial
from pyqtgraph.Qt import QtCore, QtWidgets
import pyqtgraph as pg

import modbus_rtu as mb

# ── 配置 ──────────────────────────────────────────────
PORT = "COM4"
BAUDRATE = 9600
SLAVE_ADDR = 0x01
REG_START = 0x0000
REG_COUNT = 0x000D               # 读 13 个保持寄存器

HISTORY = 500
TIMER_MS = 50

# 6 个 float 通道（偏移量相对于 registers_raw，即去掉 slave/func/byte_count 后）
CHANNELS = [
    (0, "Ch0_Reg0-1"),
    (4, "Ch1_Reg2-3"),
    (8, "Ch2_Reg4-5"),
    (12, "Ch3_Reg6-7"),
    (16, "Ch4_Reg8-9"),
    (20, "Ch5_Reg10-11"),
]
STATUS_OFFSET = 24               # Reg12 uint16, 相对于 registers_raw

COLORS = [
    (0, 200, 255),
    (255, 120, 0),
    (100, 255, 100),
    (255, 60, 60),
    (255, 220, 0),
    (180, 100, 255),
]


# ── Qt GUI ─────────────────────────────────────────────
class ForcePlotApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("力传感器实时多通道监控")
        self.resize(1100, 550)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.status_label = QtWidgets.QLabel("状态: 等待连接...")
        self.status_label.setStyleSheet("font: 14px;")
        layout.addWidget(self.status_label)

        self.plot_widget = pg.GraphicsLayoutWidget()
        layout.addWidget(self.plot_widget)

        self.plot = self.plot_widget.addPlot(title="实时力值 (6 通道)")
        self.plot.setLabel("left", "值")
        self.plot.setLabel("bottom", "采样点")
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.addLegend(offset=(10, 10))

        self.curves = []
        self.buffers = []
        for i, (_, name) in enumerate(CHANNELS):
            pen = pg.mkPen(color=COLORS[i], width=1.5)
            curve = self.plot.plot(pen=pen, name=name)
            self.curves.append(curve)
            self.buffers.append(deque([0.0] * HISTORY, maxlen=HISTORY))

        self.frame_count = 0
        self.err_count = 0
        self.crc_err_count = 0

        # 请求帧（CRC 由中间层自动计算，不再硬编码）
        self.tx_cmd = mb.read_holding_registers(SLAVE_ADDR, REG_START, REG_COUNT)

        try:
            self.ser = serial.Serial(PORT, BAUDRATE, timeout=0.05)
            self.status_label.setText(
                f"串口 {PORT} 已连接 @ {BAUDRATE} bps"
                f"  |  请求帧: {self.tx_cmd.hex(' ').upper()}"
            )
        except Exception as e:
            self.ser = None
            self.status_label.setText(f"串口打开失败: {e}")

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._poll)
        self.timer.start(TIMER_MS)

    # ── 轮询 & 解析 ────────────────────────────────────
    def _poll(self):
        if self.ser is None or not self.ser.is_open:
            return

        try:
            self.ser.reset_input_buffer()
            self.ser.write(self.tx_cmd)
            self.ser.flush()

            # 1) 读响应头 3 字节，获取 byte_count
            header = self.ser.read(3)
            if len(header) < 3:
                self.err_count += 1
                return

            slave, func, byte_count = header[0], header[1], header[2]
            if func != 0x03:
                self.err_count += 1
                return

            # 2) 读剩余部分: byte_count 数据 + 2 字节 CRC
            n_remaining = byte_count + 2
            remaining = self.ser.read(n_remaining)
            if len(remaining) < n_remaining:
                self.err_count += 1
                return

            full_frame = header + remaining

            # 3) 中间层 CRC 校验
            if not mb.verify_frame(full_frame):
                self.crc_err_count += 1
                self.err_count += 1
                return

            registers_raw = full_frame[3 : 3 + byte_count]

            # 4) 解析 6 个 float 通道
            values = [
                struct.unpack(">f", registers_raw[off : off + 4])[0]
                for off, _ in CHANNELS
            ]

            # 5) 状态码
            status = struct.unpack(
                ">H", registers_raw[STATUS_OFFSET : STATUS_OFFSET + 2]
            )[0]

            self.frame_count += 1

            for i, val in enumerate(values):
                self.buffers[i].append(val)
                self.curves[i].setData(list(self.buffers[i]))

            # 状态栏
            parts = [
                f"帧: {self.frame_count}",
                f"状态码: 0x{status:04X}",
            ]
            if self.crc_err_count:
                parts.append(f"CRC错: {self.crc_err_count}")
            io_errs = self.err_count - self.crc_err_count
            if io_errs:
                parts.append(f"IO错: {io_errs}")
            parts.append(
                " | " + " | ".join(
                    f"{name}={v:.3f}" for (_, name), v in zip(CHANNELS, values)
                )
            )
            self.status_label.setText("  ".join(parts))

        except Exception:
            self.err_count += 1

    # ── 窗口关闭清理 ────────────────────────────────────
    def closeEvent(self, event):
        self.timer.stop()
        if self.ser and self.ser.is_open:
            self.ser.close()
        event.accept()


# ── 入口 ───────────────────────────────────────────────
def main():
    app = pg.mkQApp("ForceSensorMonitor")
    win = ForcePlotApp()
    app.aboutToQuit.connect(win.close)
    win.show()
    app.exec_()


if __name__ == "__main__":
    main()
