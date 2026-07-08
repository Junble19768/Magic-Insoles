import math

import numpy as np
import pytest

from .cop import compute_foot_cop


def _positions(*coords: tuple[int, float, float]) -> list[tuple[int, float, float]]:
    return list(coords)


def test_zero_pressures_returns_nan_cop() -> None:
    values = np.zeros(16, dtype=float)
    positions = _positions((0, 10.0, 20.0), (1, 30.0, 40.0))
    cop = compute_foot_cop(values, positions)
    assert cop.total_pressure == 0.0
    assert math.isnan(cop.x)
    assert math.isnan(cop.y)


def test_single_sensor_cop_at_centroid() -> None:
    values = np.zeros(16, dtype=float)
    values[3] = 50.0
    positions = _positions((3, 12.5, 34.0))
    cop = compute_foot_cop(values, positions)
    assert cop.total_pressure == pytest.approx(50.0)
    assert cop.x == pytest.approx(12.5)
    assert cop.y == pytest.approx(34.0)


def test_two_equal_pressures_average_centroid() -> None:
    values = np.zeros(16, dtype=float)
    values[0] = 20.0
    values[1] = 20.0
    positions = _positions((0, 0.0, 0.0), (1, 10.0, 20.0))
    cop = compute_foot_cop(values, positions)
    assert cop.total_pressure == pytest.approx(40.0)
    assert cop.x == pytest.approx(5.0)
    assert cop.y == pytest.approx(10.0)


def test_mirror_x_flips_plot_x() -> None:
    values = np.zeros(16, dtype=float)
    values[2] = 30.0
    positions = _positions((2, 8.0, 16.0))
    cop = compute_foot_cop(values, positions, mirror_x=100.0)
    assert cop.x == pytest.approx(92.0)
    assert cop.y == pytest.approx(16.0)


def test_skips_non_positive_pressures() -> None:
    values = np.zeros(16, dtype=float)
    values[0] = -5.0
    values[1] = 0.0
    values[2] = float("nan")
    values[3] = 25.0
    positions = _positions((0, 1.0, 1.0), (1, 2.0, 2.0), (2, 3.0, 3.0), (3, 4.0, 8.0))
    cop = compute_foot_cop(values, positions)
    assert cop.total_pressure == pytest.approx(25.0)
    assert cop.x == pytest.approx(4.0)
    assert cop.y == pytest.approx(8.0)
