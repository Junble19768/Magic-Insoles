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
        # pyqtgraph 的 ImageItem 坐标轴与 setPos 的传参顺序依赖于历史实现：
        # 这里把 "height" 绑定到渲染数组的 axis=0 尺寸，确保 flipHorizontal 的标注位置一致。
        sample = build_boundary_foot_heatmap(
            np.zeros(16, dtype=float),
            flip_horizontal=False,
            blur_sigma=0.0,
        )
        self._canvas_height = int(sample.shape[0])

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
        left_img = build_boundary_foot_heatmap(
            display_values[:16],
            flip_horizontal=True,
            blur_sigma=BOUNDARY_BLUR_SIGMA,
        )
        right_img = build_boundary_foot_heatmap(
            display_values[16:32],
            flip_horizontal=False,
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

        for i, (local_idx, cx, cy) in enumerate(self._sensor_positions):
            val = float(foot_values[local_idx])
            x_pos = cx
            y_pos = (self._canvas_height - cy) if flip_horizontal else cy
            label = (f"{val:.1f}" if self._show_pressure else f"{val:.2f}") if np.isfinite(val) else "—"
            label_pool[i].setText(label)
            label_pool[i].setPos(y_pos, x_pos)
            label_pool[i].setVisible(True)
