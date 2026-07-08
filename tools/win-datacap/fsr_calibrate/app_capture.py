import time

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

from .config import (
    FORCE_CHANNEL_NAME,
    FORCE_WS_URL,
    FSR_HOST,
    FSR_PORT,
    HISTORY,
    PLOT_WINDOW_S,
    STATUS_UPDATE_INTERVAL_S,
    UI_TIMER_MS,
)
from .hub import DataHub, fsr_label
from .plot_utils import (
    FpsTracker,
    TimeSeriesBuffers,
    apply_auto_y_range,
    series_for_window,
    setup_dual_axis_plot,
)
from .runtime import ReaderRuntime


class FsrCaptureApp(QtWidgets.QWidget):
    """标定采集：双 Y 轴 ADC vs 参考压力折线图 + CSV 录制。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FSR 标定采集 — ADC vs 参考压力")
        self.resize(1100, 520)

        self.hub = DataHub()
        self.runtime = ReaderRuntime(self.hub, with_force=True)
        self.runtime.start()
        self.pipeline = self.runtime.pipeline

        self.fsr_channel = 0
        self._last_fsr_stamp = -1.0
        self._last_status_update = 0.0
        self._force_interp_now = float("nan")
        self._fps = FpsTracker()

        self.adc_series = TimeSeriesBuffers()
        self.adc_series.configure(maxlen=HISTORY)
        self.force_series = TimeSeriesBuffers()
        self.force_series.configure(maxlen=HISTORY)

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

        self.plot_widget = pg.GraphicsLayoutWidget()
        root.addWidget(self.plot_widget)
        self.plot = self.plot_widget.addPlot(title="FSR ADC vs 参考压力")
        self.force_view, self.adc_curve, self.force_curve = setup_dual_axis_plot(
            self.plot,
            left_label="ADC 电压 (V)",
            left_color="#0080FF",
            right_label="压力 (N)",
            right_color="#FF6600",
        )
        self.adc_curve.opts["name"] = "FSR ADC (V)"
        self.force_curve.opts["name"] = "参考压力(插值)"

        self.timer = QtCore.QTimer()
        self.timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(UI_TIMER_MS)

    def _update_plot(self) -> None:
        win_start, win_end = self.adc_series.window_bounds()
        adc_x, adc_y = series_for_window(
            self.adc_series.t_buf, self.adc_series.v_buf, win_start, win_end
        )
        force_x, force_y = series_for_window(
            self.force_series.t_buf, self.force_series.v_buf, win_start, win_end
        )
        self.adc_curve.setData(adc_x, adc_y)
        self.force_curve.setData(force_x, force_y)
        self.plot.setXRange(win_start, win_end, padding=0)
        apply_auto_y_range(self.plot.vb, adc_y)
        apply_auto_y_range(self.force_view, force_y)

    def _on_fsr_changed(self, index: int) -> None:
        self.fsr_channel = self.fsr_combo.itemData(index)
        self._clear_buffers()

    def _clear_buffers(self) -> None:
        self.adc_series.clear()
        self.force_series.clear()
        self.pipeline.clear_anchors()
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
            t_rel = self.adc_series.append(fsr_stamp, float(fsr_data[self.fsr_channel]))
            force_interp = self.pipeline.interp_force(fsr_stamp)
            if force_interp is not None:
                self.force_series.t_buf.append(t_rel)
                self.force_series.v_buf.append(force_interp)
                self._force_interp_now = force_interp
            self._last_fsr_stamp = fsr_stamp
            data_changed = True

        if data_changed:
            self._update_plot()
            self._fps.tick()

        self._fps.maybe_report()

        now = time.monotonic()
        if now - self._last_status_update >= STATUS_UPDATE_INTERVAL_S:
            adc_now = fsr_data[self.fsr_channel] if fsr_ok else float("nan")
            force_now = self._force_interp_now if np.isfinite(self._force_interp_now) else float("nan")
            skew_ms = abs(fsr_stamp - force_stamp) * 1000.0 if fsr_ok and force_ok else float("nan")
            parts = [
                f"FSR TCP ({FSR_HOST}:{FSR_PORT}): {'已连接' if fsr_ok else '未连接'}",
                f"压力 WS ({FORCE_WS_URL}): {'已连接' if force_ok else '未连接'}",
                f"当前 FSR[{self.fsr_channel}] ADC={adc_now:.4f} V",
                f"参考压力={force_now:.3f} N" if np.isfinite(force_now) else "参考压力=—",
                f"时间偏差={skew_ms:.0f} ms" if fsr_ok and force_ok else "时间偏差=—",
                f"UI FPS={self._fps.fps:.1f}",
            ]
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
        self.runtime.stop()
        event.accept()
