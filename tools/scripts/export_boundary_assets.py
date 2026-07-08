#!/usr/bin/env python3
"""Export insole boundary masks + centroids for frontend rendering."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
INSOLES_BOUNDARY_SRC = REPO_ROOT / "tools" / "insoles-boundary" / "src"
PAYLOAD_PATH = REPO_ROOT / "tools" / "insoles-boundary" / "reports" / "render_payload.json"
FRONTEND_DATA = REPO_ROOT / "frontend" / "public" / "data"
BACKEND_DATA = REPO_ROOT / "backend_prod" / "data"
OUTPUT_PATH = FRONTEND_DATA / "boundary_assets.json"
BACKEND_OUTPUT_PATH = BACKEND_DATA / "boundary_assets.json"


def _encode_rle(mask: np.ndarray) -> list[int]:
    """Run-length encode a boolean mask flattened row-major."""
    flat = mask.astype(np.uint8).ravel()
    if flat.size == 0:
        return []
    runs: list[int] = []
    current = int(flat[0])
    count = 1
    for value in flat[1:]:
        value = int(value)
        if value == current:
            count += 1
        else:
            runs.append(count)
            current = value
            count = 1
    runs.append(count)
    return runs


def export_boundary_assets() -> dict:
    if str(INSOLES_BOUNDARY_SRC) not in sys.path:
        sys.path.insert(0, str(INSOLES_BOUNDARY_SRC))

    from insoles.render_payload import (  # noqa: WPS433
        load_render_payload,
        region_label_centroids,
    )

    # Access internal renderer prep via render_sensor_field module cache path.
    from insoles import render_payload as rp  # noqa: WPS433

    payload = load_render_payload(PAYLOAD_PATH)
    renderer = rp._prepare_renderer(payload)  # noqa: SLF001

    centroids = [
        {"fsrIndex": fsr_index, "cx": cx, "cy": cy}
        for fsr_index, cx, cy in region_label_centroids(payload)
    ]

    masks = []
    for fsr_index, mask in enumerate(renderer.sensor_masks):
        masks.append(
            {
                "fsrIndex": fsr_index,
                "width": renderer.width,
                "height": renderer.height,
                "rle": _encode_rle(mask),
                "startsWith": 0,
            }
        )

    return {
        "schema": "insoles.boundary_assets/v1",
        "sourcePayload": "render_payload.json",
        "canvas": {
            "width": renderer.width,
            "height": renderer.height,
        },
        "centroids": centroids,
        "masks": masks,
    }


def main() -> None:
    FRONTEND_DATA.mkdir(parents=True, exist_ok=True)
    BACKEND_DATA.mkdir(parents=True, exist_ok=True)
    assets = export_boundary_assets()
    for output_path in (OUTPUT_PATH, BACKEND_OUTPUT_PATH):
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(assets, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
        print(f"Wrote {output_path}")

    payload_dest = FRONTEND_DATA / "render_payload.json"
    shutil.copy2(PAYLOAD_PATH, payload_dest)
    print(f"Copied {payload_dest}")


if __name__ == "__main__":
    main()
