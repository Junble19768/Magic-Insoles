#!/usr/bin/env python3
"""
FSR 标定客户端：同时订阅 USB-DAQ FSR（TCP）与 Modbus 压力传感器（WebSocket），
在同一曲线图中对比 ADC 电压与参考压力值。

用法：
  1. python server.py          # FSR 数据源
  2. python force_server.py    # 压力传感器 WebSocket 源
  3. python fsr_calibrate.py   # 本脚本
"""

import asyncio
import csv
import json
import struct
import socket
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import numpy as np
from pyqtgraph.Qt import QtCore, QtWidgets
import pyqtgraph as pg

try:
    import websockets
except ImportError as exc:
    raise SystemExit("请先安装 websockets: pip install websockets") from exc

# ── 连接配置 ───────────────────────────────────────────────
FSR_HOST = "127.0.0.1"
FSR_PORT = 6543
FSR_PACKET_SIZE = 320

FORCE_WS_URL = "ws://127.0.0.1:8765"

HISTORY = 500
UI_TIMER_MS = 50

FORCE_CHANNEL_NAMES = [
    "Ch0_Reg0-1",
    "Ch1_Reg2-3",
    "Ch2_Reg4-5",
    "Ch3_Reg6-7",
    "Ch4_Reg8-9",
    "Ch5_Reg10-11",
]

RECORD_DIR = Path(__file__).resolve().parent / "record"


def _csv_header() -> list[str]:
    cols = ["timestamp"]
    cols.extend(f"fsr_{i:02d}" for i in range(32))
    cols.extend(f"force_ch{i}" for i in range(len(FORCE_CHANNEL_NAMES)))
    cols.append("force_status")
    return cols


