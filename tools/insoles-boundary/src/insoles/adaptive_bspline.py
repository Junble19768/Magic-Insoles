"""Adaptive non-uniform periodic B-spline fitting and evaluation."""

from __future__ import annotations

import cv2
import numpy as np
from scipy.interpolate import BSpline

from insoles.uniform_bspline import DEFAULT_DEGREE

MIN_PARAM_SPACING = 1e-6


def _extended_control_points(control_points: np.ndarray, degree: int) -> np.ndarray:
    """Wrap control points for periodic B-spline evaluation."""
    points = np.asarray(control_points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("control_points must have shape (n, 2)")

    n_cp = len(points)
    if n_cp < degree + 1:
        raise ValueError(f"Need at least {degree + 1} control points")

    return np.vstack([points[-degree:], points, points[:degree]])


def normalize_knot_params(params: np.ndarray) -> np.ndarray:
    """Sort and normalize knot parameters to [0, 1)."""
    values = np.asarray(params, dtype=float) % 1.0
    values = np.sort(values)
    if len(values) > 1:
        min_spacing = 0.5 / max(len(values) * 4, 1)
        for index in range(1, len(values)):
            if values[index] <= values[index - 1] + min_spacing:
                values[index] = values[index - 1] + min_spacing
        if values[-1] >= 1.0:
            overflow = values[-1] - (1.0 - min_spacing)
            values = (values - overflow) % 1.0
            values = np.sort(values)
    return values


def build_periodic_knots(params: np.ndarray, degree: int) -> np.ndarray:
    """Build a periodic knot vector from arc-length parameters in [0, 1)."""
    params = normalize_knot_params(params)
    n_cp = len(params)
    if n_cp < degree + 1:
        raise ValueError(f"Need at least {degree + 1} knot parameters")

    scaled = params * n_cp
    circular = np.concatenate([scaled - n_cp, scaled, scaled + n_cp])
    knot_count = n_cp + 2 * degree + 1
    knots = np.zeros(knot_count, dtype=float)
    for index in range(knot_count):
        start = index
        window = circular[start : start + degree + 1]
        knots[index] = float(np.mean(window)) - degree
    return knots


def _map_unit_params(
    u: np.ndarray,
    knots: np.ndarray,
    n_cp: int,
    degree: int,
) -> np.ndarray:
    """Map normalized parameters in [0, 1) to the spline knot domain."""
    u = np.asarray(u, dtype=float)
    start = float(knots[degree])
    end = float(knots[n_cp + degree])
    period = end - start
    if period <= 0:
        return u * n_cp
    return start + u * period


def evaluate_adaptive_bspline(
    control_points: np.ndarray,
    params: np.ndarray,
    u: np.ndarray,
    *,
    degree: int = DEFAULT_DEGREE,
) -> np.ndarray:
    """Evaluate a non-uniform periodic B-spline at parameters in [0, 1)."""
    points = np.asarray(control_points, dtype=float)
    n_cp = len(points)
    wrapped = _extended_control_points(points, degree)
    knots = build_periodic_knots(params, degree)
    u_scaled = _map_unit_params(u, knots, n_cp, degree)

    x = BSpline(knots, wrapped[:, 0], degree)(u_scaled)
    y = BSpline(knots, wrapped[:, 1], degree)(u_scaled)
    return np.stack([x, y], axis=1)


def design_matrix(
    u: np.ndarray,
    params: np.ndarray,
    degree: int = DEFAULT_DEGREE,
) -> np.ndarray:
    """Build an (len(u), n_control_points) basis matrix."""
    u = np.asarray(u, dtype=float)
    params = normalize_knot_params(params)
    n_cp = len(params)
    basis = np.zeros((len(u), n_cp), dtype=float)
    unit = np.zeros((n_cp, 2), dtype=float)

    for index in range(n_cp):
        unit[index, 0] = 1.0
        basis[:, index] = evaluate_adaptive_bspline(unit, params, u, degree=degree)[:, 0]
        unit[index, 0] = 0.0

    return basis


def fit_adaptive_bspline(
    target_points: np.ndarray,
    params: np.ndarray,
    *,
    degree: int = DEFAULT_DEGREE,
) -> np.ndarray:
    """Fit a non-uniform periodic B-spline to target points via least squares."""
    points = np.asarray(target_points, dtype=float)
    params = normalize_knot_params(params)
    if len(points) < degree + 1:
        raise ValueError("target_points must contain at least degree + 1 points")
    if len(params) < degree + 1:
        raise ValueError("params must contain at least degree + 1 values")

    m = len(points)
    u = np.arange(m, dtype=float) / m
    basis = design_matrix(u, params, degree=degree)
    x_coef = np.linalg.lstsq(basis, points[:, 0], rcond=None)[0]
    y_coef = np.linalg.lstsq(basis, points[:, 1], rcond=None)[0]
    return np.stack([x_coef, y_coef], axis=1)


def sample_curve(
    control_points: np.ndarray,
    params: np.ndarray,
    *,
    eval_n: int = 2000,
    degree: int = DEFAULT_DEGREE,
) -> np.ndarray:
    """Sample a closed adaptive B-spline as an Nx2 float array."""
    u = np.linspace(0.0, 1.0, eval_n, endpoint=False)
    return evaluate_adaptive_bspline(control_points, params, u, degree=degree)


def render_mask(
    control_points: np.ndarray,
    params: np.ndarray,
    image_size: tuple[int, int],
    *,
    eval_n: int = 2000,
    degree: int = DEFAULT_DEGREE,
) -> np.ndarray:
    """Render a filled boolean mask from adaptive B-spline control points."""
    width, height = image_size
    curve = sample_curve(
        control_points,
        params,
        eval_n=eval_n,
        degree=degree,
    )
    polygon = curve.astype(np.int32)
    canvas = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(canvas, [polygon], 255)
    return canvas > 127


def insert_knot_param(
    params: np.ndarray,
    new_param: float,
    *,
    min_spacing: float,
) -> np.ndarray | None:
    """Insert a knot parameter if it respects the minimum spacing."""
    params = normalize_knot_params(params)
    value = float(new_param % 1.0)
    for existing in params:
        distance = min(abs(value - existing), 1.0 - abs(value - existing))
        if distance < min_spacing:
            return None
    return normalize_knot_params(np.append(params, value))
