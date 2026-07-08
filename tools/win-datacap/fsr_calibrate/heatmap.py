import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui

from .boundary import build_boundary_foot_heatmap, get_boundary_label_positions
from .config import BOUNDARY_BLUR_SIGMA


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

    def set_value_mode(self, show_pressure: bool) -> None:
        self._show_pressure = show_pressure

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
