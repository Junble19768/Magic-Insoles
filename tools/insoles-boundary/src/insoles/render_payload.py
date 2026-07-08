"""Compact portable payload for rendering insole regions elsewhere."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from insoles.adaptive_bspline import sample_curve as sample_adaptive_curve
from insoles.schema import ContourModel
from insoles.uniform_bspline import evaluate_uniform_bspline

RENDER_PAYLOAD_SCHEMA = "insoles.render_payload/v1"
COORDINATE_SYSTEM = {
    "origin": "top_left",
    "x_axis": "right",
    "y_axis": "down",
    "units": "px",
}


def _round_floats(values: list[float], *, precision: int) -> list[float]:
    return [round(float(value), precision) for value in values]


def _round_points(
    points: list[list[float]],
    *,
    precision: int,
) -> list[list[float]]:
    return [[round(float(x), precision), round(float(y), precision)] for x, y in points]


def region_to_render_dict(
    model: ContourModel,
    *,
    float_precision: int = 4,
) -> dict[str, Any]:
    """Extract render-only fields from a contour model."""
    region: dict[str, Any] = {
        "id": model.id,
        "role": "base" if model.id == "base" else "sensor",
        "cp": _round_points(model.control_points, precision=float_precision),
    }
    if model.contour_type == "adaptive_bspline":
        region["knots"] = _round_floats(
            model.fit.knot_params or [],
            precision=float_precision,
        )
    duplicate_of = model.notes.get("duplicate_of")
    if duplicate_of:
        region["dup"] = duplicate_of
    return region


def build_render_payload(
    models: list[ContourModel],
    *,
    float_precision: int = 4,
) -> dict[str, Any]:
    """Build a self-contained render payload from contour models."""
    if not models:
        raise ValueError("At least one contour model is required")

    reference = models[0]
    width, height = reference.image_size
    pixel_scale_cm = reference.pixel_scale_cm
    for model in models[1:]:
        if model.image_size != reference.image_size:
            raise ValueError(
                f"Region {model.id} image_size {model.image_size} "
                f"!= {reference.image_size}"
            )
        if model.pixel_scale_cm != pixel_scale_cm:
            raise ValueError(
                f"Region {model.id} pixel_scale_cm {model.pixel_scale_cm} "
                f"!= {pixel_scale_cm}"
            )

    contour_type = reference.contour_type
    if any(model.contour_type != contour_type for model in models):
        raise ValueError("All regions must share the same contour_type")

    spline: dict[str, Any] = {
        "type": contour_type,
        "degree": reference.fit.degree,
        "eval_n": reference.fit.eval_n,
        "closed": True,
    }
    if contour_type == "adaptive_bspline":
        spline["knot_field"] = "regions[].knots"
    else:
        spline["knot_field"] = None

    return {
        "schema": RENDER_PAYLOAD_SCHEMA,
        "coordinate_system": COORDINATE_SYSTEM,
        "canvas": {
            "width": int(width),
            "height": int(height),
            "pixel_scale_cm": round(float(pixel_scale_cm), 6),
        },
        "spline": spline,
        "render_steps": [
            "For each region, sample the closed B-spline at u=0..1 (endpoint=false).",
            "Use eval_n samples; fill the polygon on a width x height canvas.",
            "Adaptive regions require cp + knots; uniform regions require cp only.",
        ],
        "regions": [
            region_to_render_dict(model, float_precision=float_precision)
            for model in models
        ],
    }


def load_models(contour_dir: Path) -> list[ContourModel]:
    """Load contour JSON models sorted with base first."""
    def sort_key(path: Path) -> tuple[int, str]:
        stem = path.stem
        if stem == "base":
            return (0, stem)
        if stem.isdigit():
            return (1, f"{int(stem):04d}")
        return (2, stem)

    paths = sorted(contour_dir.glob("*.json"), key=sort_key)
    if not paths:
        raise FileNotFoundError(f"No contour JSON files in {contour_dir}")
    return [ContourModel.from_json(path) for path in paths]


def write_render_payload(
    payload: dict[str, Any],
    output_path: Path,
    *,
    compact: bool = True,
) -> None:
    """Write render payload JSON to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        if compact:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


@dataclass(frozen=True)
class _PreparedBoundaryRenderer:
    width: int
    height: int
    spline: dict[str, Any]
    # sensor_masks[i] corresponds to FSR index i (region id == i+1).
    sensor_masks: list[np.ndarray]
    # sensor_centroids[i] corresponds to FSR index i (region id == i+1).
    sensor_centroids: list[tuple[int, float, float]]


_RENDERER_CACHE: dict[int, _PreparedBoundaryRenderer] = {}


def load_render_payload(payload_path: Path) -> dict[str, Any]:
    """Load a portable insole render payload JSON file."""
    payload_path = Path(payload_path)
    with payload_path.open(encoding="utf-8") as handle:
        payload: dict[str, Any] = json.load(handle)

    if payload.get("schema") != RENDER_PAYLOAD_SCHEMA:
        raise ValueError(
            f"Invalid schema {payload.get('schema')} (expected {RENDER_PAYLOAD_SCHEMA})"
        )
    if not isinstance(payload.get("regions"), list) or not payload["regions"]:
        raise ValueError("render_payload missing non-empty regions[]")
    if "canvas" not in payload or "spline" not in payload:
        raise ValueError("render_payload missing canvas/spline")
    if "width" not in payload["canvas"] or "height" not in payload["canvas"]:
        raise ValueError("render_payload canvas missing width/height")

    return payload


