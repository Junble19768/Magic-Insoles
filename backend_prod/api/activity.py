"""Activity summary endpoints."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import verify_api_key
from database import DailyActivity, get_db
from services.feature import compute_daily_features

router = APIRouter(prefix="/api/activity", tags=["activity"])


def _activity_for_date(date_str: str, db: Session) -> dict[str, Any]:
    override = (
        db.query(DailyActivity).filter(DailyActivity.date == date_str).first()
    )
    if override is not None:
        return {
            "date": date_str,
            "steps": override.steps,
            "activeMinutes": override.active_minutes,
            "distanceKm": override.distance_km,
        }

    features = compute_daily_features(date_str, db)
    steps = features.step_count
    return {
        "date": date_str,
        "steps": steps,
        "activeMinutes": features.walk_min,
        "distanceKm": round(steps * 0.0006, 2),
    }


@router.get("/today")
def get_activity_today(
    _: None = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return _activity_for_date(date.today().isoformat(), db)


@router.get("/history")
def get_activity_history(
    days: int = 7,
    _: None = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    safe_days = max(1, min(days, 90))
    day_list: list[dict[str, Any]] = []
    for offset in range(safe_days):
        d = date.today() - timedelta(days=safe_days - 1 - offset)
        day_list.append(
            {
                "date": d.isoformat(),
                "steps": _activity_for_date(d.isoformat(), db)["steps"],
            }
        )
    return {"days": day_list}
