#!/usr/bin/env python3
"""Reorient masks and contours to bottom-left row/col coordinates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from insoles.contour import compute_iou, contour_to_mask, load_mask  # noqa: E402
from insoles.coord_transform import (  # noqa: E402
    transform_mask_xy_tl_to_row_col_bl,
    transform_points_row_col_bl_to_xy_tl,
    transform_points_xy_tl_to_row_col_bl,
)
from insoles.schema import ContourModel  # noqa: E402


def _mask_sort_key(path: Path) -> tuple[int, str]:
    stem = path.stem
    if stem == "base":
        return (0, stem)
    if stem.isdigit():
        return (1, f"{int(stem):04d}")
    return (2, stem)


def discover_pngs(folder: Path) -> list[Path]:
    return sorted(folder.glob("*.png"), key=_mask_sort_key)


def discover_jsons(folder: Path) -> list[Path]:
    return sorted(folder.glob("*.json"), key=_mask_sort_key)


def save_verification_image(
    original: np.ndarray,
    reconstructed: np.ndarray,
    output_path: Path,
) -> None:
    """Save side-by-side original / reconstructed / diff image."""
    diff = np.logical_xor(original, reconstructed)
    height, width = original.shape
    canvas = np.zeros((height, width * 3), dtype=np.uint8)

    canvas[:, 0:width] = original.astype(np.uint8) * 255
    canvas[:, width : 2 * width] = reconstructed.astype(np.uint8) * 255
    canvas[:, 2 * width : 3 * width] = diff.astype(np.uint8) * 255

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), canvas)


def render_bottom_left_contour(model: ContourModel) -> np.ndarray:
    """Render a bottom-left contour model back to a row/col boolean mask."""
    width, height = model.image_size
    xy_points = transform_points_row_col_bl_to_xy_tl(
        model.control_points_array(),
        (width, height),
    )
    xy_mask = contour_to_mask(
        ContourModel(
            id=model.id,
            contour_type=model.contour_type,
            image_size=model.image_size,
            pixel_scale_cm=model.pixel_scale_cm,
            fit=model.fit,
            control_points=[[float(x), float(y)] for x, y in xy_points],
            notes=model.notes,
        )
    )
    return transform_mask_xy_tl_to_row_col_bl(xy_mask)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Convert top-left (x, y) masks/contours to bottom-left "
            "(row, col) coordinates."
        ),
    )
    parser.add_argument("--mask-dir", type=Path, default=ROOT / "masks_obb")
    parser.add_argument("--contour-dir", type=Path, default=ROOT / "contours_obb")
    parser.add_argument("--out-mask-dir", type=Path, default=ROOT / "masks_bl")
    parser.add_argument("--out-contour-dir", type=Path, default=ROOT / "contours_bl")
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "reports" / "iou_summary_bl.json",
    )
    parser.add_argument(
        "--verification-dir",
        type=Path,
        default=ROOT / "verification_bl",
    )
    parser.add_argument("--no-verification", action="store_true")
    args = parser.parse_args()

    mask_paths = discover_pngs(args.mask_dir)
    contour_paths = discover_jsons(args.contour_dir)
    if not mask_paths:
        raise FileNotFoundError(f"No mask PNG files found in {args.mask_dir}")
    if not contour_paths:
        raise FileNotFoundError(f"No contour JSON files found in {args.contour_dir}")

    args.out_mask_dir.mkdir(parents=True, exist_ok=True)
    args.out_contour_dir.mkdir(parents=True, exist_ok=True)
    verification_dir = None if args.no_verification else args.verification_dir
    if verification_dir is not None:
        verification_dir.mkdir(parents=True, exist_ok=True)

    transformed_masks: dict[str, np.ndarray] = {}
    for mask_path in mask_paths:
        mask = load_mask(mask_path)
        height, width = mask.shape
        transformed = transform_mask_xy_tl_to_row_col_bl(mask)
        transformed_masks[mask_path.stem] = transformed
        cv2.imwrite(
            str(args.out_mask_dir / mask_path.name),
            transformed.astype(np.uint8) * 255,
        )

    entries: list[dict] = []
    for contour_path in contour_paths:
        model = ContourModel.from_json(contour_path)
        width, height = model.image_size
        row_col_points = transform_points_xy_tl_to_row_col_bl(
            model.control_points_array(),
            (width, height),
        )
        model.control_points = [[float(row), float(col)] for row, col in row_col_points]
        notes = dict(model.notes)
        notes["coordinate_system"] = {
            "origin": "bottom_left",
            "axes": {"row": "left", "col": "up"},
            "point_order": ["row", "col"],
            "equivalent_ops": ["swap_xy", "horizontal_flip"],
        }
        model.notes = notes
        model.to_json(args.out_contour_dir / contour_path.name)

        if model.id not in transformed_masks:
            raise KeyError(f"Missing transformed mask for id '{model.id}'")
        mask = transformed_masks[model.id]
        reconstructed = render_bottom_left_contour(model)
        iou = compute_iou(mask, reconstructed)
        if verification_dir is not None:
            save_verification_image(mask, reconstructed, verification_dir / f"{model.id}.png")

        entries.append(
            {
                "id": model.id,
                "image_size": model.image_size,
                "n_control_points": model.fit.n_control_points,
                "iou": round(float(iou), 6),
                "output_mask": str(args.out_mask_dir / f"{model.id}.png"),
                "output_contour": str(args.out_contour_dir / f"{model.id}.json"),
            }
        )

    ious = [entry["iou"] for entry in entries]
    report = {
        "source_mask_dir": str(args.mask_dir),
        "source_contour_dir": str(args.contour_dir),
        "output_mask_dir": str(args.out_mask_dir),
        "output_contour_dir": str(args.out_contour_dir),
        "coordinate_system": {
            "origin": "bottom_left",
            "axes": {"row": "left", "col": "up"},
            "point_order": ["row", "col"],
        },
        "summary": {
            "count": len(entries),
            "mean_iou": round(float(np.mean(ious)), 6),
            "min_iou": round(float(np.min(ious)), 6),
            "max_iou": round(float(np.max(ious)), 6),
        },
        "entries": entries,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")

    print(
        f"Reoriented {len(entries)} items to bottom-left row/col "
        f"(mean IOU={report['summary']['mean_iou']}, "
        f"min IOU={report['summary']['min_iou']})"
    )
    print(f"Report written to {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
