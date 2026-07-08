"""Geometry helpers for base-axis-aligned OBB re-framing."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class ObbFrame:
    """Derived OBB frame and old-to-new affine transform."""

    axis_start: tuple[float, float]
    axis_end: tuple[float, float]
    axis_long: np.ndarray
    axis_short: np.ndarray
    min_long: float
    max_long: float
    min_short: float
    max_short: float
    margin_cm: float
    pixel_scale_cm: float
    output_size: tuple[int, int]
    affine_old_to_new: np.ndarray
    corners_old: np.ndarray


def _normalize(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm == 0:
        raise ValueError("Axis vector must be non-zero")
    return vector / norm


def build_obb_frame(
    points: np.ndarray,
    *,
    axis_start: tuple[float, float],
    axis_end: tuple[float, float],
    margin_cm: float,
    pixel_scale_cm: float,
) -> ObbFrame:
    """Build an expanded OBB frame from contour points and a given long axis."""
    samples = np.asarray(points, dtype=float)
    if samples.ndim != 2 or samples.shape[1] != 2:
        raise ValueError("points must have shape (n, 2)")
    if len(samples) < 3:
        raise ValueError("Need at least 3 points to derive an OBB")
    if pixel_scale_cm <= 0:
        raise ValueError("pixel_scale_cm must be positive")

    axis = np.array([axis_end[0] - axis_start[0], axis_end[1] - axis_start[1]], dtype=float)
    axis_long = _normalize(axis)
    axis_short = np.array([-axis_long[1], axis_long[0]], dtype=float)

    long_proj = samples @ axis_long
    short_proj = samples @ axis_short

    margin_px = margin_cm / pixel_scale_cm
    min_long = float(np.min(long_proj) - margin_px)
    max_long = float(np.max(long_proj) + margin_px)
    min_short = float(np.min(short_proj) - margin_px)
    max_short = float(np.max(short_proj) + margin_px)

    out_width = int(np.ceil(max_long - min_long)) + 1
    out_height = int(np.ceil(max_short - min_short)) + 1

    affine = np.array(
        [
            [axis_long[0], axis_long[1], -min_long],
            [axis_short[0], axis_short[1], -min_short],
        ],
        dtype=np.float32,
    )

    c00 = min_long * axis_long + min_short * axis_short
    c10 = max_long * axis_long + min_short * axis_short
    c11 = max_long * axis_long + max_short * axis_short
    c01 = min_long * axis_long + max_short * axis_short
    corners_old = np.vstack([c00, c10, c11, c01]).astype(float)

    return ObbFrame(
        axis_start=axis_start,
        axis_end=axis_end,
        axis_long=axis_long,
        axis_short=axis_short,
        min_long=min_long,
        max_long=max_long,
        min_short=min_short,
        max_short=max_short,
        margin_cm=margin_cm,
        pixel_scale_cm=pixel_scale_cm,
        output_size=(out_width, out_height),
        affine_old_to_new=affine,
        corners_old=corners_old,
    )


def transform_points(points: np.ndarray, affine_old_to_new: np.ndarray) -> np.ndarray:
    """Apply a 2x3 affine transform to Nx2 points."""
    samples = np.asarray(points, dtype=float)
    affine = np.asarray(affine_old_to_new, dtype=float)
    if affine.shape != (2, 3):
        raise ValueError("affine_old_to_new must have shape (2, 3)")
    if samples.ndim != 2 or samples.shape[1] != 2:
        raise ValueError("points must have shape (n, 2)")

    linear = affine[:, :2]
    shift = affine[:, 2]
    return samples @ linear.T + shift


def rotated_output_size(width: int, height: int) -> tuple[int, int]:
    """Return (width, height) after a 90-degree clockwise rotation."""
    return height, width


def rotate_image_90_clockwise(image: np.ndarray) -> np.ndarray:
    """Rotate a 2D image 90 degrees clockwise."""
    if image.ndim != 2:
        raise ValueError("image must be a 2D array")
    return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)


def rotate_points_90_clockwise(
    points: np.ndarray,
    width: int,
    height: int,
) -> np.ndarray:
    """Rotate top-left (x, y) points 90 degrees clockwise within a WxH canvas."""
    samples = np.asarray(points, dtype=float)
    if samples.ndim != 2 or samples.shape[1] != 2:
        raise ValueError("points must have shape (n, 2)")

    x = samples[:, 0]
    y = samples[:, 1]
    new_x = (height - 1) - y
    new_y = x
    return np.stack([new_x, new_y], axis=1)
