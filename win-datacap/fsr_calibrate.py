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
from queue import Empty, SimpleQueue
from typing import Any

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
UI_TIMER_MS = 16
PLOT_WINDOW_S = 5.0
STATUS_UPDATE_INTERVAL_S = 0.2
CSV_FLUSH_EVERY_ROWS = 20
# 压力锚点保留时长；FSR 帧在队列中等待后时间戳可能略早于当前锚点窗口
FORCE_ANCHOR_WINDOW_S = 60.0
FORCE_INTERP_MAX_SKEW_S = 2.0

FORCE_CHANNEL_NAME = "Ch0_Reg0-1"

RECORD_DIR = Path(__file__).resolve().parent / "record"


def can_interp_force(fsr_stamp: float, anchor_t: np.ndarray) -> bool:
    if len(anchor_t) < 2:
        return False
    t_min, t_max = float(anchor_t[0]), float(anchor_t[-1])
    if t_min <= fsr_stamp <= t_max:
        return True
    # FSR 在队列中等待时锚点窗口已前移，允许小范围外推
    skew = FORCE_INTERP_MAX_SKEW_S
    return (t_min - skew) <= fsr_stamp <= (t_max + skew)


def interp_force_at(
    fsr_stamp: float, anchor_t: np.ndarray, anchor_v: np.ndarray
) -> float:
    return float(np.interp(fsr_stamp, anchor_t, anchor_v))


def _csv_header() -> list[str]:
    cols = ["timestamp"]
    cols.extend(f"fsr_{i:02d}" for i in range(32))
    cols.append("force_ch0")
    return cols


class CsvRecorder:
    """按 FSR 帧节拍写入 CSV，文件名取开始录制时的系统时间。"""

    def __init__(self):
        self._file = None
        self._writer: Any | None = None
        self._path: Path | None = None
        self._last_fsr_stamp: float | None = None
        self._row_count = 0
        self._pending_flush = 0

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
        self._pending_flush = 0
        print(f"录制开始: {self._path}")
        return self._path

    def stop(self) -> int:
        if not self.is_active:
            return 0
        count = self._row_count
        path = self._path
        if self._file is not None:
            self._file.flush()
            self._file.close()
        self._file = None
        self._writer = None
        self._last_fsr_stamp = None
        print(f"录制结束: {path} ({count} 行)")
        return count

    def write_row(
        self,
        fsr_stamp: float,
        fsr_data: np.ndarray,
        force_value: float,
    ) -> bool:
        if not self.is_active or self._writer is None:
            return False
        if self._last_fsr_stamp is not None and fsr_stamp == self._last_fsr_stamp:
            return False
        self._last_fsr_stamp = fsr_stamp
        row: list[float | str | int] = [fsr_stamp]
        row.extend(float(fsr_data[i]) for i in range(32))
        row.append(float(force_value))
        self._writer.writerow(row)
        self._pending_flush += 1
        if self._pending_flush >= CSV_FLUSH_EVERY_ROWS and self._file is not None:
            self._file.flush()
            self._pending_flush = 0
        self._row_count += 1
        return True


