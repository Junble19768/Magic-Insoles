"""Boundary distance metrics for contour fitting quality."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.spatial import cKDTree


@dataclass(frozen=True)
class BoundaryMetrics:
    """Symmetric boundary distances between target and fitted curves."""

    boundary_mean: float
    hausdorff_px: float
    target_to_curve_max: float
    curve_to_target_max: float


def boundary_distances(
    target_pts: np.ndarray,
    curve_pts: np.ndarray,
) -> BoundaryMetrics:
    """Compute symmetric mean boundary distance and Hausdorff distance."""
    target = np.asarray(target_pts, dtype=float)
    curve = np.asarray(curve_pts, dtype=float)
    if target.ndim != 2 or target.shape[1] != 2:
        raise ValueError("target_pts must have shape (n, 2)")
    if curve.ndim != 2 or curve.shape[1] != 2:
        raise ValueError("curve_pts must have shape (m, 2)")
    if len(target) == 0 or len(curve) == 0:
        raise ValueError("target_pts and curve_pts must be non-empty")

    tree_curve = cKDTree(curve)
    d_target, _ = tree_curve.query(target, k=1)
    tree_target = cKDTree(target)
    d_curve, _ = tree_target.query(curve, k=1)

    target_to_curve_max = float(np.max(d_target))
    curve_to_target_max = float(np.max(d_curve))
    boundary_mean = float((np.mean(d_target) + np.mean(d_curve)) / 2.0)
    hausdorff_px = float(max(target_to_curve_max, curve_to_target_max))

    return BoundaryMetrics(
        boundary_mean=boundary_mean,
        hausdorff_px=hausdorff_px,
        target_to_curve_max=target_to_curve_max,
        curve_to_target_max=curve_to_target_max,
    )
