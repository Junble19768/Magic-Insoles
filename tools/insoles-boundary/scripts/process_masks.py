#!/usr/bin/env python3
"""Batch-process mask PNGs into parametric B-spline contour JSON files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from insoles.contour import (  # noqa: E402
    BASE_MAX_CONTROL_POINTS,
    BASE_MIN_CONTROL_POINTS,
    DEFAULT_EVAL_N,
    SENSOR_MAX_CONTROL_POINTS,
    SENSOR_MIN_CONTROL_POINTS,
    compute_iou,
    control_point_limits,
    contour_to_mask,
    load_mask,
    mask_to_parametric_contour,
)
from insoles.schema import (  # noqa: E402
    DEFAULT_PIXEL_SCALE_CM,
    pixel_scale_for_dimension_scale,
)


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


def detect_duplicates(masks: dict[str, np.ndarray]) -> dict[str, str]:
    """Map duplicate mask ids to the first identical mask id."""
    duplicates: dict[str, str] = {}
    seen: dict[bytes, str] = {}
    for mask_id, mask in masks.items():
        digest = mask.tobytes()
        if digest in seen:
            duplicates[mask_id] = seen[digest]
        else:
            seen[digest] = mask_id
    return duplicates


def save_verification_image(
    original: np.ndarray,
    reconstructed: np.ndarray,
    output_path: Path,
) -> None:
    """Save a side-by-side original / reconstructed / diff image."""
    diff = np.logical_xor(original, reconstructed)
    height, width = original.shape
    canvas = np.zeros((height, width * 3), dtype=np.uint8)

    canvas[:, 0:width] = original.astype(np.uint8) * 255
    canvas[:, width : 2 * width] = reconstructed.astype(np.uint8) * 255
    canvas[:, 2 * width : 3 * width] = diff.astype(np.uint8) * 255

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), canvas)


def process_masks(
    mask_dir: Path,
    output_dir: Path,
    report_path: Path,
    verification_dir: Path | None,
    *,
    sensor_min_cp: int,
    sensor_max_cp: int,
    base_min_cp: int,
    base_max_cp: int,
    eval_n: int,
    fit_mode: str,
    optimization_metric: str,
    pixel_scale_cm: float,
) -> dict:
    """Process all masks and write JSON contours plus a quality report."""
    mask_paths = discover_masks(mask_dir)
    if not mask_paths:
        raise FileNotFoundError(f"No PNG masks found in {mask_dir}")

    loaded_masks = {path.stem: load_mask(path) for path in mask_paths}
    duplicates = detect_duplicates(loaded_masks)

    output_dir.mkdir(parents=True, exist_ok=True)
    if verification_dir is not None:
        verification_dir.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    for path in mask_paths:
        mask_id = path.stem
        mask = loaded_masks[mask_id]
        notes: dict[str, str] = {}
        if mask_id in duplicates:
            notes["duplicate_of"] = duplicates[mask_id]

        if mask_id == "base":
            min_cp, max_cp = base_min_cp, base_max_cp
        else:
            min_cp, max_cp = sensor_min_cp, sensor_max_cp

        model = mask_to_parametric_contour(
            mask,
            mask_id,
            min_control_points=min_cp,
            max_control_points=max_cp,
            eval_n=eval_n,
            notes=notes,
            fit_mode=fit_mode,
            optimization_metric=optimization_metric,
            pixel_scale_cm=pixel_scale_cm,
        )
        model.to_json(output_dir / f"{mask_id}.json")

        reconstructed = contour_to_mask(model)
        iou = compute_iou(mask, reconstructed)

        if verification_dir is not None:
            save_verification_image(
                mask,
                reconstructed,
                verification_dir / f"{mask_id}.png",
            )

        entry = {
            "id": mask_id,
            "source": str(path),
            "output": str(output_dir / f"{mask_id}.json"),
            "n_control_points": model.fit.n_control_points,
            "cp_min": min_cp,
            "cp_max": max_cp,
            "iou": round(iou, 6),
            "duplicate_of": notes.get("duplicate_of"),
        }
        if fit_mode == "adaptive":
            entry.update(
                {
                    "optimization_metric": model.fit.optimization_metric,
                    "metric_value": round(float(model.fit.metric_value), 6),
                    "boundary_mean_px": round(float(model.fit.metric_value), 6)
                    if model.fit.optimization_metric == "boundary_mean"
                    else None,
                    "hausdorff_px": round(float(model.fit.hausdorff_px), 6),
                }
            )
        entries.append(entry)

    ious = [entry["iou"] for entry in entries]
    control_points = [entry["n_control_points"] for entry in entries]
    summary: dict[str, float | int] = {
        "count": len(entries),
        "mean_iou": round(float(np.mean(ious)), 6),
        "min_iou": round(float(np.min(ious)), 6),
        "max_iou": round(float(np.max(ious)), 6),
        "mean_control_points": round(float(np.mean(control_points)), 2),
        "max_control_points": int(np.max(control_points)),
    }
    if fit_mode == "adaptive":
        boundary_values = [
            float(entry["metric_value"])
            for entry in entries
            if entry.get("optimization_metric") == "boundary_mean"
        ]
        hausdorff_values = [float(entry["hausdorff_px"]) for entry in entries]
        if boundary_values:
            summary["mean_boundary_px"] = round(float(np.mean(boundary_values)), 6)
            summary["max_boundary_px"] = round(float(np.max(boundary_values)), 6)
        summary["mean_hausdorff_px"] = round(float(np.mean(hausdorff_values)), 6)
        summary["max_hausdorff_px"] = round(float(np.max(hausdorff_values)), 6)

    contour_type = (
        "adaptive_bspline" if fit_mode == "adaptive" else "uniform_bspline"
    )
    report = {
        "mask_dir": str(mask_dir),
        "output_dir": str(output_dir),
        "contour_type": contour_type,
        "fit_mode": fit_mode,
        "optimization_metric": optimization_metric if fit_mode == "adaptive" else "iou",
        "pixel_scale_cm": pixel_scale_cm,
        "sensor_control_points": [sensor_min_cp, sensor_max_cp],
        "base_control_points": [base_min_cp, base_max_cp],
        "eval_n": eval_n,
        "summary": summary,
        "entries": entries,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")

    return report


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Convert binary mask PNGs to parametric B-spline contours.",
    )
    parser.add_argument("--mask-dir", type=Path, default=ROOT / "masks")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "contours")
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "reports" / "iou_summary.json",
    )
    parser.add_argument(
        "--verification-dir",
        type=Path,
        default=ROOT / "verification",
    )
    parser.add_argument("--no-verification", action="store_true")
    parser.add_argument(
        "--fit-mode",
        choices=("uniform", "adaptive"),
        default="adaptive",
    )
    parser.add_argument(
        "--metric",
        choices=("boundary_mean", "hausdorff"),
        default="boundary_mean",
        help="Optimization metric for adaptive fitting.",
    )
    parser.add_argument(
        "--sensor-min-cp",
        type=int,
        default=SENSOR_MIN_CONTROL_POINTS,
    )
    parser.add_argument(
        "--sensor-max-cp",
        type=int,
        default=SENSOR_MAX_CONTROL_POINTS,
    )
    parser.add_argument(
        "--base-min-cp",
        type=int,
        default=BASE_MIN_CONTROL_POINTS,
    )
    parser.add_argument(
        "--base-max-cp",
        type=int,
        default=BASE_MAX_CONTROL_POINTS,
    )
    parser.add_argument("--eval-n", type=int, default=DEFAULT_EVAL_N)
    parser.add_argument(
        "--pixel-scale-cm",
        type=float,
        default=None,
        help="cm/px for the input masks (overrides --dimension-scale when set).",
    )
    parser.add_argument(
        "--dimension-scale",
        type=float,
        default=None,
        help=(
            "Linear dimension scale relative to source masks "
            "(e.g. 0.1 when downscaled 10x); derives pixel_scale_cm."
        ),
    )
    parser.add_argument(
        "--source-pixel-scale-cm",
        type=float,
        default=DEFAULT_PIXEL_SCALE_CM,
        help="cm/px of the unscaled source masks for --dimension-scale.",
    )
    return parser


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    verification_dir = None if args.no_verification else args.verification_dir
    if args.pixel_scale_cm is not None:
        pixel_scale_cm = args.pixel_scale_cm
    elif args.dimension_scale is not None:
        pixel_scale_cm = pixel_scale_for_dimension_scale(
            args.source_pixel_scale_cm,
            args.dimension_scale,
        )
    else:
        pixel_scale_cm = DEFAULT_PIXEL_SCALE_CM

    report = process_masks(
        args.mask_dir,
        args.output_dir,
        args.report,
        verification_dir,
        sensor_min_cp=args.sensor_min_cp,
        sensor_max_cp=args.sensor_max_cp,
        base_min_cp=args.base_min_cp,
        base_max_cp=args.base_max_cp,
        eval_n=args.eval_n,
        fit_mode=args.fit_mode,
        optimization_metric=args.metric,
        pixel_scale_cm=pixel_scale_cm,
    )

    summary = report["summary"]
    if args.fit_mode == "adaptive":
        print(
            f"Processed {summary['count']} masks "
            f"(mean boundary={summary.get('mean_boundary_px', 'n/a')} px, "
            f"mean Hausdorff={summary.get('mean_hausdorff_px', 'n/a')} px, "
            f"mean IOU={summary['mean_iou']}, "
            f"max control points={summary['max_control_points']})"
        )
    else:
        print(
            f"Processed {summary['count']} masks "
            f"(mean IOU={summary['mean_iou']}, min IOU={summary['min_iou']}, "
            f"max control points={summary['max_control_points']})"
        )
    print(f"Report written to {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
