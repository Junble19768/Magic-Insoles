import time
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

from .calibration_store import CalibrationStore
from .config import (
    DEFAULT_CALIB_YAML,
    FSR_HOST,
    FSR_PORT,
    MODEL_UI_TO_YAML,
    STATUS_UPDATE_INTERVAL_S,
    UI_TIMER_MS,
)
from .heatmap import FootPressurePanel
from .hub import DataHub
from .plot_utils import FpsTracker
from .runtime import ReaderRuntime


class FsrVisualizeApp(QtWidgets.QWidget):
    """脚型可视化：ADC / 结算压力热力图 + 重心 (COP)。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FSR 脚型可视化 — 热力图与重心")
        self.resize(900, 520)

        self.calibration = CalibrationStore()
        self._model_key = MODEL_UI_TO_YAML["幂函数"]
        self._use_pressure_mode = False

        self.hub = DataHub()
        self.runtime = ReaderRuntime(self.hub, with_force=False)
        self.runtime.start()

        self._last_fsr_stamp = -1.0
        self._last_status_update = 0.0
        self._fps = FpsTracker()

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        ctrl = QtWidgets.QHBoxLayout()

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
        ctrl.addStretch()
        root.addLayout(ctrl)

        self.status_label = QtWidgets.QLabel("状态: 等待连接...")
        self.status_label.setStyleSheet("font: 13px;")
        root.addWidget(self.status_label)

        self.foot_panel = FootPressurePanel()
        root.addWidget(self.foot_panel)

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

    def _on_model_changed(self, label: str) -> None:
        self._model_key = MODEL_UI_TO_YAML.get(label, "power")

    def _on_pressure_mode_toggled(self, checked: bool) -> None:
        if checked and not self.calibration.is_loaded:
            self.pressure_mode_chk.blockSignals(True)
            self.pressure_mode_chk.setChecked(False)
            self.pressure_mode_chk.blockSignals(False)
            self.status_label.setText("请先加载标定 YAML 后再切换压力模式")
            return
        self._use_pressure_mode = checked
        self.foot_panel.set_value_mode(checked)

    def _foot_display_values(self, fsr_data: np.ndarray) -> np.ndarray:
        if self._use_pressure_mode and self.calibration.is_loaded:
            return self.calibration.voltages_to_forces(fsr_data, self._model_key)
        return fsr_data.copy()

    def _refresh(self) -> None:
        fsr_data, fsr_stamp, fsr_ok, _, _, _ = self.hub.snapshot()

        if fsr_ok and fsr_stamp != self._last_fsr_stamp:
            foot_display = self._foot_display_values(fsr_data)
            self.foot_panel.update_feet(foot_display, (foot_display[:16], foot_display[16:32]))
            self._last_fsr_stamp = fsr_stamp
            self._fps.tick()

        self._fps.maybe_report()

        now = time.monotonic()
        if now - self._last_status_update >= STATUS_UPDATE_INTERVAL_S:
            calib_state = "已加载" if self.calibration.is_loaded else "未加载"
            mode = "压力 (N)" if self._use_pressure_mode else "ADC (V)"
            left_vals = self._foot_display_values(fsr_data)[:16] if fsr_ok else np.zeros(16)
            right_vals = self._foot_display_values(fsr_data)[16:32] if fsr_ok else np.zeros(16)
            left_sum = float(np.nansum(left_vals)) if self._use_pressure_mode else float("nan")
            right_sum = float(np.nansum(right_vals)) if self._use_pressure_mode else float("nan")
            parts = [
                f"FSR TCP ({FSR_HOST}:{FSR_PORT}): {'已连接' if fsr_ok else '未连接'}",
                f"标定 YAML: {calib_state}",
                f"显示模式: {mode}",
                f"模型: {self.model_combo.currentText()}",
                f"UI FPS={self._fps.fps:.1f}",
            ]
            if self._use_pressure_mode and fsr_ok:
                parts.append(f"左脚 Σ={left_sum:.1f} N  右脚 Σ={right_sum:.1f} N")
            self.status_label.setText("  |  ".join(parts))
            self._last_status_update = now

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.timer.stop()
        self.runtime.stop()
        event.accept()
