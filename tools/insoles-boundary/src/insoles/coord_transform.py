"""Coordinate transforms between top-left image XY and bottom-left row/col."""

from __future__ import annotations

import numpy as np


def transform_points_xy_tl_to_row_col_bl(
    points: np.ndarray,
    image_size: tuple[int, int],
) -> np.ndarray:
    """Convert top-left (x, y) points to bottom-left (row, col) coordinates.

    Origin is the image bottom-left corner. ``col`` increases upward.
    The raster layout matches ``transpose`` then ``horizontal_flip``:

    ``row`` is the first-axis index (original ``x``), and ``col`` is the
    second-axis index (``H - 1 - y``).
    """
    _width, height = image_size
    samples = np.asarray(points, dtype=float)
    if samples.ndim != 2 or samples.shape[1] != 2:
        raise ValueError("points must have shape (n, 2)")

    x = samples[:, 0]
    y = samples[:, 1]
    row = x
    col = height - 1.0 - y
    return np.stack([row, col], axis=1)


def transform_points_row_col_bl_to_xy_tl(
    points: np.ndarray,
    image_size: tuple[int, int],
) -> np.ndarray:
    """Convert bottom-left (row, col) points back to top-left (x, y)."""
    _width, height = image_size
    samples = np.asarray(points, dtype=float)
    if samples.ndim != 2 or samples.shape[1] != 2:
        raise ValueError("points must have shape (n, 2)")

    row = samples[:, 0]
    col = samples[:, 1]
    x = row
    y = height - 1.0 - col
    return np.stack([x, y], axis=1)


def transform_mask_xy_tl_to_row_col_bl(mask: np.ndarray) -> np.ndarray:
    """Reindex a top-left mask into bottom-left row/col storage.

    Equivalent to transposing the image and flipping it horizontally.
    """
    old = np.asarray(mask, dtype=bool)
    if old.ndim != 2:
        raise ValueError("mask must be a 2D array")

    return np.fliplr(old.T)


def transform_mask_row_col_bl_to_xy_tl(mask: np.ndarray) -> np.ndarray:
    """Convert a bottom-left row/col mask back to top-left XY storage."""
    old = np.asarray(mask, dtype=bool)
    if old.ndim != 2:
        raise ValueError("mask must be a 2D array")

    return np.fliplr(old).T