class AlignPipeline:
    """后台对齐管道：去重推拉力锚点，仅对可插值 FSR 时间戳写 CSV。"""

    def __init__(self):
        self._queue: SimpleQueue = SimpleQueue()
        self._lock = threading.Lock()
        self._anchors: deque[tuple[float, float]] = deque()
        self._recorder = CsvRecorder()
        self._record_path: Path | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def update_force(self, stamp: float, value: float) -> None:
        """压力采样在采集线程直接更新锚点，避免 ~kHz 入队淹没 FSR 事件。"""
        with self._lock:
            if self._anchors and value == self._anchors[-1][1]:
                return
            self._anchors.append((stamp, value))
            self._prune_anchors_locked(stamp)

    def enqueue_fsr(self, stamp: float, data: np.ndarray) -> None:
        self._queue.put(("fsr", stamp, data.copy()))

    def request_start_record(self) -> Path:
        done = threading.Event()
        result: dict[str, Path | None] = {"path": None}
        self._queue.put(("start_record", done, result))
        done.wait(timeout=5.0)
        path = result["path"]
        if path is None:
            raise RuntimeError("录制启动超时")
        return path

    def request_stop_record(self) -> int:
        done = threading.Event()
        result: dict[str, int] = {"count": 0}
        self._queue.put(("stop_record", done, result))
        done.wait(timeout=5.0)
        return result["count"]

    def clear_anchors(self) -> None:
        self._queue.put(("clear",))

    def shutdown(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2.0)

    def snapshot(self) -> tuple[list[tuple[float, float]], Path | None, bool, int]:
        with self._lock:
            return (
                list(self._anchors),
                self._record_path,
                self._recorder.is_active,
                self._recorder.row_count,
            )

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=0.1)
            except Empty:
                continue
            self._dispatch(item)

    def _prune_anchors_locked(self, now: float) -> None:
        cutoff = now - FORCE_ANCHOR_WINDOW_S
        while self._anchors and self._anchors[0][0] < cutoff:
            self._anchors.popleft()
        while len(self._anchors) > HISTORY:
            self._anchors.popleft()

    def _dispatch(self, item: tuple) -> None:
        kind = item[0]
        if kind == "fsr":
            _, stamp, data = item
            self._on_fsr(stamp, data)
        elif kind == "start_record":
            _, done, result = item
            path = self._recorder.start()
            with self._lock:
                self._record_path = path
            result["path"] = path
            done.set()
        elif kind == "stop_record":
            _, done, result = item
            count = self._recorder.stop()
            with self._lock:
                if not self._recorder.is_active:
                    self._record_path = None
            result["count"] = count
            done.set()
        elif kind == "clear":
            with self._lock:
                self._anchors.clear()

    def _on_fsr(self, stamp: float, data: np.ndarray) -> None:
        with self._lock:
            anchors = list(self._anchors)
            recording = self._recorder.is_active
        if not can_interp_force(stamp, np.asarray([a[0] for a in anchors])):
            return
        anchor_t = np.asarray([a[0] for a in anchors], dtype=float)
        anchor_v = np.asarray([a[1] for a in anchors], dtype=float)
        force_value = interp_force_at(stamp, anchor_t, anchor_v)
        if recording:
            self._recorder.write_row(stamp, data, force_value)


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
        self.force_values = [0.0]
        self.force_stamp = 0.0
        self.force_connected = False

    def set_fsr(self, data: np.ndarray, stamp: float):
        with self._lock:
            self.fsr_data = data.copy()
            self.fsr_stamp = stamp
            self.fsr_connected = True

    def set_force(self, values: list, stamp: float):
        with self._lock:
            self.force_values = list(values)
            self.force_stamp = stamp
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
            )


def _fsr_reader(
    hub: DataHub, pipeline: AlignPipeline, stop_event: threading.Event
):
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
                fsr_data = np.array(values[:32], dtype=float)
                fsr_stamp = values[32]
                hub.set_fsr(fsr_data, fsr_stamp)
                pipeline.enqueue_fsr(fsr_stamp, fsr_data)
        except OSError as e:
            with hub._lock:
                hub.fsr_connected = False
            print(f"FSR 连接失败，1 秒后重试: {e}")
            time.sleep(1.0)
        finally:
            sock.close()


async def _force_ws_loop(
    hub: DataHub, pipeline: AlignPipeline, stop_event: threading.Event
):
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
                    stamp = float(payload.get("timestamp", time.time()))
                    value = float(values[0])
                    hub.set_force([value], stamp)
                    pipeline.update_force(stamp, value)
        except Exception as e:
            with hub._lock:
                hub.force_connected = False
            print(f"压力 WebSocket 断开，1 秒后重试: {e}")
            await asyncio.sleep(1.0)


def _force_reader_thread(
    hub: DataHub, pipeline: AlignPipeline, stop_event: threading.Event
):
    asyncio.run(_force_ws_loop(hub, pipeline, stop_event))


class FsrCalibrateApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FSR 标定 — 压力 vs ADC")
        self.resize(1200, 620)

        self.hub = DataHub()
        self.pipeline = AlignPipeline()
        self._stop = threading.Event()
        threading.Thread(
            target=_fsr_reader,
            args=(self.hub, self.pipeline, self._stop),
            daemon=True,
        ).start()
        threading.Thread(
            target=_force_reader_thread,
            args=(self.hub, self.pipeline, self._stop),
            daemon=True,
        ).start()

        self.fsr_channel = 0
        self._t_origin: float | None = None
        self._last_fsr_stamp = -1.0
        self._last_anchor_count = 0
        self._last_status_update = 0.0
        self._ui_fps_count = 0
        self._last_ui_fps_report = time.monotonic()
        self._ui_fps = 0.0

        self.adc_t_buf: deque[float] = deque(maxlen=HISTORY)
        self.adc_v_buf: deque[float] = deque(maxlen=HISTORY)
        self.force_t_buf: deque[float] = deque(maxlen=HISTORY)
        self.force_v_buf: deque[float] = deque(maxlen=HISTORY)

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
        ctrl.addWidget(QtWidgets.QLabel(f"压力: {FORCE_CHANNEL_NAME}"))

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
        self.plot.setLabel("bottom", "时间 (s)")
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
            name="参考压力(实测)",
        )
        self.force_interp_curve = pg.PlotCurveItem(
            pen=pg.mkPen(color=(255, 180, 0), width=2, style=QtCore.Qt.DashLine),
            name="参考压力(插值@FSR)",
        )
        self.force_view.addItem(self.force_curve)
        self.force_view.addItem(self.force_interp_curve)

        def _sync_views():
            self.force_view.setGeometry(self.plot.vb.sceneBoundingRect())
            self.force_view.linkedViewChanged(self.plot.vb, self.force_view.XAxis)

        self.plot.vb.sigResized.connect(_sync_views)
        _sync_views()
        self.plot.enableAutoRange(axis="x", enable=False)
        self.plot.enableAutoRange(axis="y", enable=False)
        self.force_view.enableAutoRange(axis="y", enable=False)
        self.plot.setXRange(0, PLOT_WINDOW_S, padding=0)

        self.timer = QtCore.QTimer()
        self.timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(UI_TIMER_MS)

    def _rel_time(self, stamp: float) -> float:
        if self._t_origin is None:
            self._t_origin = stamp
        return stamp - self._t_origin

    def _window_bounds(self) -> tuple[float, float]:
        if self._t_origin is None:
            return 0.0, PLOT_WINDOW_S
        t_now = time.time() - self._t_origin
        win_end = max(PLOT_WINDOW_S, t_now)
        return win_end - PLOT_WINDOW_S, win_end

    def _series_for_window(
        self,
        t_buf: deque[float],
        v_buf: deque[float],
        win_start: float,
        win_end: float,
    ) -> tuple[list[float], list[float]]:
        """仅返回窗口内真实采样点，无数据则不绘制。"""
        xs: list[float] = []
        ys: list[float] = []
        for t, v in zip(t_buf, v_buf):
            if win_start <= t <= win_end:
                xs.append(t)
                ys.append(v)
        return xs, ys

    def _interp_force_at_fsr_times(
        self,
        fsr_t_buf: deque[float],
        force_t_buf: deque[float],
        force_v_buf: deque[float],
        win_start: float,
        win_end: float,
    ) -> tuple[list[float], list[float]]:
        """在 FSR 时间戳上对推拉力实测值做线性插值。"""
        fsr_x = [t for t in fsr_t_buf if win_start <= t <= win_end]
        if len(fsr_x) < 1 or len(force_t_buf) < 2:
            return [], []

        ft = np.asarray(force_t_buf, dtype=float)
        fv = np.asarray(force_v_buf, dtype=float)
        fsr_t = np.asarray(fsr_x, dtype=float)
        t_min, t_max = float(ft[0]), float(ft[-1])
        mask = (fsr_t >= t_min) & (fsr_t <= t_max)
        if not np.any(mask):
            return [], []

        interp_t = fsr_t[mask]
        interp_v = np.interp(interp_t, ft, fv)
        return interp_t.tolist(), interp_v.tolist()

    def _apply_y_range(self, viewbox: pg.ViewBox, values: list[float]) -> None:
        """按当前窗口内真实采样值自动缩放 Y 轴。"""
        if not values:
            viewbox.setYRange(-0.01, 0.01, padding=0)
            return
        lo, hi = min(values), max(values)
        if lo == hi:
            pad = max(abs(lo) * 0.1, 0.01)
            viewbox.setYRange(lo - pad, hi + pad, padding=0)
            return
        margin = (hi - lo) * 0.1
        viewbox.setYRange(lo - margin, hi + margin, padding=0)

    def _update_plot(self) -> None:
        win_start, win_end = self._window_bounds()
        adc_x, adc_y = self._series_for_window(
            self.adc_t_buf, self.adc_v_buf, win_start, win_end
        )
        force_x, force_y = self._series_for_window(
            self.force_t_buf, self.force_v_buf, win_start, win_end
        )
        interp_x, interp_y = self._interp_force_at_fsr_times(
            self.adc_t_buf, self.force_t_buf, self.force_v_buf, win_start, win_end
        )
        self.adc_curve.setData(adc_x, adc_y)
        self.force_curve.setData(force_x, force_y)
        self.force_interp_curve.setData(interp_x, interp_y)
        self.plot.setXRange(win_start, win_end, padding=0)
        self._apply_y_range(self.plot.vb, adc_y)
        self._apply_y_range(self.force_view, force_y + interp_y)

    def _sync_force_from_pipeline(self, anchors: list[tuple[float, float]]) -> None:
        self.force_t_buf.clear()
        self.force_v_buf.clear()
        for stamp, value in anchors:
            self.force_t_buf.append(self._rel_time(stamp))
            self.force_v_buf.append(value)

    def _on_fsr_changed(self, index: int):
        self.fsr_channel = self.fsr_combo.itemData(index)
        self._clear_buffers()

    def _clear_buffers(self):
        self.adc_t_buf.clear()
        self.adc_v_buf.clear()
        self.force_t_buf.clear()
        self.force_v_buf.clear()
        self.pipeline.clear_anchors()
        self._t_origin = None
        self._last_fsr_stamp = -1.0
        self._last_anchor_count = 0
        self.plot.setXRange(0, PLOT_WINDOW_S, padding=0)
        self._update_plot()

    def _on_start_record(self):
        path = self.pipeline.request_start_record()
        self.start_record_btn.setEnabled(False)
        self.stop_record_btn.setEnabled(True)
        print(f"录制文件: record/{path.name}")

    def _on_stop_record(self):
        count = self.pipeline.request_stop_record()
        self.start_record_btn.setEnabled(True)
        self.stop_record_btn.setEnabled(False)
        print(f"已保存 {count} 行")

    def _refresh(self):
        fsr_data, fsr_stamp, fsr_ok, force_values, force_stamp, force_ok = (
            self.hub.snapshot()
        )
        anchors, record_path, recording, row_count = self.pipeline.snapshot()

        data_changed = False
        if fsr_ok and fsr_stamp != self._last_fsr_stamp:
            self.adc_t_buf.append(self._rel_time(fsr_stamp))
            self.adc_v_buf.append(float(fsr_data[self.fsr_channel]))
            self._last_fsr_stamp = fsr_stamp
            data_changed = True
        if len(anchors) != self._last_anchor_count:
            self._sync_force_from_pipeline(anchors)
            self._last_anchor_count = len(anchors)
            data_changed = True

        self._update_plot()
        if data_changed:
            self._ui_fps_count += 1

        now = time.monotonic()
        if now - self._last_ui_fps_report >= 1.0:
            elapsed = now - self._last_ui_fps_report
            self._ui_fps = self._ui_fps_count / elapsed if elapsed > 0 else 0.0
            self._ui_fps_count = 0
            self._last_ui_fps_report = now

        if now - self._last_status_update >= STATUS_UPDATE_INTERVAL_S:
            fsr_state = "已连接" if fsr_ok else "未连接"
            force_state = "已连接" if force_ok else "未连接"
            adc_now = fsr_data[self.fsr_channel] if fsr_ok else float("nan")
            force_now = (
                self.force_v_buf[-1]
                if self.force_v_buf
                else (
                    force_values[0]
                    if force_ok and len(force_values) >= 1
                    else float("nan")
                )
            )
            skew_ms = (
                abs(fsr_stamp - force_stamp) * 1000.0
                if fsr_ok and force_ok
                else float("nan")
            )
            parts = [
                f"FSR TCP ({FSR_HOST}:{FSR_PORT}): {fsr_state}",
                f"压力 WS ({FORCE_WS_URL}): {force_state}",
                f"当前 FSR[{self.fsr_channel}] ADC={adc_now:.4f} V",
                f"当前压力={force_now:.3f} N",
                f"时间偏差={skew_ms:.0f} ms" if fsr_ok and force_ok else "时间偏差=—",
                f"UI FPS={self._ui_fps:.1f}",
            ]
            if recording and record_path is not None:
                parts.append(
                    f"录制中 → record/{record_path.name} ({row_count} 行)"
                )
            self.status_label.setText("  |  ".join(parts))
            self._last_status_update = now

    def closeEvent(self, event):
        self.timer.stop()
        _, record_path, recording, _ = self.pipeline.snapshot()
        if recording:
            count = self.pipeline.request_stop_record()
            if record_path is not None:
                print(f"窗口关闭，录制已自动保存: {record_path} ({count} 行)")
        self._stop.set()
        self.pipeline.shutdown()
        event.accept()


def main():
    app = pg.mkQApp("FsrCalibrate")
    win = FsrCalibrateApp()
    app.aboutToQuit.connect(win.close)
    win.show()
    app.exec_()


if __name__ == "__main__":
    main()
