from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import COP_TRAJECTORY_MIN_POINTS


@dataclass(frozen=True)
class FootCop:
    x: float
    y: float
    total_pressure: float


@dataclass(frozen=True)
class CopTrajectorySample:
    stamp: float
    x: float
    y: float


@dataclass(frozen=True)
class CopLineFit:
    angle_deg: float
    centroid: tuple[float, float]
    direction: tuple[float, float]
    point_count: int


class CopTrajectoryTracker:
    """Sliding-window buffer of COP samples keyed by device timestamp."""

    def __init__(self, window_s: float) -> None:
        self._window_s = float(window_s)
        self._samples: list[CopTrajectorySample] = []

    def append(self, stamp: float, x: float, y: float) -> None:
        if not np.isfinite(stamp) or not np.isfinite(x) or not np.isfinite(y):
            return
        self._samples.append(CopTrajectorySample(stamp=float(stamp), x=float(x), y=float(y)))

    def prune(self, stamp: float) -> None:
        if not np.isfinite(stamp):
            return
        cutoff = float(stamp) - self._window_s
        self._samples = [sample for sample in self._samples if sample.stamp >= cutoff]

    def clear(self) -> None:
        self._samples.clear()

    def xs_ys(self) -> tuple[np.ndarray, np.ndarray]:
        if not self._samples:
            return np.array([], dtype=float), np.array([], dtype=float)
        xs = np.array([sample.x for sample in self._samples], dtype=float)
        ys = np.array([sample.y for sample in self._samples], dtype=float)
        return xs, ys

    def __len__(self) -> int:
        return len(self._samples)


def compute_foot_cop(
    foot_values: np.ndarray,
    sensor_positions: list[tuple[int, float, float]],
    *,
    mirror_x: float | None = None,
) -> FootCop:
    """Compute pressure-weighted center of pressure for one foot.

  Each sensor contributes at its region centroid ``(cx, cy)`` with weight equal
  to its pressure value. Only finite pressures strictly greater than zero are
  included. When ``mirror_x`` is set, plot X becomes ``mirror_x - cx`` (left
  foot display convention).
    """
    weighted_x = 0.0
    weighted_y = 0.0
    total_pressure = 0.0

    for local_idx, cx, cy in sensor_positions:
        pressure = float(foot_values[local_idx])
        if not np.isfinite(pressure) or pressure <= 0.0:
            continue
        plot_x = mirror_x - cx if mirror_x is not None else cx
        weighted_x += plot_x * pressure
        weighted_y += cy * pressure
        total_pressure += pressure

    if total_pressure <= 0.0:
        return FootCop(x=float("nan"), y=float("nan"), total_pressure=0.0)

    return FootCop(
        x=weighted_x / total_pressure,
        y=weighted_y / total_pressure,
        total_pressure=total_pressure,
    )


def fit_cop_trajectory_line(
    xs: np.ndarray,
    ys: np.ndarray,
    *,
    min_points: int = COP_TRAJECTORY_MIN_POINTS,
) -> CopLineFit | None:
    """Fit a line to COP trajectory points via SVD; return angle from +Y axis."""
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    mask = np.isfinite(xs) & np.isfinite(ys)
    xs = xs[mask]
    ys = ys[mask]
    if xs.size < min_points:
        return None

    pts = np.column_stack([xs, ys])
    centroid = pts.mean(axis=0)
    centered = pts - centroid
    if np.allclose(centered, 0.0):
        return None

    _, _, vh = np.linalg.svd(centered, full_matrices=False)
    direction = vh[0]
    dx, dy = float(direction[0]), float(direction[1])
    if dy < 0.0:
        dx, dy = -dx, -dy

    norm = float(np.hypot(dx, dy))
    if norm <= 0.0:
        return None
    dx /= norm
    dy /= norm

    angle_deg = float(np.degrees(np.arctan2(abs(dx), abs(dy))))
    return CopLineFit(
        angle_deg=angle_deg,
        centroid=(float(centroid[0]), float(centroid[1])),
        direction=(dx, dy),
        point_count=int(xs.size),
    )


def fit_line_segment(
    fit: CopLineFit,
    xs: np.ndarray,
    ys: np.ndarray,
    *,
    half_extent: float | None = None,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return line segment endpoints for plotting a fitted trajectory line."""
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    mask = np.isfinite(xs) & np.isfinite(ys)
    xs = xs[mask]
    ys = ys[mask]

    cx, cy = fit.centroid
    dx, dy = fit.direction

    if xs.size == 0:
        extent = half_extent if half_extent is not None else 1.0
        return (cx - dx * extent, cy - dy * extent), (cx + dx * extent, cy + dy * extent)

    projections = (xs - cx) * dx + (ys - cy) * dy
    t_min = float(projections.min())
    t_max = float(projections.max())
    if half_extent is not None:
        half = float(half_extent)
        t_min = min(t_min, -half)
        t_max = max(t_max, half)

    return (cx + dx * t_min, cy + dy * t_min), (cx + dx * t_max, cy + dy * t_max)
