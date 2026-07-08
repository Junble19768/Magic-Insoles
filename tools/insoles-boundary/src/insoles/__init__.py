"""Insole mask contour parameterization."""

from insoles.adaptive_bspline import (
    evaluate_adaptive_bspline,
    fit_adaptive_bspline,
    render_mask as render_adaptive_mask,
    sample_curve as sample_adaptive_curve,
)
from insoles.boundary_metrics import BoundaryMetrics, boundary_distances
from insoles.contour import (
    BASE_MAX_CONTROL_POINTS,
    BASE_MIN_CONTROL_POINTS,
    SENSOR_MAX_CONTROL_POINTS,
    SENSOR_MIN_CONTROL_POINTS,
    auto_select_fit,
    auto_select_fit_adaptive,
    compute_iou,
    contour_to_mask,
    control_point_limits,
    extract_largest_contour,
    load_mask,
    mask_to_parametric_contour,
    resample_contour,
)
from insoles.schema import ContourModel, FitMetadata
from insoles.uniform_bspline import (
    DEFAULT_DEGREE,
    FIT_TARGET_POINTS,
    evaluate_uniform_bspline,
    fit_uniform_bspline,
    render_mask,
)

__all__ = [
    "BASE_MAX_CONTROL_POINTS",
    "BASE_MIN_CONTROL_POINTS",
    "BoundaryMetrics",
    "ContourModel",
    "DEFAULT_DEGREE",
    "FIT_TARGET_POINTS",
    "FitMetadata",
    "SENSOR_MAX_CONTROL_POINTS",
    "SENSOR_MIN_CONTROL_POINTS",
    "auto_select_fit",
    "auto_select_fit_adaptive",
    "boundary_distances",
    "compute_iou",
    "contour_to_mask",
    "control_point_limits",
    "evaluate_adaptive_bspline",
    "evaluate_uniform_bspline",
    "extract_largest_contour",
    "fit_adaptive_bspline",
    "fit_uniform_bspline",
    "load_mask",
    "mask_to_parametric_contour",
    "render_adaptive_mask",
    "render_mask",
    "resample_contour",
    "sample_adaptive_curve",
]
