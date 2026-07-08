"""Legacy sample: COM4 力传感器实时折线图（pyqtgraph + Modbus RTU）。"""

import struct
from collections import deque

import numpy as np
import pyqtgraph as pg
import serial
from pyqtgraph.Qt import QtCore, QtWidgets

import modbus_rtu as mb

PORT = "COM4"
BAUDRATE = 9600
SLAVE_ADDR = 0x01
REG_START = 0x0000
REG_COUNT = 0x000D

HISTORY = 500
TIMER_MS = 50

CHANNELS = [
    (0, "Ch0_Reg0-1"),
    (4, "Ch1_Reg2-3"),
    (8, "Ch2_Reg4-5"),
    (12, "Ch3_Reg6-7"),
    (16, "Ch4_Reg8-9"),
    (20, "Ch5_Reg10-11"),
]
STATUS_OFFSET = 24

COLORS = [
    (0, 200, 255),
    (255, 120, 0),
    (100, 255, 100),
    (255, 60, 60),
    (255, 220, 0),
    (180, 100, 255),
]


class ForcePlotApp(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("力传感器实时多通道监控 (legacy sample)")
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
            curve = self.plot.plot(pen=pg.mkPen(color=COLORS[i], width=1.5), name=name)
            self.curves.append(curve)
            self.buffers.append(deque([0.0] * HISTORY, maxlen=HISTORY))

        self.frame_count = 0
        self.err_count = 0
        self.crc_err_count = 0
        self.tx_cmd = mb.read_holding_registers(SLAVE_ADDR, REG_START, REG_COUNT)

        try:
            self.ser = serial.Serial(PORT, BAUDRATE, timeout=0.05)
            self.status_label.setText(
                f"串口 {PORT} 已连接 @ {BAUDRATE} bps  |  请求帧: {self.tx_cmd.hex(' ').upper()}"
            )
        except Exception as exc:
            self.ser = None
            self.status_label.setText(f"串口打开失败: {exc}")

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._poll)
        self.timer.start(TIMER_MS)

    def _poll(self) -> None:
        if self.ser is None or not self.ser.is_open:
            return
        try:
            self.ser.reset_input_buffer()
            self.ser.write(self.tx_cmd)
            self.ser.flush()
            header = self.ser.read(3)
            if len(header) < 3:
                self.err_count += 1
                return
            _, func, byte_count = header[0], header[1], header[2]
            if func != 0x03:
                self.err_count += 1
                return
            remaining = self.ser.read(byte_count + 2)
            if len(remaining) < byte_count + 2:
                self.err_count += 1
                return
            full_frame = header + remaining
            if not mb.verify_frame(full_frame):
                self.crc_err_count += 1
                self.err_count += 1
                return

            registers_raw = full_frame[3 : 3 + byte_count]
            values = [struct.unpack(">f", registers_raw[off : off + 4])[0] for off, _ in CHANNELS]
            status = struct.unpack(">H", registers_raw[STATUS_OFFSET : STATUS_OFFSET + 2])[0]

            self.frame_count += 1
            for i, value in enumerate(values):
                self.buffers[i].append(value)
                self.curves[i].setData(list(self.buffers[i]))

            parts = [f"帧: {self.frame_count}", f"状态码: 0x{status:04X}"]
            if self.crc_err_count:
                parts.append(f"CRC错: {self.crc_err_count}")
            io_errs = self.err_count - self.crc_err_count
            if io_errs:
                parts.append(f"IO错: {io_errs}")
            parts.append(" | " + " | ".join(f"{name}={v:.3f}" for (_, name), v in zip(CHANNELS, values)))
            self.status_label.setText("  ".join(parts))
        except Exception:
            self.err_count += 1

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.timer.stop()
        if self.ser and self.ser.is_open:
            self.ser.close()
        event.accept()


def main() -> None:
    app = pg.mkQApp("ForceSensorMonitorLegacy")
    win = ForcePlotApp()
    app.aboutToQuit.connect(win.close)
    win.show()
    app.exec_()


if __name__ == "__main__":
    main()