def _sample_region_polygon(
    *,
    region: dict[str, Any],
    spline: dict[str, Any],
) -> np.ndarray:
    """Sample a closed region polygon as Nx2 float points in pixel space."""
    cp = np.asarray(region["cp"], dtype=float)
    eval_n = int(spline["eval_n"])
    degree = int(spline["degree"])
    spline_type = str(spline["type"])

    if spline_type == "adaptive_bspline":
        knots = np.asarray(region.get("knots", []), dtype=float)
        if knots.size == 0:
            raise ValueError(f"adaptive_bspline region {region.get('id')} missing knots")
        return sample_adaptive_curve(cp, knots, eval_n=eval_n, degree=degree)

    if spline_type == "uniform_bspline":
        u = np.linspace(0.0, 1.0, eval_n, endpoint=False)
        return evaluate_uniform_bspline(cp, u, degree=degree)

    raise ValueError(f"Unsupported spline.type={spline_type}")


def region_label_centroids(payload: dict[str, Any]) -> list[tuple[int, float, float]]:
    """Return ``[(fsr_index, cx, cy), ...]`` for each sensor region (sorted by fsr_index)."""
    renderer = _prepare_renderer(payload)
    return list(renderer.sensor_centroids)


def render_sensor_field(
    payload: dict[str, Any],
    sensor_values: np.ndarray,
    *,
    blur_sigma: float = 0.0,
) -> np.ndarray:
    """Render a scalar field for sensor regions into a float (height x width) array."""
    renderer = _prepare_renderer(payload)
    field = np.zeros((renderer.height, renderer.width), dtype=np.float32)
    values = np.asarray(sensor_values, dtype=float)

    # Fill with max so overlapping duplicated geometries don't "erase" larger values.
    for fsr_index, mask in enumerate(renderer.sensor_masks):
        if fsr_index >= len(values):
            break
        value = float(values[fsr_index])
        if not np.isfinite(value):
            value = 0.0
        if value == 0.0:
            # Fast path: nothing to lift.
            continue
        current = field[mask]
        field[mask] = np.maximum(current, value)

    if blur_sigma and blur_sigma > 0.0:
        # BORDER_REPLICATE approximates the previous "edge" padding behavior.
        field = cv2.GaussianBlur(
            field,
            ksize=(0, 0),
            sigmaX=float(blur_sigma),
            sigmaY=float(blur_sigma),
            borderType=cv2.BORDER_REPLICATE,
        )

    return field


def _prepare_renderer(payload: dict[str, Any]) -> _PreparedBoundaryRenderer:
    cache_key = id(payload)
    cached = _RENDERER_CACHE.get(cache_key)
    if cached is not None:
        return cached

    width = int(payload["canvas"]["width"])
    height = int(payload["canvas"]["height"])
    spline = dict(payload["spline"])

    spline_regions = [
        (int(r["id"]), r) for r in payload["regions"] if r.get("role") == "sensor"
    ]
    if not spline_regions:
        raise ValueError("render_payload has no sensor regions")

    # Build masks and centroids for FSR indices [0..15].
    sensor_masks: list[np.ndarray | None] = [None] * 16
    sensor_centroids: list[tuple[int, float, float] | None] = [None] * 16

    for region_id, region in spline_regions:
        fsr_index = region_id - 1
        if not (0 <= fsr_index < 16):
            continue

        curve = _sample_region_polygon(region=region, spline=spline)
        polygon = curve.astype(np.int32)
        contour = polygon.reshape((-1, 1, 2)).astype(np.int32)

        mask_u8 = np.zeros((height, width), dtype=np.uint8)
        cv2.fillPoly(mask_u8, [contour], 1)
        sensor_masks[fsr_index] = mask_u8.astype(bool)

        m = cv2.moments(contour)
        if m["m00"] != 0.0:
            cx = float(m["m10"] / m["m00"])
            cy = float(m["m01"] / m["m00"])
        else:
            cx = float(np.mean(curve[:, 0]))
            cy = float(np.mean(curve[:, 1]))
        sensor_centroids[fsr_index] = (fsr_index, cx, cy)

    missing = [str(i) for i, item in enumerate(sensor_masks) if item is None]
    if missing:
        raise ValueError(f"Missing sensor regions for FSR indices: {', '.join(missing)}")

    finalized_masks = [m for m in sensor_masks if m is not None]
    finalized_centroids = [c for c in sensor_centroids if c is not None]
    renderer = _PreparedBoundaryRenderer(
        width=width,
        height=height,
        spline=spline,
        sensor_masks=finalized_masks,
        sensor_centroids=finalized_centroids,  # already length 16
    )
    _RENDERER_CACHE[cache_key] = renderer
    return renderer
