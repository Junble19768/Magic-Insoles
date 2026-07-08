import math

import numpy as np
import pytest

from .cop import CopTrajectoryTracker, compute_foot_cop, fit_cop_trajectory_line


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


def test_fit_vertical_trajectory_angle_near_zero() -> None:
    ys = np.linspace(0.0, 10.0, 8)
    xs = np.zeros_like(ys)
    fit = fit_cop_trajectory_line(xs, ys)
    assert fit is not None
    assert fit.angle_deg == pytest.approx(0.0, abs=1e-6)


def test_fit_horizontal_trajectory_angle_near_ninety() -> None:
    xs = np.linspace(0.0, 10.0, 8)
    ys = np.zeros_like(xs)
    fit = fit_cop_trajectory_line(xs, ys)
    assert fit is not None
    assert fit.angle_deg == pytest.approx(90.0, abs=1e-6)


def test_fit_diagonal_trajectory_angle_near_forty_five() -> None:
    t = np.linspace(0.0, 10.0, 8)
    xs = t
    ys = t
    fit = fit_cop_trajectory_line(xs, ys)
    assert fit is not None
    assert fit.angle_deg == pytest.approx(45.0, abs=1e-6)


def test_fit_returns_none_for_insufficient_points() -> None:
    assert fit_cop_trajectory_line(np.array([1.0]), np.array([2.0])) is None
    assert fit_cop_trajectory_line(np.array([float("nan")]), np.array([1.0])) is None


def test_trajectory_tracker_prunes_outside_window() -> None:
    tracker = CopTrajectoryTracker(window_s=10.0)
    tracker.append(0.0, 1.0, 2.0)
    tracker.append(5.0, 3.0, 4.0)
    tracker.append(12.0, 5.0, 6.0)
    tracker.prune(12.0)
    xs, ys = tracker.xs_ys()
    assert xs.size == 2
    assert xs[0] == pytest.approx(3.0)
    assert ys[1] == pytest.approx(6.0)


def test_trajectory_tracker_clear() -> None:
    tracker = CopTrajectoryTracker(window_s=10.0)
    tracker.append(1.0, 1.0, 1.0)
    tracker.clear()
    xs, ys = tracker.xs_ys()
    assert xs.size == 0
    assert ys.size == 0
