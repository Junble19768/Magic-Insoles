import time
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

from .calibration_store import CalibrationStore
from .config import (
    DEFAULT_CALIB_YAML,
    FORCE_WS_URL,
    FSR_HOST,
    FSR_PORT,
    HISTORY,
    MODEL_UI_TO_YAML,
    PLOT_WINDOW_S,
    REF_PLOT_Y_MAX_N,
    REF_PLOT_Y_MIN_N,
    REF_RESIDUAL_Y_AUTO,
    STATUS_UPDATE_INTERVAL_S,
    UI_TIMER_MS,
)
from .hub import DataHub, fsr_label
from .plot_utils import FpsTracker, TimeSeriesBuffers, apply_auto_y_range, series_for_window
from .runtime import ReaderRuntime


class FsrReferenceApp(QtWidgets.QWidget):
    """标定结果参考：同轴压力对比（固定 0–300 N）+ 残差曲线。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FSR 标定结果参考 — 压力对比与残差")
        self.resize(1100, 620)

        self.calibration = CalibrationStore()
        self._model_key = MODEL_UI_TO_YAML["幂函数"]

        self.hub = DataHub()
        self.runtime = ReaderRuntime(self.hub, with_force=True)
        self.runtime.start()
        self.pipeline = self.runtime.pipeline

        self.fsr_channel = 0
        self._last_fsr_stamp = -1.0
        self._last_status_update = 0.0
        self._fsr_pressure_now = float("nan")
        self._force_interp_now = float("nan")
        self._fps = FpsTracker()

        self.fsr_series = TimeSeriesBuffers()
        self.fsr_series.configure(maxlen=HISTORY)
        self.force_series = TimeSeriesBuffers()
        self.force_series.configure(maxlen=HISTORY)
        self.residual_series = TimeSeriesBuffers()
        self.residual_series.configure(maxlen=HISTORY)

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

        self.clear_btn = QtWidgets.QPushButton("清空曲线")
        self.clear_btn.clicked.connect(self._clear_buffers)
        ctrl.addWidget(self.clear_btn)
        ctrl.addStretch()
        root.addLayout(ctrl)

        self.status_label = QtWidgets.QLabel("状态: 等待连接...")
        self.status_label.setStyleSheet("font: 13px;")
        root.addWidget(self.status_label)

        self.plot_widget = pg.GraphicsLayoutWidget()
        root.addWidget(self.plot_widget)

        self.pressure_plot = self.plot_widget.addPlot(row=0, col=0, title="FSR 估算压力 vs 参考压力")
        self.pressure_plot.setLabel("bottom", "时间 (s)")
        self.pressure_plot.setLabel("left", "压力 (N)")
        self.pressure_plot.showGrid(x=True, y=True, alpha=0.3)
        self.pressure_plot.addLegend(offset=(10, 10))
        self.pressure_plot.enableAutoRange(axis="x", enable=False)
        self.pressure_plot.enableAutoRange(axis="y", enable=False)
        self.pressure_plot.setYRange(REF_PLOT_Y_MIN_N, REF_PLOT_Y_MAX_N, padding=0)
        self.pressure_plot.setXRange(0, PLOT_WINDOW_S, padding=0)

        self.fsr_curve = self.pressure_plot.plot(
            pen=pg.mkPen(color=(0, 128, 255), width=2),
            name="FSR 估算压力 (N)",
        )
        self.force_curve = self.pressure_plot.plot(
            pen=pg.mkPen(color=(255, 102, 0), width=2),
            name="参考压力 (N)",
        )

        self.residual_plot = self.plot_widget.addPlot(row=1, col=0, title="残差 (FSR − 参考)")
        self.residual_plot.setLabel("bottom", "时间 (s)")
        self.residual_plot.setLabel("left", "残差 (N)")
        self.residual_plot.showGrid(x=True, y=True, alpha=0.3)
        self.residual_plot.enableAutoRange(axis="x", enable=False)
        self.residual_plot.enableAutoRange(axis="y", enable=REF_RESIDUAL_Y_AUTO)
        self.residual_plot.setXLink(self.pressure_plot)
        self.residual_plot.setXRange(0, PLOT_WINDOW_S, padding=0)
        self.residual_curve = self.residual_plot.plot(
            pen=pg.mkPen(color=(180, 60, 180), width=2),
            name="残差 (N)",
        )

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
        self._clear_buffers()

    def _on_model_changed(self, label: str) -> None:
        self._model_key = MODEL_UI_TO_YAML.get(label, "power")
        self._clear_buffers()

    def _fsr_pressure(self, fsr_data: np.ndarray, channel: int) -> float:
        if not self.calibration.is_loaded:
            return float("nan")
        return float(self.calibration.voltages_to_forces(fsr_data, self._model_key)[channel])

    def _update_plot(self) -> None:
        win_start, win_end = self.fsr_series.window_bounds()
        fsr_x, fsr_y = series_for_window(
            self.fsr_series.t_buf, self.fsr_series.v_buf, win_start, win_end
        )
        force_x, force_y = series_for_window(
            self.force_series.t_buf, self.force_series.v_buf, win_start, win_end
        )
        res_x, res_y = series_for_window(
            self.residual_series.t_buf, self.residual_series.v_buf, win_start, win_end
        )

        if self.calibration.is_loaded:
            self.fsr_curve.setData(fsr_x, fsr_y)
        else:
            self.fsr_curve.setData([], [])

        self.force_curve.setData(force_x, force_y)
        self.residual_curve.setData(res_x, res_y)

        self.pressure_plot.setXRange(win_start, win_end, padding=0)
        self.pressure_plot.setYRange(REF_PLOT_Y_MIN_N, REF_PLOT_Y_MAX_N, padding=0)
        if REF_RESIDUAL_Y_AUTO:
            apply_auto_y_range(self.residual_plot.vb, res_y)

    def _on_fsr_changed(self, index: int) -> None:
        self.fsr_channel = self.fsr_combo.itemData(index)
        self._clear_buffers()

    def _clear_buffers(self) -> None:
        self.fsr_series.clear()
        self.force_series.clear()
        self.residual_series.clear()
        self.pipeline.clear_anchors()
        self._last_fsr_stamp = -1.0
        self._fsr_pressure_now = float("nan")
        self._force_interp_now = float("nan")
        self.pressure_plot.setXRange(0, PLOT_WINDOW_S, padding=0)
        self._update_plot()

    def _refresh(self) -> None:
        fsr_data, fsr_stamp, fsr_ok, _, force_stamp, force_ok = self.hub.snapshot()

        data_changed = False
        if fsr_ok and fsr_stamp != self._last_fsr_stamp:
            fsr_p = self._fsr_pressure(fsr_data, self.fsr_channel)
            force_interp = self.pipeline.interp_force(fsr_stamp)
            t_rel = self.fsr_series.append(fsr_stamp, fsr_p)
            if force_interp is not None:
                self.force_series.t_buf.append(t_rel)
                self.force_series.v_buf.append(force_interp)
                self._force_interp_now = force_interp
                if self.calibration.is_loaded and np.isfinite(fsr_p):
                    self.residual_series.t_buf.append(t_rel)
                    self.residual_series.v_buf.append(fsr_p - force_interp)
            self._fsr_pressure_now = fsr_p
            self._last_fsr_stamp = fsr_stamp
            data_changed = True

        if data_changed:
            self._update_plot()
            self._fps.tick()

        self._fps.maybe_report()

        now = time.monotonic()
        if now - self._last_status_update >= STATUS_UPDATE_INTERVAL_S:
            residual_now = (
                self._fsr_pressure_now - self._force_interp_now
                if np.isfinite(self._fsr_pressure_now) and np.isfinite(self._force_interp_now)
                else float("nan")
            )
            calib_state = "已加载" if self.calibration.is_loaded else "未加载（需加载 YAML）"
            ch_fit_ok = (
                self.calibration.channel_model_ok(self.fsr_channel, self._model_key)
                if self.calibration.is_loaded
                else False
            )
            parts = [
                f"FSR TCP ({FSR_HOST}:{FSR_PORT}): {'已连接' if fsr_ok else '未连接'}",
                f"压力 WS ({FORCE_WS_URL}): {'已连接' if force_ok else '未连接'}",
                f"标定 YAML: {calib_state}",
                f"模型: {self.model_combo.currentText()}" + (" ✓" if ch_fit_ok else " ✗"),
                f"FSR[{self.fsr_channel}] 估算={self._fsr_pressure_now:.1f} N"
                if np.isfinite(self._fsr_pressure_now)
                else f"FSR[{self.fsr_channel}] 估算=—",
                f"参考={self._force_interp_now:.1f} N"
                if np.isfinite(self._force_interp_now)
                else "参考=—",
                f"残差={residual_now:.1f} N" if np.isfinite(residual_now) else "残差=—",
                f"时间偏差={abs(fsr_stamp - force_stamp) * 1000.0:.0f} ms"
                if fsr_ok and force_ok
                else "时间偏差=—",
                f"Y 轴固定 {REF_PLOT_Y_MIN_N:.0f}–{REF_PLOT_Y_MAX_N:.0f} N",
                f"UI FPS={self._fps.fps:.1f}",
            ]
            self.status_label.setText("  |  ".join(parts))
            self._last_status_update = now

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.timer.stop()
        self.runtime.stop()
        event.accept()
