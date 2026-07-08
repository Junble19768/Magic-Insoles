#!/usr/bin/env python3
"""Fix scaled contour pixel_scale_cm and write a compact pipeline record."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from insoles.schema import (  # noqa: E402
    DEFAULT_PIXEL_SCALE_CM,
    ContourModel,
    pixel_scale_for_dimension_scale,
)


def _mask_sort_key(path: Path) -> tuple[int, str]:
    stem = path.stem
    if stem == "base":
        return (0, stem)
    if stem.isdigit():
        return (1, f"{int(stem):04d}")
    return (2, stem)


def discover_jsons(folder: Path) -> list[Path]:
    return sorted(folder.glob("*.json"), key=_mask_sort_key)


def infer_dimension_scale(source_mask: Path, scaled_mask: Path) -> float:
    """Infer linear dimension scale from a source/scaled mask pair."""
    source = cv2.imread(str(source_mask), cv2.IMREAD_GRAYSCALE)
    scaled = cv2.imread(str(scaled_mask), cv2.IMREAD_GRAYSCALE)
    if source is None or scaled is None:
        raise FileNotFoundError("Failed to read masks for scale inference")
    return float(scaled.shape[1]) / float(source.shape[1])


def load_report(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def index_entries(report: dict) -> dict[str, dict]:
    return {entry["id"]: entry for entry in report.get("entries", [])}


def fix_pixel_scale(contour_dir: Path, pixel_scale_cm: float) -> int:
    """Update pixel_scale_cm in all contour JSON files."""
    updated = 0
    for path in discover_jsons(contour_dir):
        model = ContourModel.from_json(path)
        if model.pixel_scale_cm == pixel_scale_cm:
            continue
        model.pixel_scale_cm = pixel_scale_cm
        model.to_json(path)
        updated += 1
    return updated


def build_record(
    *,
    dimension_scale: float,
    pixel_scale_cm: float,
    source_pixel_scale_cm: float,
    uniform_report: dict,
    adaptive_report: dict,
) -> dict:
    """Build a compact summary across scaled pipeline outputs."""
    uniform_by_id = index_entries(uniform_report)
    adaptive_by_id = index_entries(adaptive_report)
    mask_ids = sorted(
        set(uniform_by_id) | set(adaptive_by_id),
        key=lambda mask_id: _mask_sort_key(Path(mask_id))[0:2],
    )

    masks: list[dict] = []
    for mask_id in mask_ids:
        uniform = uniform_by_id.get(mask_id, {})
        adaptive = adaptive_by_id.get(mask_id, {})
        item: dict = {"id": mask_id}
        if uniform:
            item["uniform"] = {
                "cp": uniform.get("n_control_points"),
                "iou": uniform.get("iou"),
            }
        if adaptive:
            item["adaptive"] = {
                "cp": adaptive.get("n_control_points"),
                "iou": adaptive.get("iou"),
                "boundary_px": adaptive.get("metric_value"),
                "hausdorff_px": adaptive.get("hausdorff_px"),
            }
        duplicate_of = uniform.get("duplicate_of") or adaptive.get("duplicate_of")
        if duplicate_of:
            item["dup"] = duplicate_of
        masks.append(item)

    sample_uniform = uniform_report.get("entries", [{}])[0]
    sample_size = None
    if sample_uniform.get("source"):
        scaled_mask = Path(sample_uniform["source"])
        image = cv2.imread(str(scaled_mask), cv2.IMREAD_GRAYSCALE)
        if image is not None:
            sample_size = [int(image.shape[1]), int(image.shape[0])]

    return {
        "source": {
            "mask_dir": "masks",
            "pixel_scale_cm": source_pixel_scale_cm,
        },
        "scaled": {
            "mask_dir": "masks_scaled",
            "dimension_scale": round(dimension_scale, 6),
            "pixel_scale_cm": round(pixel_scale_cm, 6),
            "image_size": sample_size,
            "interpolation": "INTER_NEAREST",
        },
        "cp_budget": {
            "sensor": uniform_report.get("sensor_control_points", [10, 20]),
            "base": uniform_report.get("base_control_points", [10, 40]),
        },
        "outputs": {
            "uniform": {
                "dir": "contours_scaled",
                "type": "uniform_bspline",
                "metric": "iou",
                "summary": uniform_report.get("summary", {}),
            },
            "adaptive": {
                "dir": "contours_scaled_adaptive",
                "type": "adaptive_bspline",
                "metric": "boundary_mean",
                "summary": adaptive_report.get("summary", {}),
            },
        },
        "masks": masks,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fix scaled contour pixel_scale_cm and write compact record.",
    )
    parser.add_argument(
        "--dimension-scale",
        type=float,
        default=None,
        help="Linear scale of scaled masks relative to source (default: infer).",
    )
    parser.add_argument(
        "--source-pixel-scale-cm",
        type=float,
        default=DEFAULT_PIXEL_SCALE_CM,
    )
    parser.add_argument(
        "--uniform-report",
        type=Path,
        default=ROOT / "reports" / "iou_summary_scaled.json",
    )
    parser.add_argument(
        "--adaptive-report",
        type=Path,
        default=ROOT / "reports" / "boundary_summary_scaled.json",
    )
    parser.add_argument(
        "--contour-dirs",
        type=Path,
        nargs="+",
        default=[
            ROOT / "contours_scaled",
            ROOT / "contours_scaled_adaptive",
        ],
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports" / "scaled_record.json",
    )
    parser.add_argument(
        "--source-mask",
        type=Path,
        default=ROOT / "masks" / "base.png",
    )
    parser.add_argument(
        "--scaled-mask",
        type=Path,
        default=ROOT / "masks_scaled" / "base.png",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    dimension_scale = args.dimension_scale
    if dimension_scale is None:
        dimension_scale = infer_dimension_scale(args.source_mask, args.scaled_mask)

    pixel_scale_cm = pixel_scale_for_dimension_scale(
        args.source_pixel_scale_cm,
        dimension_scale,
    )
    pixel_scale_cm = round(pixel_scale_cm, 6)

    updated = 0
    for contour_dir in args.contour_dirs:
        updated += fix_pixel_scale(contour_dir, pixel_scale_cm)

    uniform_report = load_report(args.uniform_report)
    adaptive_report = load_report(args.adaptive_report)
    record = build_record(
        dimension_scale=dimension_scale,
        pixel_scale_cm=pixel_scale_cm,
        source_pixel_scale_cm=args.source_pixel_scale_cm,
        uniform_report=uniform_report,
        adaptive_report=adaptive_report,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    # Update reports with corrected pixel_scale_cm
    for report_path in (args.uniform_report, args.adaptive_report):
        report = load_report(report_path)
        report["pixel_scale_cm"] = round(pixel_scale_cm, 6)
        report["dimension_scale"] = round(dimension_scale, 6)
        report["source_pixel_scale_cm"] = args.source_pixel_scale_cm
        with report_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")

    print(
        f"pixel_scale_cm={pixel_scale_cm} (dimension_scale={dimension_scale:.6f}), "
        f"updated {updated} contour JSON files"
    )
    print(f"Record written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
