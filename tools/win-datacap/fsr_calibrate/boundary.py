from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

TOOLS_ROOT = Path(__file__).resolve().parents[2]
INSOLES_BOUNDARY_SRC = TOOLS_ROOT / "insoles-boundary" / "src"

if str(INSOLES_BOUNDARY_SRC) not in sys.path:
    sys.path.insert(0, str(INSOLES_BOUNDARY_SRC))

from .config import BOUNDARY_PAYLOAD_PATH  # noqa: E402

from insoles.render_payload import (  # noqa: E402
    load_render_payload,
    region_label_centroids,
    render_sensor_field,
)


DEFAULT_BOUNDARY_PAYLOAD = BOUNDARY_PAYLOAD_PATH


_PAYLOAD_CACHE: dict[Path, dict[str, Any]] = {}


def load_boundary_payload(payload_path: Path = DEFAULT_BOUNDARY_PAYLOAD) -> dict[str, Any]:
    """Load and cache insole geometry render payload for the boundary renderer."""
    payload_path = Path(payload_path)
    cached = _PAYLOAD_CACHE.get(payload_path)
    if cached is not None:
        return cached
    payload = load_render_payload(payload_path)
    _PAYLOAD_CACHE[payload_path] = payload
    return payload


def get_boundary_label_positions(
    *,
    payload_path: Path = DEFAULT_BOUNDARY_PAYLOAD,
) -> list[tuple[int, float, float]]:
    """Return ``[(fsr_index, cx, cy), ...]`` for sensor regions (top-left origin)."""
    payload = load_boundary_payload(payload_path)
    return region_label_centroids(payload)


def build_boundary_foot_heatmap(
    foot_values: np.ndarray,
    *,
    flip_horizontal: bool = False,
    transpose: bool = False,
    payload_path: Path = DEFAULT_BOUNDARY_PAYLOAD,
    blur_sigma: float = 0.0,
) -> np.ndarray:
    """Render a single foot scalar field using B-spline sensor region geometry."""
    payload = load_boundary_payload(payload_path)
    field = render_sensor_field(
        payload,
        foot_values,
        blur_sigma=float(blur_sigma),
    )
    if transpose:
        field = field.T
    if flip_horizontal:
        # Mirror in display X after transpose (plot x = row index of field.T).
        field = np.flip(field, axis=0)
    return field

