import threading
import time
from collections import deque
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

from .calibration_store import CalibrationStore
from .config import DEFAULT_CALIB_YAML, FORCE_CHANNEL_NAME, FORCE_WS_URL, FSR_HOST, FSR_PORT, HISTORY, MODEL_UI_TO_YAML, PLOT_WINDOW_S, STATUS_UPDATE_INTERVAL_S, UI_TIMER_MS
from .heatmap import FootPressurePanel
from .io_readers import force_reader_thread, fsr_reader
from .pipeline import AlignPipeline


def fsr_label(index: int) -> str:
    foot = "左脚" if index < 16 else "右脚"
    return f"FSR {index:02d} ({foot} #{index % 16})"


class DataHub:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.fsr_data = np.zeros(32, dtype=float)
        self.fsr_stamp = 0.0
        self.fsr_connected = False
        self.force_values = [0.0]
        self.force_stamp = 0.0
        self.force_connected = False

    def set_fsr(self, data: np.ndarray, stamp: float) -> None:
        with self._lock:
            self.fsr_data = data.copy()
            self.fsr_stamp = stamp
            self.fsr_connected = True

    def set_force(self, values: list[float], stamp: float) -> None:
        with self._lock:
            self.force_values = list(values)
            self.force_stamp = stamp
            self.force_connected = True

    def set_fsr_disconnected(self) -> None:
        with self._lock:
            self.fsr_connected = False

    def set_force_disconnected(self) -> None:
        with self._lock:
            self.force_connected = False

    def snapshot(self) -> tuple[np.ndarray, float, bool, list[float], float, bool]:
        with self._lock:
            return (
                self.fsr_data.copy(),
                self.fsr_stamp,
                self.fsr_connected,
                list(self.force_values),
                self.force_stamp,
                self.force_connected,
            )


