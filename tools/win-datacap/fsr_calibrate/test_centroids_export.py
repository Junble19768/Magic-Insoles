"""Validate exported C centroids against insoles-boundary source."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

TOOLS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS_ROOT.parents[1]
INSOLES_BOUNDARY_SRC = REPO_ROOT / "tools" / "insoles-boundary" / "src"
PAYLOAD_PATH = REPO_ROOT / "tools" / "insoles-boundary" / "reports" / "render_payload.json"
CENTROIDS_HEADER = TOOLS_ROOT / "generated" / "insole_sensor_centroids.h"
BOUNDARY_ASSETS = REPO_ROOT / "frontend" / "public" / "data" / "boundary_assets.json"

_FLOAT_RE = re.compile(r"\{\s*([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)f,\s*([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)f\s*\}")


def _load_payload_centroids() -> list[tuple[int, float, float]]:
    if str(INSOLES_BOUNDARY_SRC) not in sys.path:
        sys.path.insert(0, str(INSOLES_BOUNDARY_SRC))

    from insoles.render_payload import load_render_payload, region_label_centroids  # noqa: WPS433

    payload = load_render_payload(PAYLOAD_PATH)
    return region_label_centroids(payload)


def _parse_centroid_table(header_text: str, table_name: str) -> list[tuple[float, float]]:
    pattern = re.compile(
        rf"static const insole_centroid_t {re.escape(table_name)}\[INSOLE_SENSOR_COUNT\] = \{{(.*?)\}};",
        re.DOTALL,
    )
    match = pattern.search(header_text)
    if match is None:
        raise ValueError(f"Table {table_name} not found in header")

    entries = _FLOAT_RE.findall(match.group(1))
    if len(entries) != 16:
        raise ValueError(f"Expected 16 entries in {table_name}, got {len(entries)}")
    return [(float(x), float(y)) for x, y in entries]


def test_generated_header_matches_payload() -> None:
    assert CENTROIDS_HEADER.is_file(), f"Missing {CENTROIDS_HEADER}; run export_boundary_assets.py"

    payload_centroids = _load_payload_centroids()
    header_text = CENTROIDS_HEADER.read_text(encoding="utf-8")
    right = _parse_centroid_table(header_text, "INSOLE_CENTROID_RIGHT")
    left = _parse_centroid_table(header_text, "INSOLE_CENTROID_LEFT")

    width_match = re.search(r"#define INSOLE_CANVAS_WIDTH\s+(\d+)", header_text)
    assert width_match is not None
    canvas_width = int(width_match.group(1))

    for index, ((fsr_index, cx, cy), (right_x, right_y)) in enumerate(
        zip(payload_centroids, right, strict=True)
    ):
        assert fsr_index == index
        assert right_x == pytest.approx(cx, abs=1e-4)
        assert right_y == pytest.approx(cy, abs=1e-4)

    for (fsr_index, cx, cy), (left_x, left_y) in zip(payload_centroids, left, strict=True):
        assert left_x == pytest.approx(canvas_width - 1 - cx, abs=1e-4)
        assert left_y == pytest.approx(cy, abs=1e-4)


def test_header_matches_boundary_assets_json() -> None:
    import json

    assert BOUNDARY_ASSETS.is_file()
    assets = json.loads(BOUNDARY_ASSETS.read_text(encoding="utf-8"))
    header_text = CENTROIDS_HEADER.read_text(encoding="utf-8")
    right = _parse_centroid_table(header_text, "INSOLE_CENTROID_RIGHT")

    centroids = sorted(assets["centroids"], key=lambda item: int(item["fsrIndex"]))
    for item, (right_x, right_y) in zip(centroids, right, strict=True):
        assert right_x == pytest.approx(float(item["cx"]), abs=1e-4)
        assert right_y == pytest.approx(float(item["cy"]), abs=1e-4)
