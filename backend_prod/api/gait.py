"""Gait analysis endpoint."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import verify_api_key
from database import ForceBatch, day_bounds, get_db
from services.feature import (
    average_foot_pressures,
    compute_cop_points,
    compute_daily_features,
)

router = APIRouter(prefix="/api/gait", tags=["gait"])


def _foot_analysis(
    batches: list[ForceBatch], foot_offset: int, classification: str, confidence: float
) -> dict[str, Any]:
    pressures = average_foot_pressures(batches, foot_offset)
    # Scale uint16 to 0-255 for frontend compatibility
    max_val = max(pressures) if pressures else 1
    scale = 255.0 / max(max_val, 1)
    scaled = [min(255, int(p * scale)) for p in pressures]
    return {
        "pressures": scaled,
        "copPoints": compute_cop_points(batches, foot_offset),
        "classification": classification,
        "confidence": confidence,
    }


@router.get("/summary")
def get_gait_summary(
    date_param: str | None = Query(default=None, alias="date"),
    _: None = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    target = date.today().isoformat() if date_param is None else date_param
    start_ts, end_ts = day_bounds(target)
    batches = (
        db.query(ForceBatch)
        .filter(
            ForceBatch.receive_time >= start_ts,
            ForceBatch.receive_time <= end_ts,
        )
        .order_by(ForceBatch.receive_time)
        .all()
    )
    features = compute_daily_features(target, db)
    gait = features.gait_summary
    if "内" in gait or features.abnormal_pct > 10:
        right_class = "in_toe"
        right_conf = 0.78
        left_class = "normal"
        left_conf = 0.94
    else:
        right_class = "normal"
        right_conf = 0.94
        left_class = "normal"
        left_conf = 0.94

    return {
        "date": target,
        "leftFoot": _foot_analysis(batches, 0, left_class, left_conf),
        "rightFoot": _foot_analysis(batches, 16, right_class, right_conf),
    }
