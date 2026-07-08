"""Contour extraction and B-spline parameterization."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

from insoles.adaptive_bspline import (
    fit_adaptive_bspline,
    insert_knot_param,
    render_mask as render_adaptive_mask,
    sample_curve as sample_adaptive_curve,
)
from insoles.boundary_metrics import BoundaryMetrics, boundary_distances
from insoles.schema import DEFAULT_PIXEL_SCALE_CM, ContourModel, FitMetadata
from insoles.uniform_bspline import (
    DEFAULT_DEGREE,
    FIT_TARGET_POINTS,
    fit_uniform_bspline,
    render_mask,
)

SENSOR_MIN_CONTROL_POINTS = 10
SENSOR_MAX_CONTROL_POINTS = 100
BASE_MIN_CONTROL_POINTS = 10
BASE_MAX_CONTROL_POINTS = 150
DEFAULT_EVAL_N = 2000
MIN_SPLINE_POINTS = 4
SEARCH_STEP = 5
REFINE_RADIUS = 5


def load_mask(path: Path | str) -> np.ndarray:
    """Load a mask PNG and return a boolean array (True = selected)."""
    image = np.array(Image.open(path))
    channel = image[..., 0] if image.ndim == 3 else image
    return channel > 127


def extract_largest_contour(mask: np.ndarray) -> np.ndarray:
    """Extract the largest external contour as an Nx2 float array."""
    binary = mask.astype(np.uint8) * 255
    contours, _ = cv2.findContours(
        binary,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_NONE,
    )
    if not contours:
        raise ValueError("No external contour found in mask")

    largest = max(contours, key=cv2.contourArea)
    return largest[:, 0, :].astype(float)


def resample_contour(points: np.ndarray, n: int) -> np.ndarray:
    """Uniformly resample a closed contour by arc length."""
    if len(points) < 2:
        raise ValueError("Contour must contain at least two points")

    closed = np.vstack([points, points[0:1]])
    diffs = np.diff(closed, axis=0)
    segment_lengths = np.sqrt(np.sum(diffs**2, axis=1))
    cumulative = np.insert(np.cumsum(segment_lengths), 0, 0.0)
    total_length = cumulative[-1]
    if total_length == 0:
        raise ValueError("Contour has zero arc length")

    sample_positions = np.linspace(0.0, total_length, n)
    x = np.interp(sample_positions, cumulative, closed[:, 0])
    y = np.interp(sample_positions, cumulative, closed[:, 1])
    return np.stack([x, y], axis=1)


def control_point_limits(mask_id: str) -> tuple[int, int]:
    """Return ``(min_cp, max_cp)`` for a mask identifier."""
    if mask_id == "base":
        return BASE_MIN_CONTROL_POINTS, BASE_MAX_CONTROL_POINTS
    return SENSOR_MIN_CONTROL_POINTS, SENSOR_MAX_CONTROL_POINTS


def compute_iou(original: np.ndarray, reconstructed: np.ndarray) -> float:
    """Compute intersection-over-union between two boolean masks."""
    intersection = np.logical_and(original, reconstructed).sum()
    union = np.logical_or(original, reconstructed).sum()
    if union == 0:
        return 1.0
    return float(intersection / union)


def _search_values(min_cp: int, max_cp: int) -> list[int]:
    """Build coarse and refined control-point counts to evaluate."""
    search_min = max(min_cp, MIN_SPLINE_POINTS)
    coarse = list(range(search_min, max_cp + 1, SEARCH_STEP))
    if not coarse or coarse[-1] != max_cp:
        coarse.append(max_cp)
    return sorted(set(coarse))


def _refined_values(
    coarse_values: list[int],
    best_n_cp: int,
    min_cp: int,
    max_cp: int,
) -> list[int]:
    """Add integer counts around the best coarse candidate."""
    refined = set(coarse_values)
    low = max(min_cp, best_n_cp - REFINE_RADIUS)
    high = min(max_cp, best_n_cp + REFINE_RADIUS)
    refined.update(range(low, high + 1))
    return sorted(refined)


def auto_select_fit(
    contour: np.ndarray,
    mask: np.ndarray,
    image_size: tuple[int, int],
    *,
    min_control_points: int,
    max_control_points: int,
    eval_n: int = DEFAULT_EVAL_N,
    degree: int = DEFAULT_DEGREE,
) -> tuple[np.ndarray, int, float]:
    """Pick control-point count that maximizes IOU within the given bounds."""
    target_points = resample_contour(contour, FIT_TARGET_POINTS)

    best_control_points: np.ndarray | None = None
    best_n_cp = 0
    best_iou = -1.0

    def evaluate(n_cp: int) -> None:
        nonlocal best_control_points, best_n_cp, best_iou
        try:
            control_points = fit_uniform_bspline(
                target_points,
                n_cp,
                degree=degree,
            )
            reconstructed = render_mask(
                control_points,
                image_size,
                eval_n=eval_n,
                degree=degree,
            )
            iou = compute_iou(mask, reconstructed)
        except (ValueError, np.linalg.LinAlgError):
            return

        if iou > best_iou or (iou == best_iou and n_cp > best_n_cp):
            best_control_points = control_points
            best_n_cp = n_cp
            best_iou = iou

    coarse_values = _search_values(min_control_points, max_control_points)
    for n_cp in coarse_values:
        evaluate(n_cp)

    anchor = best_n_cp if best_n_cp else coarse_values[0]
    for n_cp in _refined_values(
        coarse_values,
        anchor,
        min_control_points,
        max_control_points,
    ):
        if n_cp in coarse_values:
            continue
        evaluate(n_cp)

    if best_control_points is None:
        raise RuntimeError(
            "Failed to fit a uniform B-spline within control-point bounds "
            f"[{min_control_points}, {max_control_points}]"
        )

    return best_control_points, best_n_cp, best_iou


def _candidate_sort_key(
    boundary_mean: float,
    hausdorff_px: float,
    n_cp: int,
    *,
    optimization_metric: str,
) -> tuple[float, int]:
    """Return a sort key for selecting the best adaptive fit candidate."""
    if optimization_metric == "hausdorff":
        return (hausdorff_px, n_cp)
    return (boundary_mean, n_cp)


def auto_select_fit_adaptive(
    contour: np.ndarray,
    mask: np.ndarray,
    image_size: tuple[int, int],
    *,
    min_control_points: int,
    max_control_points: int,
    eval_n: int = DEFAULT_EVAL_N,
    degree: int = DEFAULT_DEGREE,
    optimization_metric: str = "boundary_mean",
) -> tuple[np.ndarray, np.ndarray, int, BoundaryMetrics, float]:
    """Adaptively insert knots and pick the fit that minimizes boundary distance."""
    target_points = resample_contour(contour, FIT_TARGET_POINTS)
    target_arc_params = np.linspace(0.0, 1.0, FIT_TARGET_POINTS, endpoint=False)
    min_spacing = 1.0 / (2.0 * FIT_TARGET_POINTS)

    search_min = max(min_control_points, MIN_SPLINE_POINTS)
    params = np.linspace(0.0, 1.0, search_min, endpoint=False)

    candidates: list[
        tuple[np.ndarray, np.ndarray, int, BoundaryMetrics, float]
    ] = []

    while len(params) <= max_control_points:
        try:
            control_points = fit_adaptive_bspline(
                target_points,
                params,
                degree=degree,
            )
            reconstructed = render_adaptive_mask(
                control_points,
                params,
                image_size,
                eval_n=eval_n,
                degree=degree,
            )
            curve_points = sample_adaptive_curve(
                control_points,
                params,
                eval_n=eval_n,
                degree=degree,
            )
            metrics = boundary_distances(target_points, curve_points)
            iou = compute_iou(mask, reconstructed)
            candidates.append(
                (control_points, params.copy(), len(params), metrics, iou)
            )
        except (ValueError, np.linalg.LinAlgError):
            break

        if len(params) >= max_control_points:
            break

        tree = cKDTree(curve_points)
        distances, _ = tree.query(target_points, k=1)
        worst_indices = np.argsort(-distances)
        next_params = None
        for worst_index in worst_indices[:10]:
            next_params = insert_knot_param(
                params,
                target_arc_params[int(worst_index)],
                min_spacing=min_spacing,
            )
            if next_params is not None:
                break
        if next_params is None:
            break
        params = next_params

    if not candidates:
        raise RuntimeError(
            "Failed to fit an adaptive B-spline within control-point bounds "
            f"[{min_control_points}, {max_control_points}]"
        )

    best = min(
        candidates,
        key=lambda item: _candidate_sort_key(
            item[3].boundary_mean,
            item[3].hausdorff_px,
            item[2],
            optimization_metric=optimization_metric,
        ),
    )
    control_points, params, n_cp, metrics, iou = best
    return control_points, params, n_cp, metrics, iou


def mask_to_parametric_contour(
    mask: np.ndarray,
    mask_id: str,
    *,
    min_control_points: int | None = None,
    max_control_points: int | None = None,
    eval_n: int = DEFAULT_EVAL_N,
    pixel_scale_cm: float = DEFAULT_PIXEL_SCALE_CM,
    notes: dict | None = None,
    fit_mode: str = "uniform",
    optimization_metric: str = "boundary_mean",
) -> ContourModel:
    """Convert a boolean mask to a parametric B-spline contour model."""
    height, width = mask.shape
    image_size = (width, height)
    contour = extract_largest_contour(mask)

    default_min, default_max = control_point_limits(mask_id)
    min_cp = default_min if min_control_points is None else min_control_points
    max_cp = default_max if max_control_points is None else max_control_points

    if fit_mode == "adaptive":
        control_points, knot_params, n_cp, metrics, iou = auto_select_fit_adaptive(
            contour,
            mask,
            image_size,
            min_control_points=min_cp,
            max_control_points=max_cp,
            eval_n=eval_n,
            optimization_metric=optimization_metric,
        )
        metric_value = (
            metrics.hausdorff_px
            if optimization_metric == "hausdorff"
            else metrics.boundary_mean
        )
        return ContourModel(
            id=mask_id,
            contour_type="adaptive_bspline",
            image_size=[width, height],
            pixel_scale_cm=pixel_scale_cm,
            fit=FitMetadata(
                degree=DEFAULT_DEGREE,
                n_control_points=n_cp,
                eval_n=eval_n,
                iou=iou,
                optimization_metric=optimization_metric,
                metric_value=metric_value,
                hausdorff_px=metrics.hausdorff_px,
                knot_params=[float(value) for value in knot_params],
            ),
            control_points=[[float(x), float(y)] for x, y in control_points],
            notes=dict(notes or {}),
        )

    control_points, n_cp, iou = auto_select_fit(
        contour,
        mask,
        image_size,
        min_control_points=min_cp,
        max_control_points=max_cp,
        eval_n=eval_n,
    )

    return ContourModel(
        id=mask_id,
        contour_type="uniform_bspline",
        image_size=[width, height],
        pixel_scale_cm=pixel_scale_cm,
        fit=FitMetadata(
            degree=DEFAULT_DEGREE,
            n_control_points=n_cp,
            eval_n=eval_n,
            iou=iou,
            optimization_metric="iou",
            metric_value=iou,
        ),
        control_points=[[float(x), float(y)] for x, y in control_points],
        notes=dict(notes or {}),
    )


def contour_to_mask(
    model: ContourModel,
    *,
    eval_n: int | None = None,
) -> np.ndarray:
    """Render a boolean mask from a B-spline contour model."""
    width, height = model.image_size
    n = eval_n if eval_n is not None else model.fit.eval_n
    if model.contour_type == "adaptive_bspline":
        return render_adaptive_mask(
            model.control_points_array(),
            model.knot_params_array(),
            (width, height),
            eval_n=n,
            degree=model.fit.degree,
        )
    return render_mask(
        model.control_points_array(),
        (width, height),
        eval_n=n,
        degree=model.fit.degree,
    )
