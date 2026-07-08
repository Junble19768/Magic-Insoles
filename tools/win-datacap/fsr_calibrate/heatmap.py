from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui

from .boundary import build_boundary_foot_heatmap, get_boundary_label_positions
from .config import BOUNDARY_BLUR_SIGMA
from .cop import FootCop, compute_foot_cop

_COP_CROSS_HALF_LEN = 5.0
_COP_LABEL_OFFSET = (8.0, 8.0)


@dataclass
class _CopCrosshair:
    h_core: pg.PlotDataItem
    v_core: pg.PlotDataItem
    h_outline: pg.PlotDataItem
    v_outline: pg.PlotDataItem


class FootPressurePanel(pg.GraphicsLayoutWidget):
    """双脚压力/电压热力图，叠加数值标注。"""

    def __init__(self) -> None:
        super().__init__()
        self._left_labels: list[pg.TextItem] = []
        self._right_labels: list[pg.TextItem] = []
        self._sensor_positions = get_boundary_label_positions()
        sample = build_boundary_foot_heatmap(
            np.zeros(16, dtype=float),
            blur_sigma=0.0,
        )
        self._canvas_height = int(sample.shape[0])
        self._canvas_width = int(sample.shape[1])
        self._left_label_x_max = float(max(self._canvas_height - 1, 0))

        self.left_plot = self.addPlot(row=0, col=0, title="左脚")
        self.right_plot = self.addPlot(row=0, col=1, title="右脚")
        for plot in (self.left_plot, self.right_plot):
            plot.setAspectLocked(True)
            plot.hideAxis("left")
            plot.hideAxis("bottom")
            plot.invertY(True)

        self.left_image = pg.ImageItem()
        self.right_image = pg.ImageItem()
        self.left_plot.addItem(self.left_image)
        self.right_plot.addItem(self.right_image)

        self._cmap = pg.colormap.get("viridis") or pg.colormap.get("CET-L9")
        self._show_pressure = False

        self._left_cop_cross = self._create_crosshair(self.left_plot)
        self._right_cop_cross = self._create_crosshair(self.right_plot)
        self._left_cop_label = self._create_cop_label(self.left_plot)
        self._right_cop_label = self._create_cop_label(self.right_plot)
        self._hide_cop_overlay(self._left_cop_cross, self._left_cop_label)
        self._hide_cop_overlay(self._right_cop_cross, self._right_cop_label)

    def set_value_mode(self, show_pressure: bool) -> None:
        self._show_pressure = show_pressure
        if not show_pressure:
            self._hide_cop_overlay(self._left_cop_cross, self._left_cop_label)
            self._hide_cop_overlay(self._right_cop_cross, self._right_cop_label)

    def update_feet(self, display_values: np.ndarray, raw_foot_values: tuple[np.ndarray, np.ndarray]) -> None:
        left_raw, right_raw = raw_foot_values
        left_img = build_boundary_foot_heatmap(
            display_values[:16],
            transpose=True,
            flip_horizontal=True,
            blur_sigma=BOUNDARY_BLUR_SIGMA,
        )
        right_img = build_boundary_foot_heatmap(
            display_values[16:32],
            transpose=True,
            blur_sigma=BOUNDARY_BLUR_SIGMA,
        )

        if self._show_pressure:
            max_data = float(np.nanmax([np.nanmax(left_img), np.nanmax(right_img), 0.0]))
            denom = max(max_data, 100.0)
            left_img = left_img / denom
            right_img = right_img / denom
            vmax = 1.0
        else:
            vmax = float(np.nanmax([np.nanmax(left_img), np.nanmax(right_img), 0.01]))

        self._left_label_x_max = float(max(left_img.shape[0] - 1, 0))

        for image, img_data in ((self.left_image, left_img), (self.right_image, right_img)):
            image.setImage(img_data, autoLevels=False)
            image.setLevels((0.0, vmax))
            if self._cmap is not None:
                image.setLookupTable(self._cmap.getLookupTable(0, vmax))

        self._update_labels(self.left_plot, self._left_labels, left_raw, foot="left")
        self._update_labels(self.right_plot, self._right_labels, right_raw, foot="right")
        self._update_cop_overlays(left_raw, right_raw)

    @staticmethod
    def _create_crosshair(plot: pg.PlotItem) -> _CopCrosshair:
        outline_pen = pg.mkPen((255, 255, 200), width=3)
        core_pen = pg.mkPen((220, 40, 40), width=1.5)
        cross = _CopCrosshair(
            h_core=pg.PlotDataItem(pen=core_pen),
            v_core=pg.PlotDataItem(pen=core_pen),
            h_outline=pg.PlotDataItem(pen=outline_pen),
            v_outline=pg.PlotDataItem(pen=outline_pen),
        )
        for item in (cross.h_outline, cross.v_outline, cross.h_core, cross.v_core):
            plot.addItem(item)
        cross.h_outline.setZValue(9)
        cross.v_outline.setZValue(9)
        cross.h_core.setZValue(10)
        cross.v_core.setZValue(10)
        return cross

    @staticmethod
    def _create_cop_label(plot: pg.PlotItem) -> pg.TextItem:
        label = pg.TextItem(anchor=(0.0, 0.0), color=(255, 240, 180))
        label.setFont(QtGui.QFont("Arial", 9, QtGui.QFont.Bold))
        plot.addItem(label)
        label.setZValue(11)
        return label

    @staticmethod
    def _hide_cop_overlay(cross: _CopCrosshair, label: pg.TextItem) -> None:
        for item in (cross.h_core, cross.v_core, cross.h_outline, cross.v_outline, label):
            item.setVisible(False)

    @staticmethod
    def _set_crosshair_pos(cross: _CopCrosshair, x: float, y: float) -> None:
        half = _COP_CROSS_HALF_LEN
        cross.h_core.setData([x - half, x + half], [y, y])
        cross.v_core.setData([x, x], [y - half, y + half])
        cross.h_outline.setData([x - half, x + half], [y, y])
        cross.v_outline.setData([x, x], [y - half, y + half])

    def _update_cop_overlays(self, left_raw: np.ndarray, right_raw: np.ndarray) -> None:
        if not self._show_pressure:
            self._hide_cop_overlay(self._left_cop_cross, self._left_cop_label)
            self._hide_cop_overlay(self._right_cop_cross, self._right_cop_label)
            return

        left_cop = compute_foot_cop(
            left_raw,
            self._sensor_positions,
            mirror_x=self._left_label_x_max,
        )
        right_cop = compute_foot_cop(right_raw, self._sensor_positions)
        self._apply_cop_overlay(self._left_cop_cross, self._left_cop_label, left_cop)
        self._apply_cop_overlay(self._right_cop_cross, self._right_cop_label, right_cop)

    def _apply_cop_overlay(
        self,
        cross: _CopCrosshair,
        label: pg.TextItem,
        cop: FootCop,
    ) -> None:
        if cop.total_pressure <= 0.0 or not np.isfinite(cop.x) or not np.isfinite(cop.y):
            self._hide_cop_overlay(cross, label)
            return

        self._set_crosshair_pos(cross, cop.x, cop.y)
        for item in (cross.h_core, cross.v_core, cross.h_outline, cross.v_outline):
            item.setVisible(True)

        offset_x, offset_y = _COP_LABEL_OFFSET
        label.setText(f"Σ {cop.total_pressure:.1f} N")
        label.setPos(cop.x + offset_x, cop.y + offset_y)
        label.setVisible(True)

    def _update_labels(
        self,
        plot: pg.PlotItem,
        label_pool: list[pg.TextItem],
        foot_values: np.ndarray,
        *,
        foot: str,
    ) -> None:
        while len(label_pool) < len(self._sensor_positions):
            text = pg.TextItem(anchor=(0.5, 0.5), color=(255, 255, 255))
            text.setFont(QtGui.QFont("Arial", 8, QtGui.QFont.Bold))
            plot.addItem(text)
            label_pool.append(text)

        for i, (local_idx, cx, cy) in enumerate(self._sensor_positions):
            val = float(foot_values[local_idx])
            if foot == "left":
                # Left foot: same XY basis as right, then mirror in display X.
                plot_x = self._left_label_x_max - cx
                plot_y = cy
            else:
                plot_x = cx
                plot_y = cy
            label = (f"{val:.1f}" if self._show_pressure else f"{val:.2f}") if np.isfinite(val) else "—"
            label_pool[i].setText(label)
            label_pool[i].setPos(plot_x, plot_y)
            label_pool[i].setVisible(True)
