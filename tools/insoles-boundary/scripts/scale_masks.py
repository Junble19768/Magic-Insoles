#!/usr/bin/env python3
"""Scale binary mask PNGs by a fixed ratio while preserving binary values."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from insoles.contour import load_mask  # noqa: E402
from insoles.schema import pixel_scale_for_dimension_scale  # noqa: E402


def _mask_sort_key(path: Path) -> tuple[int, str]:
    stem = path.stem
    if stem == "base":
        return (0, stem)
    if stem.isdigit():
        return (1, f"{int(stem):04d}")
    return (2, stem)


def discover_masks(mask_dir: Path) -> list[Path]:
    """Return mask PNG paths sorted with base first, then numeric ids."""
    return sorted(mask_dir.glob("*.png"), key=_mask_sort_key)


def scale_binary_mask(mask: np.ndarray, scale: float) -> np.ndarray:
    """Scale a boolean mask with nearest-neighbor interpolation and re-binarize."""
    if scale <= 0:
        raise ValueError(f"scale must be positive, got {scale}")

    binary = mask.astype(np.uint8) * 255
    height, width = binary.shape[:2]
    new_width = max(1, int(round(width * scale)))
    new_height = max(1, int(round(height * scale)))

    resized = cv2.resize(
        binary,
        (new_width, new_height),
        interpolation=cv2.INTER_NEAREST,
    )
    _, scaled = cv2.threshold(resized, 127, 255, cv2.THRESH_BINARY)
    return scaled


def process_masks(
    mask_dir: Path,
    output_dir: Path,
    scale: float,
    report_path: Path | None,
    *,
    source_pixel_scale_cm: float,
) -> dict:
    """Scale all masks in mask_dir and write binary PNGs to output_dir."""
    mask_paths = discover_masks(mask_dir)
    if not mask_paths:
        raise FileNotFoundError(f"No PNG masks found in {mask_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []

    for path in mask_paths:
        mask = load_mask(path)
        scaled = scale_binary_mask(mask, scale)
        output_path = output_dir / path.name
        cv2.imwrite(str(output_path), scaled)

        unique_values = sorted(int(value) for value in np.unique(scaled))
        entries.append(
            {
                "id": path.stem,
                "source": str(path),
                "output": str(output_path),
                "source_size": [int(mask.shape[1]), int(mask.shape[0])],
                "output_size": [int(scaled.shape[1]), int(scaled.shape[0])],
                "unique_values": unique_values,
            }
        )

    report = {
        "mask_dir": str(mask_dir),
        "output_dir": str(output_dir),
        "scale": scale,
        "source_pixel_scale_cm": source_pixel_scale_cm,
        "pixel_scale_cm": pixel_scale_for_dimension_scale(
            source_pixel_scale_cm,
            scale,
        ),
        "interpolation": "INTER_NEAREST",
        "summary": {"count": len(entries)},
        "entries": entries,
    }

    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")

    return report


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Scale binary mask PNGs by a fixed ratio.",
    )
    parser.add_argument("--mask-dir", type=Path, default=ROOT / "masks")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "masks_scaled")
    parser.add_argument(
        "--scale",
        type=float,
        required=True,
        help="Uniform scale factor applied to width and height (e.g. 0.1 for 10x downscale).",
    )
    parser.add_argument(
        "--source-pixel-scale-cm",
        type=float,
        default=0.00855,
        help="cm/px of the source masks before scaling.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "reports" / "scale_masks.json",
    )
    parser.add_argument("--no-report", action="store_true")
    return parser


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    report = process_masks(
        args.mask_dir,
        args.output_dir,
        args.scale,
        None if args.no_report else args.report,
        source_pixel_scale_cm=args.source_pixel_scale_cm,
    )

    sample = report["entries"][0]
    print(
        f"Scaled {report['summary']['count']} masks by {args.scale} "
        f"({sample['source_size']} -> {sample['output_size']})"
    )
    print(f"Output written to {args.output_dir}")
    if not args.no_report:
        print(f"Report written to {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
