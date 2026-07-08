#!/usr/bin/env python3
"""Render a uniform B-spline contour JSON back to a mask PNG."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from insoles.contour import contour_to_mask  # noqa: E402
from insoles.schema import ContourModel  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Render a uniform B-spline contour JSON file to a mask PNG.",
    )
    parser.add_argument("contour_json", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--eval-n", type=int, default=None)
    return parser


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    model = ContourModel.from_json(args.contour_json)
    mask = contour_to_mask(model, eval_n=args.eval_n)

    output_path = args.output or Path(f"{model.id}_rendered.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), mask.astype("uint8") * 255)
    print(f"Rendered {model.id} to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
