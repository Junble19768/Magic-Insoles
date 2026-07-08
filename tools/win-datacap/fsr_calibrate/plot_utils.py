import time
from collections import deque

import numpy as np
import pyqtgraph as pg

from .config import PLOT_WINDOW_S


class TimeSeriesBuffers:
    """Sliding-window time series with relative timestamps."""

    def __init__(self) -> None:
        self.t_origin: float | None = None
        self.t_buf: deque[float] = deque()
        self.v_buf: deque[float] = deque()

    def configure(self, *, maxlen: int) -> None:
        self.t_buf = deque(maxlen=maxlen)
        self.v_buf = deque(maxlen=maxlen)

    def rel_time(self, stamp: float) -> float:
        if self.t_origin is None:
            self.t_origin = stamp
        return stamp - self.t_origin

    def window_bounds(self) -> tuple[float, float]:
        if self.t_origin is None:
            return 0.0, PLOT_WINDOW_S
        win_end = max(PLOT_WINDOW_S, time.time() - self.t_origin)
        return win_end - PLOT_WINDOW_S, win_end

    def clear(self) -> None:
        self.t_origin = None
        self.t_buf.clear()
        self.v_buf.clear()

    def append(self, stamp: float, value: float) -> float:
        t_rel = self.rel_time(stamp)
        self.t_buf.append(t_rel)
        self.v_buf.append(value)
        return t_rel


def series_for_window(
    t_buf: deque[float],
    v_buf: deque[float],
    win_start: float,
    win_end: float,
) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for t, v in zip(t_buf, v_buf):
        if win_start <= t <= win_end and np.isfinite(v):
            xs.append(t)
            ys.append(v)
    return xs, ys


def apply_auto_y_range(viewbox: pg.ViewBox, values: list[float]) -> None:
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


def setup_dual_axis_plot(
    plot: pg.PlotItem,
    *,
    left_label: str,
    left_color: str,
    right_label: str,
    right_color: str,
) -> tuple[pg.ViewBox, pg.PlotDataItem, pg.PlotDataItem]:
    plot.setLabel("bottom", "时间 (s)")
    plot.setLabel("left", left_label, color=left_color)
    plot.showGrid(x=True, y=True, alpha=0.3)
    plot.addLegend(offset=(10, 10))

    force_view = pg.ViewBox()
    plot.showAxis("right")
    plot.scene().addItem(force_view)
    plot.getAxis("right").linkToView(force_view)
    force_view.setXLink(plot)
    plot.getAxis("right").setLabel(right_label, color=right_color)

    left_curve = plot.plot(pen=pg.mkPen(color=left_color, width=2), name=left_label)
    right_curve = pg.PlotCurveItem(pen=pg.mkPen(color=right_color, width=2), name=right_label)
    force_view.addItem(right_curve)

    def sync_views() -> None:
        force_view.setGeometry(plot.vb.sceneBoundingRect())
        force_view.linkedViewChanged(plot.vb, force_view.XAxis)

    plot.vb.sigResized.connect(sync_views)
    sync_views()
    plot.enableAutoRange(axis="x", enable=False)
    plot.enableAutoRange(axis="y", enable=False)
    force_view.enableAutoRange(axis="y", enable=False)
    plot.setXRange(0, PLOT_WINDOW_S, padding=0)
    return force_view, left_curve, right_curve


class FpsTracker:
    def __init__(self) -> None:
        self._count = 0
        self._last_report = time.monotonic()
        self.fps = 0.0

    def tick(self) -> None:
        self._count += 1

    def maybe_report(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_report
        if elapsed < 1.0:
            return
        self.fps = self._count / elapsed if elapsed > 0 else 0.0
        self._count = 0
        self._last_report = now
