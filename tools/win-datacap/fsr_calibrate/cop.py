from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FootCop:
    x: float
    y: float
    total_pressure: float


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
