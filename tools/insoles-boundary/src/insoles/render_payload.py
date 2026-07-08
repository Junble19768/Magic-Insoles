"""Compact portable payload for rendering insole regions elsewhere."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from insoles.schema import ContourModel

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