class CsvRecorder:
    """按 FSR 帧节拍写入 CSV，文件名取开始录制时的系统时间。"""

    def __init__(self):
        self._file = None
        self._writer: csv.writer | None = None
        self._path: Path | None = None
        self._last_fsr_stamp: float | None = None
        self._row_count = 0

    @property
    def is_active(self) -> bool:
        return self._file is not None

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def row_count(self) -> int:
        return self._row_count

    def start(self) -> Path:
        if self.is_active:
            return self._path  # type: ignore[return-value]
        RECORD_DIR.mkdir(parents=True, exist_ok=True)
        name = datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"
        self._path = RECORD_DIR / name
        self._file = open(self._path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        self._writer.writerow(_csv_header())
        self._last_fsr_stamp = None
        self._row_count = 0
        print(f"录制开始: {self._path}")
        return self._path

    def stop(self) -> int:
        if not self.is_active:
            return 0
        count = self._row_count
        path = self._path
        self._file.close()
        self._file = None
        self._writer = None
        self._last_fsr_stamp = None
        print(f"录制结束: {path} ({count} 行)")
        return count

    def write_if_new(
        self,
        fsr_data: np.ndarray,
        fsr_stamp: float,
        force_values: list[float],
        force_status: int,
        force_ok: bool,
    ) -> bool:
        if not self.is_active or self._writer is None:
            return False
        if self._last_fsr_stamp is not None and fsr_stamp == self._last_fsr_stamp:
            return False
        self._last_fsr_stamp = fsr_stamp
        row: list[float | str | int] = [fsr_stamp]
        row.extend(float(fsr_data[i]) for i in range(32))
        if force_ok and len(force_values) >= len(FORCE_CHANNEL_NAMES):
            row.extend(float(force_values[i]) for i in range(len(FORCE_CHANNEL_NAMES)))
            row.append(force_status)
        else:
            row.extend([""] * len(FORCE_CHANNEL_NAMES))
            row.append("")
        self._writer.writerow(row)
        self._file.flush()
        self._row_count += 1
        return True


def _fsr_label(index: int) -> str:
    foot = "左脚" if index < 16 else "右脚"
    local = index % 16
    return f"FSR {index:02d} ({foot} #{local})"


class DataHub:
    """后台线程写入，UI 线程读取的最新采样缓存。"""

    def __init__(self):
        self._lock = threading.Lock()
        self.fsr_data = np.zeros(32, dtype=float)
        self.fsr_stamp = 0.0
        self.fsr_connected = False
        self.force_values = [0.0] * len(FORCE_CHANNEL_NAMES)
        self.force_stamp = 0.0
        self.force_connected = False
        self.force_status = 0

    def set_fsr(self, data: np.ndarray, stamp: float):
        with self._lock:
            self.fsr_data = data.copy()
            self.fsr_stamp = stamp
            self.fsr_connected = True

    def set_force(self, values: list, stamp: float, status: int):
        with self._lock:
            self.force_values = list(values)
            self.force_stamp = stamp
            self.force_status = status
            self.force_connected = True

    def snapshot(self):
        with self._lock:
            return (
                self.fsr_data.copy(),
                self.fsr_stamp,
                self.fsr_connected,
                list(self.force_values),
                self.force_stamp,
                self.force_connected,
                self.force_status,
            )


def _fsr_reader(hub: DataHub, stop_event: threading.Event):
    while not stop_event.is_set():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((FSR_HOST, FSR_PORT))
            sock.settimeout(1.0)
            print(f"FSR 已连接 {FSR_HOST}:{FSR_PORT}")
            buf = b""
            while not stop_event.is_set():
                try:
                    chunk = sock.recv(FSR_PACKET_SIZE - len(buf))
                except socket.timeout:
                    continue
                if not chunk:
                    break
                buf += chunk
                if len(buf) < FSR_PACKET_SIZE:
                    continue
                packet, buf = buf[:FSR_PACKET_SIZE], buf[FSR_PACKET_SIZE:]
                values = struct.unpack("40d", packet)
                hub.set_fsr(np.array(values[:32], dtype=float), values[32])
        except OSError as e:
            with hub._lock:
                hub.fsr_connected = False
            print(f"FSR 连接失败，1 秒后重试: {e}")
            time.sleep(1.0)
        finally:
            sock.close()


async def _force_ws_loop(hub: DataHub, stop_event: threading.Event):
    while not stop_event.is_set():
        try:
            async with websockets.connect(FORCE_WS_URL) as ws:
                print(f"压力传感器已连接 {FORCE_WS_URL}")
                async for msg in ws:
                    if stop_event.is_set():
                        break
                    payload = json.loads(msg)
                    values = payload.get("values", [])
                    if not values:
                        continue
                    hub.set_force(
                        [float(v) for v in values],
                        float(payload.get("timestamp", time.time())),
                        int(payload.get("status", 0)),
                    )
        except Exception as e:
            with hub._lock:
                hub.force_connected = False
            print(f"压力 WebSocket 断开，1 秒后重试: {e}")
            await asyncio.sleep(1.0)


def _force_reader_thread(hub: DataHub, stop_event: threading.Event):
    asyncio.run(_force_ws_loop(hub, stop_event))


class FsrCalibrateApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FSR 标定 — 压力 vs ADC")
        self.resize(1200, 620)

        self.hub = DataHub()
        self._stop = threading.Event()
        threading.Thread(
            target=_fsr_reader, args=(self.hub, self._stop), daemon=True
        ).start()
        threading.Thread(
            target=_force_reader_thread, args=(self.hub, self._stop), daemon=True
        ).start()

        self.force_channel = 0
        self.fsr_channel = 0

        self.adc_buf = deque([0.0] * HISTORY, maxlen=HISTORY)
        self.force_buf = deque([0.0] * HISTORY, maxlen=HISTORY)
        self.recorder = CsvRecorder()

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)

        # ── 控制栏 ─────────────────────────────────────────
        ctrl = QtWidgets.QHBoxLayout()

        ctrl.addWidget(QtWidgets.QLabel("FSR 通道:"))
        self.fsr_combo = QtWidgets.QComboBox()
        for i in range(32):
            self.fsr_combo.addItem(_fsr_label(i), i)
        self.fsr_combo.currentIndexChanged.connect(self._on_fsr_changed)
        ctrl.addWidget(self.fsr_combo)

        ctrl.addSpacing(20)
        ctrl.addWidget(QtWidgets.QLabel("压力通道:"))
        self.force_combo = QtWidgets.QComboBox()
        for i, name in enumerate(FORCE_CHANNEL_NAMES):
            self.force_combo.addItem(name, i)
        self.force_combo.currentIndexChanged.connect(self._on_force_changed)
        ctrl.addWidget(self.force_combo)

        self.clear_btn = QtWidgets.QPushButton("清空曲线")
        self.clear_btn.clicked.connect(self._clear_buffers)
        ctrl.addWidget(self.clear_btn)

        ctrl.addSpacing(20)
        self.start_record_btn = QtWidgets.QPushButton("开始录制")
        self.start_record_btn.clicked.connect(self._on_start_record)
        ctrl.addWidget(self.start_record_btn)

        self.stop_record_btn = QtWidgets.QPushButton("停止录制")
        self.stop_record_btn.clicked.connect(self._on_stop_record)
        self.stop_record_btn.setEnabled(False)
        ctrl.addWidget(self.stop_record_btn)

        ctrl.addStretch()
        root.addLayout(ctrl)

        self.status_label = QtWidgets.QLabel("状态: 等待连接...")
        self.status_label.setStyleSheet("font: 13px;")
        root.addWidget(self.status_label)

        # ── 双 Y 轴曲线（同一图）────────────────────────────
        self.plot_widget = pg.GraphicsLayoutWidget()
        root.addWidget(self.plot_widget)

        self.plot = self.plot_widget.addPlot(title="FSR ADC vs 参考压力")
        self.plot.setLabel("bottom", "采样点")
        self.plot.setLabel("left", "ADC 电压 (V)", color="#0080FF")
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.addLegend(offset=(10, 10))

        self.force_view = pg.ViewBox()
        self.plot.showAxis("right")
        self.plot.scene().addItem(self.force_view)
        self.plot.getAxis("right").linkToView(self.force_view)
        self.force_view.setXLink(self.plot)
        self.plot.getAxis("right").setLabel("压力值", color="#FF6600")

        self.adc_curve = self.plot.plot(
            pen=pg.mkPen(color=(0, 128, 255), width=2),
            name="FSR ADC (V)",
        )
        self.force_curve = pg.PlotCurveItem(
            pen=pg.mkPen(color=(255, 102, 0), width=2),
            name="参考压力",
        )
        self.force_view.addItem(self.force_curve)

        def _sync_views():
            self.force_view.setGeometry(self.plot.vb.sceneBoundingRect())
            self.force_view.linkedViewChanged(self.plot.vb, self.force_view.XAxis)

        self.plot.vb.sigResized.connect(_sync_views)
        _sync_views()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._refresh)
        self.timer.start(UI_TIMER_MS)

    def _on_fsr_changed(self, index: int):
        self.fsr_channel = self.fsr_combo.itemData(index)
        self._clear_buffers()

    def _on_force_changed(self, index: int):
        self.force_channel = self.force_combo.itemData(index)
        self._clear_buffers()

    def _clear_buffers(self):
        self.adc_buf.clear()
        self.force_buf.clear()
        for _ in range(HISTORY):
            self.adc_buf.append(0.0)
            self.force_buf.append(0.0)

    def _on_start_record(self):
        path = self.recorder.start()
        self.start_record_btn.setEnabled(False)
        self.stop_record_btn.setEnabled(True)
        print(f"录制文件: record/{path.name}")

    def _on_stop_record(self):
        count = self.recorder.stop()
        self.start_record_btn.setEnabled(True)
        self.stop_record_btn.setEnabled(False)
        print(f"已保存 {count} 行")

    def _refresh(self):
        fsr_data, fsr_stamp, fsr_ok, force_values, force_stamp, force_ok, status = (
            self.hub.snapshot()
        )

        if self.recorder.is_active and fsr_ok:
            self.recorder.write_if_new(
                fsr_data, fsr_stamp, force_values, status, force_ok
            )

        if fsr_ok:
            self.adc_buf.append(float(fsr_data[self.fsr_channel]))
        if force_ok and self.force_channel < len(force_values):
            self.force_buf.append(float(force_values[self.force_channel]))

        x = list(range(len(self.adc_buf)))
        self.adc_curve.setData(x, list(self.adc_buf))
        self.force_curve.setData(x, list(self.force_buf))

        fsr_state = "已连接" if fsr_ok else "未连接"
        force_state = "已连接" if force_ok else "未连接"
        adc_now = fsr_data[self.fsr_channel] if fsr_ok else float("nan")
        force_now = (
            force_values[self.force_channel]
            if force_ok and self.force_channel < len(force_values)
            else float("nan")
        )
        parts = [
            f"FSR TCP ({FSR_HOST}:{FSR_PORT}): {fsr_state}",
            f"压力 WS ({FORCE_WS_URL}): {force_state}",
            f"当前 FSR[{self.fsr_channel}] ADC={adc_now:.4f} V",
            f"当前压力[{self.force_channel}]={force_now:.3f}",
            f"状态码=0x{status:04X}",
        ]
        if self.recorder.is_active and self.recorder.path is not None:
            parts.append(
                f"录制中 → record/{self.recorder.path.name} "
                f"({self.recorder.row_count} 行)"
            )
        self.status_label.setText("  |  ".join(parts))

    def closeEvent(self, event):
        self.timer.stop()
        if self.recorder.is_active:
            count = self.recorder.stop()
            path = self.recorder.path
            if path is not None:
                print(f"窗口关闭，录制已自动保存: {path} ({count} 行)")
        self._stop.set()
        event.accept()


def main():
    app = pg.mkQApp("FsrCalibrate")
    win = FsrCalibrateApp()
    app.aboutToQuit.connect(win.close)
    win.show()
    app.exec_()


if __name__ == "__main__":
    main()
