"""Activity summary endpoints."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import verify_api_key
from database import get_db
from services.feature import compute_daily_features

router = APIRouter(prefix="/api/activity", tags=["activity"])


def _steps_for_date(date_str: str, db: Session) -> int:
    features = compute_daily_features(date_str, db)
    return features.step_count


@router.get("/today")
def get_activity_today(
    _: None = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    today = date.today().isoformat()
    features = compute_daily_features(today, db)
    steps = features.step_count
    return {
        "date": today,
        "steps": steps,
        "activeMinutes": features.walk_min,
        "distanceKm": round(steps * 0.0006, 2),
    }


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
            {"date": d.isoformat(), "steps": _steps_for_date(d.isoformat(), db)}
        )
    return {"days": day_list}
