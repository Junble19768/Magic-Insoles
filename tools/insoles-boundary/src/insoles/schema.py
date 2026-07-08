"""JSON schema for parametric B-spline contours."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from insoles.adaptive_bspline import evaluate_adaptive_bspline
from insoles.uniform_bspline import DEFAULT_DEGREE, evaluate_uniform_bspline

DEFAULT_PIXEL_SCALE_CM = 0.00855


def pixel_scale_for_dimension_scale(
    source_pixel_scale_cm: float,
    dimension_scale: float,
) -> float:
    """Return cm/px after resizing image dimensions by ``dimension_scale``."""
    if dimension_scale <= 0:
        raise ValueError("dimension_scale must be positive")
    return source_pixel_scale_cm / dimension_scale


@dataclass
class FitMetadata:
    """Quality metrics from B-spline fitting."""

    degree: int
    n_control_points: int
    eval_n: int
    iou: float
    optimization_metric: str = "iou"
    metric_value: float = 0.0
    hausdorff_px: float = 0.0
    knot_params: list[float] | None = None


@dataclass
class ContourModel:
    """Parametric B-spline contour for one mask."""

    id: str
    contour_type: str
    image_size: list[int]
    pixel_scale_cm: float
    fit: FitMetadata
    control_points: list[list[float]]
    notes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContourModel:
        """Parse from a dictionary."""
        fit_data = dict(data["fit"])
        fit_data.setdefault("optimization_metric", "iou")
        fit_data.setdefault("metric_value", float(fit_data.get("iou", 0.0)))
        fit_data.setdefault("hausdorff_px", 0.0)
        fit_data.setdefault("knot_params", None)
        fit = FitMetadata(**fit_data)
        return cls(
            id=data["id"],
            contour_type=data["contour_type"],
            image_size=list(data["image_size"]),
            pixel_scale_cm=float(data["pixel_scale_cm"]),
            fit=fit,
            control_points=[list(point) for point in data["control_points"]],
            notes=dict(data.get("notes", {})),
        )

    def control_points_array(self) -> np.ndarray:
        """Return control points as an Nx2 float array."""
        return np.array(self.control_points, dtype=float)

    def knot_params_array(self) -> np.ndarray:
        """Return knot parameters as a 1D float array."""
        if not self.fit.knot_params:
            raise ValueError("knot_params are required for adaptive_bspline contours")
        return np.array(self.fit.knot_params, dtype=float)

    def sample_curve(self, eval_n: int | None = None) -> np.ndarray:
        """Sample the closed B-spline as an Nx2 float array."""
        n = eval_n if eval_n is not None else self.fit.eval_n
        u = np.linspace(0.0, 1.0, n, endpoint=False)
        if self.contour_type == "adaptive_bspline":
            return evaluate_adaptive_bspline(
                self.control_points_array(),
                self.knot_params_array(),
                u,
                degree=self.fit.degree,
            )
        return evaluate_uniform_bspline(
            self.control_points_array(),
            u,
            degree=self.fit.degree,
        )

    def to_json(self, path: Path | str, *, indent: int = 2) -> None:
        """Write model to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=indent)
            handle.write("\n")

    @classmethod
    def from_json(cls, path: Path | str) -> ContourModel:
        """Load model from a JSON file."""
        with Path(path).open(encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))
