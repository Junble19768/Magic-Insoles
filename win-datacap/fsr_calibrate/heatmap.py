import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui

from .config import FOOT_BLUR_SIGMA, FOOT_GRID_COLS, FOOT_GRID_ROWS, FOOT_SCALE_UP, FOOT_SENSOR_REGIONS


def _gaussian_kernel_1d(sigma: float) -> np.ndarray:
    size = max(3, int(6 * sigma + 1) | 1)
    half = size // 2
    x = np.arange(-half, half + 1, dtype=float)
    kernel = np.exp(-0.5 * (x / sigma) ** 2)
    return kernel / kernel.sum()


def _gaussian_blur_2d(arr: np.ndarray, sigma: float) -> np.ndarray:
    kernel = _gaussian_kernel_1d(sigma)
    pad = len(kernel) // 2
    padded = np.pad(arr, pad, mode="edge")
    tmp = np.apply_along_axis(lambda row: np.convolve(row, kernel, mode="valid"), 1, padded)
    return np.apply_along_axis(lambda col: np.convolve(col, kernel, mode="valid"), 0, tmp)


def _fill_foot_grid(foot_values: np.ndarray) -> np.ndarray:
    img = np.zeros((FOOT_GRID_ROWS, FOOT_GRID_COLS), dtype=float)
    for idx, r0, r1, c0, c1 in FOOT_SENSOR_REGIONS:
        img[r0:r1, c0:c1] = foot_values[idx]
    return img


def _sensor_label_positions() -> list[tuple[int, float, float]]:
    positions: list[tuple[int, float, float]] = []
    for idx, r0, r1, c0, c1 in FOOT_SENSOR_REGIONS:
        cx = (c0 + c1) * 0.5 * FOOT_SCALE_UP
        cy = (r0 + r1) * 0.5 * FOOT_SCALE_UP
        positions.append((idx, cx, cy))
    return positions


def build_foot_heatmap(foot_values: np.ndarray, flip_horizontal: bool) -> np.ndarray:
    grid = np.nan_to_num(_fill_foot_grid(foot_values), nan=0.0, posinf=0.0, neginf=0.0)
    blurred = _gaussian_blur_2d(grid, FOOT_BLUR_SIGMA)
    if flip_horizontal:
        blurred = np.flip(blurred, axis=0)
    return np.repeat(np.repeat(blurred, FOOT_SCALE_UP, axis=0), FOOT_SCALE_UP, axis=1)


class FootPressurePanel(pg.GraphicsLayoutWidget):
    """双脚压力/电压热力图，叠加数值标注。"""

    def __init__(self) -> None:
        super().__init__()
        self._left_labels: list[pg.TextItem] = []
        self._right_labels: list[pg.TextItem] = []
        self._sensor_positions = _sensor_label_positions()

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

        self._cmap = pg.colormap.get("viridis")
        self._show_pressure = False

    def set_value_mode(self, show_pressure: bool) -> None:
        self._show_pressure = show_pressure

    def update_feet(self, display_values: np.ndarray, raw_foot_values: tuple[np.ndarray, np.ndarray]) -> None:
        left_raw, right_raw = raw_foot_values
        left_img = build_foot_heatmap(display_values[:16], flip_horizontal=True)
        right_img = build_foot_heatmap(display_values[16:32], flip_horizontal=False)

        if self._show_pressure:
            max_data = float(np.nanmax([np.nanmax(left_img), np.nanmax(right_img), 0.0]))
            denom = max(max_data, 100.0)
            left_img = left_img / denom
            right_img = right_img / denom
            vmax = 1.0
        else:
            vmax = float(np.nanmax([np.nanmax(left_img), np.nanmax(right_img), 0.01]))

        for image, img_data in ((self.left_image, left_img), (self.right_image, right_img)):
            image.setImage(img_data, autoLevels=False)
            image.setLevels((0.0, vmax))
            image.setLookupTable(self._cmap.getLookupTable(0, vmax))

        self._update_labels(self.left_plot, self._left_labels, left_raw, flip_horizontal=True)
        self._update_labels(self.right_plot, self._right_labels, right_raw, flip_horizontal=False)

    def _update_labels(
        self,
        plot: pg.PlotItem,
        label_pool: list[pg.TextItem],
        foot_values: np.ndarray,
        flip_horizontal: bool,
    ) -> None:
        while len(label_pool) < len(self._sensor_positions):
            text = pg.TextItem(anchor=(0.5, 0.5), color=(255, 255, 255))
            text.setFont(QtGui.QFont("Arial", 8, QtGui.QFont.Bold))
            plot.addItem(text)
            label_pool.append(text)

        height = FOOT_GRID_ROWS * FOOT_SCALE_UP
        for i, (local_idx, cx, cy) in enumerate(self._sensor_positions):
            val = float(foot_values[local_idx])
            x_pos = cx
            y_pos = (height - cy) if flip_horizontal else cy
            label = (f"{val:.1f}" if self._show_pressure else f"{val:.2f}") if np.isfinite(val) else "—"
            label_pool[i].setText(label)
            label_pool[i].setPos(y_pos, x_pos)
            label_pool[i].setVisible(True)
