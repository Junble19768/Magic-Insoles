"""Uniform periodic B-spline fitting and evaluation."""

from __future__ import annotations

import cv2
import numpy as np
from scipy.interpolate import BSpline


DEFAULT_DEGREE = 3
FIT_TARGET_POINTS = 200


def _extended_control_points(control_points: np.ndarray, degree: int) -> np.ndarray:
    """Wrap control points for periodic B-spline evaluation."""
    points = np.asarray(control_points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("control_points must have shape (n, 2)")

    n_cp = len(points)
    if n_cp < degree + 1:
        raise ValueError(f"Need at least {degree + 1} control points")

    return np.vstack([points[-degree:], points, points[:degree]])


def _knot_vector(n_control_points: int, degree: int) -> np.ndarray:
    """Build a uniform knot vector for periodic evaluation."""
    return np.arange(
        -degree,
        -degree + n_control_points + 3 * degree + 1,
        dtype=float,
    )


def design_matrix(
    u: np.ndarray,
    n_control_points: int,
    degree: int = DEFAULT_DEGREE,
) -> np.ndarray:
    """Build an (len(u), n_control_points) basis matrix."""
    u = np.asarray(u, dtype=float)
    basis = np.zeros((len(u), n_control_points), dtype=float)
    unit = np.zeros((n_control_points, 2), dtype=float)

    for index in range(n_control_points):
        unit[index, 0] = 1.0
        basis[:, index] = evaluate_uniform_bspline(unit, u, degree=degree)[:, 0]
        unit[index, 0] = 0.0

    return basis


def fit_uniform_bspline(
    target_points: np.ndarray,
    n_control_points: int,
    *,
    degree: int = DEFAULT_DEGREE,
) -> np.ndarray:
    """Fit a uniform periodic B-spline to target points via least squares."""
    points = np.asarray(target_points, dtype=float)
    if len(points) < degree + 1:
        raise ValueError("target_points must contain at least degree + 1 points")

    m = len(points)
    u = np.arange(m, dtype=float) / m
    basis = design_matrix(u, n_control_points, degree=degree)
    x_coef = np.linalg.lstsq(basis, points[:, 0], rcond=None)[0]
    y_coef = np.linalg.lstsq(basis, points[:, 1], rcond=None)[0]
    return np.stack([x_coef, y_coef], axis=1)


def evaluate_uniform_bspline(
    control_points: np.ndarray,
    u: np.ndarray,
    *,
    degree: int = DEFAULT_DEGREE,
) -> np.ndarray:
    """Evaluate a uniform periodic B-spline at parameters in [0, 1)."""
    points = np.asarray(control_points, dtype=float)
    n_cp = len(points)
    wrapped = _extended_control_points(points, degree)
    knots = _knot_vector(n_cp, degree)
    u_scaled = np.asarray(u, dtype=float) * n_cp

    x = BSpline(knots, wrapped[:, 0], degree)(u_scaled)
    y = BSpline(knots, wrapped[:, 1], degree)(u_scaled)
    return np.stack([x, y], axis=1)


def render_mask(
    control_points: np.ndarray,
    image_size: tuple[int, int],
    *,
    eval_n: int = 2000,
    degree: int = DEFAULT_DEGREE,
) -> np.ndarray:
    """Render a filled boolean mask from uniform B-spline control points."""
    width, height = image_size
    u = np.linspace(0.0, 1.0, eval_n, endpoint=False)
    curve = evaluate_uniform_bspline(control_points, u, degree=degree)
    polygon = curve.astype(np.int32)
    canvas = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(canvas, [polygon], 255)
    return canvas > 127
