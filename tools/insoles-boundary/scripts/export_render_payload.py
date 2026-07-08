#!/usr/bin/env python3
"""Export a compact portable JSON payload for rendering insole regions."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from insoles.render_payload import (  # noqa: E402
    build_render_payload,
    load_models,
    write_render_payload,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export compact render payload for web/embedded consumers.",
    )
    parser.add_argument(
        "--contour-dir",
        type=Path,
        default=ROOT / "contours_scaled_adaptive",
        help="Directory with per-region contour JSON files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports" / "render_payload.json",
    )
    parser.add_argument(
        "--precision",
        type=int,
        default=4,
        help="Decimal places for control points and knot params.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Write indented JSON instead of compact single-line arrays.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    models = load_models(args.contour_dir)
    payload = build_render_payload(models, float_precision=args.precision)
    write_render_payload(payload, args.output, compact=not args.pretty)

    region_count = len(payload["regions"])
    canvas = payload["canvas"]
    print(
        f"Exported {region_count} regions to {args.output} "
        f"({canvas['width']}x{canvas['height']}, "
        f"pixel_scale_cm={canvas['pixel_scale_cm']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
