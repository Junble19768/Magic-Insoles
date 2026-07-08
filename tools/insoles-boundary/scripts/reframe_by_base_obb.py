#!/usr/bin/env python3
"""Re-frame masks and contours with an expanded base-aligned OBB."""

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
from insoles.obb_transform import build_obb_frame, transform_points  # noqa: E402
from insoles.schema import ContourModel  # noqa: E402

DEFAULT_AXIS_START = (1883.0, 609.0)
DEFAULT_AXIS_END = (1763.0, 3643.0)
DEFAULT_MARGIN_CM = 1.0


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


def parse_point(text: str) -> tuple[float, float]:
    x_text, y_text = text.split(",")
    return float(x_text), float(y_text)


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transform masks/contours into an expanded base-aligned OBB frame.",
    )
    parser.add_argument("--mask-dir", type=Path, default=ROOT / "masks")
    parser.add_argument("--contour-dir", type=Path, default=ROOT / "contours")
    parser.add_argument("--out-mask-dir", type=Path, default=ROOT / "masks_obb")
    parser.add_argument("--out-contour-dir", type=Path, default=ROOT / "contours_obb")
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "reports" / "iou_summary_obb.json",
    )
    parser.add_argument(
        "--frame-meta",
        type=Path,
        default=ROOT / "reports" / "obb_frame.json",
    )
    parser.add_argument(
        "--verification-dir",
        type=Path,
        default=ROOT / "verification_obb",
    )
    parser.add_argument("--no-verification", action="store_true")
    parser.add_argument("--axis-start", type=str, default="1883,609")
    parser.add_argument("--axis-end", type=str, default="1763,3643")
    parser.add_argument("--margin-cm", type=float, default=DEFAULT_MARGIN_CM)
    args = parser.parse_args()

    base_path = args.contour_dir / "base.json"
    if not base_path.exists():
        raise FileNotFoundError(f"Missing base contour JSON: {base_path}")

    base_model = ContourModel.from_json(base_path)
    base_curve = base_model.sample_curve(eval_n=max(base_model.fit.eval_n, 4000))
    axis_start = parse_point(args.axis_start)
    axis_end = parse_point(args.axis_end)
    frame = build_obb_frame(
        base_curve,
        axis_start=axis_start,
        axis_end=axis_end,
        margin_cm=args.margin_cm,
        pixel_scale_cm=base_model.pixel_scale_cm,
    )

    args.out_mask_dir.mkdir(parents=True, exist_ok=True)
    args.out_contour_dir.mkdir(parents=True, exist_ok=True)
    verification_dir = None if args.no_verification else args.verification_dir
    if verification_dir is not None:
        verification_dir.mkdir(parents=True, exist_ok=True)

    output_size = frame.output_size
    mask_paths = discover_pngs(args.mask_dir)
    contour_paths = discover_jsons(args.contour_dir)
    if not mask_paths:
        raise FileNotFoundError(f"No mask PNG files found in {args.mask_dir}")
    if not contour_paths:
        raise FileNotFoundError(f"No contour JSON files found in {args.contour_dir}")

    transformed_masks: dict[str, np.ndarray] = {}
    for mask_path in mask_paths:
        mask = load_mask(mask_path)
        warped_u8 = cv2.warpAffine(
            mask.astype(np.uint8) * 255,
            frame.affine_old_to_new,
            output_size,
            flags=cv2.INTER_NEAREST,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )
        warped = warped_u8 > 127
        transformed_masks[mask_path.stem] = warped
        cv2.imwrite(str(args.out_mask_dir / mask_path.name), warped.astype(np.uint8) * 255)

    entries: list[dict] = []
    for contour_path in contour_paths:
        model = ContourModel.from_json(contour_path)
        control_points = model.control_points_array()
        transformed_cp = transform_points(control_points, frame.affine_old_to_new)
        model.control_points = [[float(x), float(y)] for x, y in transformed_cp]
        model.image_size = [output_size[0], output_size[1]]
        notes = dict(model.notes)
        notes["obb_axis_start"] = [axis_start[0], axis_start[1]]
        notes["obb_axis_end"] = [axis_end[0], axis_end[1]]
        notes["obb_margin_cm"] = args.margin_cm
        notes["obb_source"] = "base-axis-obb"
        model.notes = notes
        model.to_json(args.out_contour_dir / contour_path.name)

        if model.id not in transformed_masks:
            raise KeyError(f"Missing transformed mask for id '{model.id}'")
        mask = transformed_masks[model.id]
        reconstructed = contour_to_mask(model)
        iou = compute_iou(mask, reconstructed)
        if verification_dir is not None:
            save_verification_image(mask, reconstructed, verification_dir / f"{model.id}.png")

        entries.append(
            {
                "id": model.id,
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
        "pixel_scale_cm": base_model.pixel_scale_cm,
        "axis_start": [axis_start[0], axis_start[1]],
        "axis_end": [axis_end[0], axis_end[1]],
        "margin_cm": args.margin_cm,
        "output_size": [output_size[0], output_size[1]],
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

    frame_meta = {
        "axis_start": [axis_start[0], axis_start[1]],
        "axis_end": [axis_end[0], axis_end[1]],
        "axis_long": frame.axis_long.tolist(),
        "axis_short": frame.axis_short.tolist(),
        "min_long": frame.min_long,
        "max_long": frame.max_long,
        "min_short": frame.min_short,
        "max_short": frame.max_short,
        "margin_cm": frame.margin_cm,
        "pixel_scale_cm": frame.pixel_scale_cm,
        "output_size": [output_size[0], output_size[1]],
        "corners_old": frame.corners_old.tolist(),
        "affine_old_to_new": frame.affine_old_to_new.tolist(),
    }
    args.frame_meta.parent.mkdir(parents=True, exist_ok=True)
    with args.frame_meta.open("w", encoding="utf-8") as handle:
        json.dump(frame_meta, handle, indent=2)
        handle.write("\n")

    print(
        f"Reframed {len(entries)} items to {output_size[0]}x{output_size[1]} "
        f"(mean IOU={report['summary']['mean_iou']}, min IOU={report['summary']['min_iou']})"
    )
    print(f"Frame metadata written to {args.frame_meta}")
    print(f"Report written to {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