class FsrCalibrateApp(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FSR 标定 — 压力 vs ADC")
        self.resize(1400, 720)

        self.calibration = CalibrationStore()
        self._model_key = MODEL_UI_TO_YAML["幂函数"]
        self._use_pressure_mode = False

        self.hub = DataHub()
        self.pipeline = AlignPipeline()
        self._stop = threading.Event()
        threading.Thread(target=fsr_reader, args=(self.hub, self.pipeline, self._stop), daemon=True).start()
        threading.Thread(target=force_reader_thread, args=(self.hub, self.pipeline, self._stop), daemon=True).start()

        self.fsr_channel = 0
        self._t_origin: float | None = None
        self._last_fsr_stamp = -1.0
        self._last_status_update = 0.0
        self._ui_fps_count = 0
        self._last_ui_fps_report = time.monotonic()
        self._ui_fps = 0.0
        self._force_interp_now = float("nan")

        self.adc_t_buf: deque[float] = deque(maxlen=HISTORY)
        self.adc_v_buf: deque[float] = deque(maxlen=HISTORY)
        self.force_interp_t_buf: deque[float] = deque(maxlen=HISTORY)
        self.force_interp_v_buf: deque[float] = deque(maxlen=HISTORY)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        ctrl = QtWidgets.QHBoxLayout()
        ctrl.addWidget(QtWidgets.QLabel("FSR 通道:"))
        self.fsr_combo = QtWidgets.QComboBox()
        for i in range(32):
            self.fsr_combo.addItem(fsr_label(i), i)
        self.fsr_combo.currentIndexChanged.connect(self._on_fsr_changed)
        ctrl.addWidget(self.fsr_combo)

        ctrl.addSpacing(12)
        ctrl.addWidget(QtWidgets.QLabel("标定 YAML:"))
        self.yaml_path_label = QtWidgets.QLabel("(未加载)")
        self.yaml_path_label.setStyleSheet("color: #666;")
        ctrl.addWidget(self.yaml_path_label)
        self.load_yaml_btn = QtWidgets.QPushButton("加载 YAML…")
        self.load_yaml_btn.clicked.connect(self._on_load_yaml)
        ctrl.addWidget(self.load_yaml_btn)

        ctrl.addSpacing(12)
        ctrl.addWidget(QtWidgets.QLabel("拟合模型:"))
        self.model_combo = QtWidgets.QComboBox()
        for label in MODEL_UI_TO_YAML:
            self.model_combo.addItem(label)
        self.model_combo.setCurrentText("幂函数")
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        ctrl.addWidget(self.model_combo)

        self.pressure_mode_chk = QtWidgets.QCheckBox("真实压力替换电压读数")
        self.pressure_mode_chk.toggled.connect(self._on_pressure_mode_toggled)
        ctrl.addWidget(self.pressure_mode_chk)

        ctrl.addSpacing(12)
        ctrl.addWidget(QtWidgets.QLabel(f"压力: {FORCE_CHANNEL_NAME}"))
        self.clear_btn = QtWidgets.QPushButton("清空曲线")
        self.clear_btn.clicked.connect(self._clear_buffers)
        ctrl.addWidget(self.clear_btn)

        ctrl.addSpacing(12)
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

        content = QtWidgets.QHBoxLayout()
        self.foot_panel = FootPressurePanel()
        self.foot_panel.setMinimumWidth(420)
        content.addWidget(self.foot_panel, stretch=2)
        self.plot_widget = pg.GraphicsLayoutWidget()
        content.addWidget(self.plot_widget, stretch=3)
        root.addLayout(content)

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
        self.plot.getAxis("right").setLabel("压力 (N)", color="#FF6600")

        self.adc_curve = self.plot.plot(pen=pg.mkPen(color=(0, 128, 255), width=2), name="FSR ADC (V)")
        self.force_curve = pg.PlotCurveItem(pen=pg.mkPen(color=(255, 102, 0), width=2), name="参考压力(插值)")
        self.force_view.addItem(self.force_curve)

        def sync_views() -> None:
            self.force_view.setGeometry(self.plot.vb.sceneBoundingRect())
            self.force_view.linkedViewChanged(self.plot.vb, self.force_view.XAxis)

        self.plot.vb.sigResized.connect(sync_views)
        sync_views()
        self.plot.enableAutoRange(axis="x", enable=False)
        self.plot.enableAutoRange(axis="y", enable=False)
        self.force_view.enableAutoRange(axis="y", enable=False)
        self.plot.setXRange(0, PLOT_WINDOW_S, padding=0)

        if DEFAULT_CALIB_YAML.is_file():
            self.calibration.load(DEFAULT_CALIB_YAML)
            self._update_yaml_status()

        self.timer = QtCore.QTimer()
        self.timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(UI_TIMER_MS)

    def _update_yaml_status(self) -> None:
        if self.calibration.is_loaded and self.calibration.loaded_path is not None:
            self.yaml_path_label.setText(self.calibration.loaded_path.name)
            self.yaml_path_label.setStyleSheet("color: #163B31;")
        elif self.calibration.load_error:
            self.yaml_path_label.setText(f"加载失败: {self.calibration.load_error}")
            self.yaml_path_label.setStyleSheet("color: #CC3300;")
        else:
            self.yaml_path_label.setText("(未加载)")
            self.yaml_path_label.setStyleSheet("color: #666;")

    def _on_load_yaml(self) -> None:
        path_str, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择标定 YAML",
            str(DEFAULT_CALIB_YAML.parent),
            "YAML 文件 (*.yml *.yaml);;所有文件 (*)",
        )
        if not path_str:
            return
        self.calibration.load(Path(path_str))
        self._update_yaml_status()
        self._update_plot_axis_labels()
        self._clear_buffers()

    def _on_model_changed(self, label: str) -> None:
        self._model_key = MODEL_UI_TO_YAML.get(label, "power")
        self._update_plot_axis_labels()
        if self._use_pressure_mode:
            self._rebuild_adc_buffer_from_hub()

    def _on_pressure_mode_toggled(self, checked: bool) -> None:
        self._use_pressure_mode = checked
        self.foot_panel.set_value_mode(checked)
        self._update_plot_axis_labels()
        self._rebuild_adc_buffer_from_hub()

    def _update_plot_axis_labels(self) -> None:
        if self._use_pressure_mode:
            self.plot.setLabel("left", "FSR 估算压力 (N)", color="#0080FF")
            self.adc_curve.opts["name"] = "FSR 估算压力 (N)"
        else:
            self.plot.setLabel("left", "ADC 电压 (V)", color="#0080FF")
            self.adc_curve.opts["name"] = "FSR ADC (V)"

    def _fsr_display_value(self, fsr_data: np.ndarray, channel: int) -> float:
        if self._use_pressure_mode and self.calibration.is_loaded:
            return float(self.calibration.voltages_to_forces(fsr_data, self._model_key)[channel])
        return float(fsr_data[channel])

    def _foot_display_values(self, fsr_data: np.ndarray) -> np.ndarray:
        if self._use_pressure_mode and self.calibration.is_loaded:
            return self.calibration.voltages_to_forces(fsr_data, self._model_key)
        return fsr_data.copy()

    def _rebuild_adc_buffer_from_hub(self) -> None:
        fsr_data, fsr_stamp, fsr_ok, _, _, _ = self.hub.snapshot()
        if not fsr_ok:
            return
        self.adc_t_buf.clear()
        self.adc_v_buf.clear()
        if self._t_origin is not None and fsr_stamp >= self._t_origin:
            self.adc_t_buf.append(self._rel_time(fsr_stamp))
            self.adc_v_buf.append(self._fsr_display_value(fsr_data, self.fsr_channel))
        self._update_plot()

    def _rel_time(self, stamp: float) -> float:
        if self._t_origin is None:
            self._t_origin = stamp
        return stamp - self._t_origin

    def _window_bounds(self) -> tuple[float, float]:
        if self._t_origin is None:
            return 0.0, PLOT_WINDOW_S
        win_end = max(PLOT_WINDOW_S, time.time() - self._t_origin)
        return win_end - PLOT_WINDOW_S, win_end

    @staticmethod
    def _series_for_window(t_buf: deque[float], v_buf: deque[float], win_start: float, win_end: float) -> tuple[list[float], list[float]]:
        xs: list[float] = []
        ys: list[float] = []
        for t, v in zip(t_buf, v_buf):
            if win_start <= t <= win_end and np.isfinite(v):
                xs.append(t)
                ys.append(v)
        return xs, ys

    @staticmethod
    def _apply_y_range(viewbox: pg.ViewBox, values: list[float]) -> None:
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
        adc_x, adc_y = self._series_for_window(self.adc_t_buf, self.adc_v_buf, win_start, win_end)
        force_x, force_y = self._series_for_window(self.force_interp_t_buf, self.force_interp_v_buf, win_start, win_end)
        self.adc_curve.setData(adc_x, adc_y)
        self.force_curve.setData(force_x, force_y)
        self.plot.setXRange(win_start, win_end, padding=0)
        self._apply_y_range(self.plot.vb, adc_y)
        self._apply_y_range(self.force_view, force_y)

    def _on_fsr_changed(self, index: int) -> None:
        self.fsr_channel = self.fsr_combo.itemData(index)
        self._clear_buffers()

    def _clear_buffers(self) -> None:
        self.adc_t_buf.clear()
        self.adc_v_buf.clear()
        self.force_interp_t_buf.clear()
        self.force_interp_v_buf.clear()
        self.pipeline.clear_anchors()
        self._t_origin = None
        self._last_fsr_stamp = -1.0
        self._force_interp_now = float("nan")
        self.plot.setXRange(0, PLOT_WINDOW_S, padding=0)
        self._update_plot()

    def _on_start_record(self) -> None:
        path = self.pipeline.request_start_record()
        self.start_record_btn.setEnabled(False)
        self.stop_record_btn.setEnabled(True)
        print(f"录制文件: record/{path.name}")

    def _on_stop_record(self) -> None:
        count = self.pipeline.request_stop_record()
        self.start_record_btn.setEnabled(True)
        self.stop_record_btn.setEnabled(False)
        print(f"已保存 {count} 行")

    def _refresh(self) -> None:
        fsr_data, fsr_stamp, fsr_ok, _, force_stamp, force_ok = self.hub.snapshot()
        _, record_path, recording, row_count = self.pipeline.snapshot()

        data_changed = False
        if fsr_ok and fsr_stamp != self._last_fsr_stamp:
            t_rel = self._rel_time(fsr_stamp)
            self.adc_t_buf.append(t_rel)
            self.adc_v_buf.append(self._fsr_display_value(fsr_data, self.fsr_channel))
            force_interp = self.pipeline.interp_force(fsr_stamp)
            if force_interp is not None:
                self.force_interp_t_buf.append(t_rel)
                self.force_interp_v_buf.append(force_interp)
                self._force_interp_now = force_interp
            self._last_fsr_stamp = fsr_stamp
            data_changed = True

        if fsr_ok:
            foot_display = self._foot_display_values(fsr_data)
            self.foot_panel.update_feet(foot_display, (foot_display[:16], foot_display[16:32]))

        if data_changed:
            self._update_plot()
            self._ui_fps_count += 1

        now = time.monotonic()
        if now - self._last_ui_fps_report >= 1.0:
            elapsed = now - self._last_ui_fps_report
            self._ui_fps = self._ui_fps_count / elapsed if elapsed > 0 else 0.0
            self._ui_fps_count = 0
            self._last_ui_fps_report = now

        if now - self._last_status_update >= STATUS_UPDATE_INTERVAL_S:
            adc_now = fsr_data[self.fsr_channel] if fsr_ok else float("nan")
            est_now = self._fsr_display_value(fsr_data, self.fsr_channel) if fsr_ok else float("nan")
            force_now = self._force_interp_now if np.isfinite(self._force_interp_now) else float("nan")
            skew_ms = abs(fsr_stamp - force_stamp) * 1000.0 if fsr_ok and force_ok else float("nan")
            calib_state = "已加载" if self.calibration.is_loaded else "未加载"
            ch_fit_ok = self.calibration.channel_model_ok(self.fsr_channel, self._model_key) if self.calibration.is_loaded else False
            parts = [
                f"FSR TCP ({FSR_HOST}:{FSR_PORT}): {'已连接' if fsr_ok else '未连接'}",
                f"压力 WS ({FORCE_WS_URL}): {'已连接' if force_ok else '未连接'}",
                f"标定 YAML: {calib_state}",
                f"模型: {self.model_combo.currentText()}" + (" ✓" if ch_fit_ok else " ✗"),
                f"当前 FSR[{self.fsr_channel}] ADC={adc_now:.4f} V",
            ]
            if self._use_pressure_mode:
                parts.append(f"估算压力={est_now:.1f} N" if np.isfinite(est_now) else "估算压力=—")
            parts.extend([
                f"参考压力={force_now:.3f} N",
                f"时间偏差={skew_ms:.0f} ms" if fsr_ok and force_ok else "时间偏差=—",
                f"UI FPS={self._ui_fps:.1f}",
            ])
            if recording and record_path is not None:
                parts.append(f"录制中 → record/{record_path.name} ({row_count} 行)")
            self.status_label.setText("  |  ".join(parts))
            self._last_status_update = now

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.timer.stop()
        _, record_path, recording, _ = self.pipeline.snapshot()
        if recording:
            count = self.pipeline.request_stop_record()
            if record_path is not None:
                print(f"窗口关闭，录制已自动保存: {record_path} ({count} 行)")
        self._stop.set()
        self.pipeline.shutdown()
        event.accept()
