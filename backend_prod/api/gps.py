"""GPS routes endpoint."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import verify_api_key
from database import GpsPoint, day_bounds, get_db
from services.feature import haversine_km

router = APIRouter(prefix="/api/gps", tags=["gps"])


@router.get("/routes")
def get_gps_routes(
    date_param: str | None = Query(default=None, alias="date"),
    _: None = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    target = date.today().isoformat() if date_param is None else date_param
    start_ts, end_ts = day_bounds(target)
    rows = (
        db.query(GpsPoint)
        .filter(
            GpsPoint.receive_time >= start_ts,
            GpsPoint.receive_time <= end_ts,
        )
        .order_by(GpsPoint.timestamp)
        .all()
    )

    points: list[dict[str, Any]] = []
    total_km = 0.0
    for index, row in enumerate(rows):
        ts = row.timestamp / 1000.0 if row.timestamp > 1e12 else float(row.timestamp)
        points.append(
            {
                "timestamp": ts,
                "lat": round(row.latitude, 6),
                "lng": round(row.longitude, 6),
            }
        )
        if index > 0:
            prev = rows[index - 1]
            total_km += haversine_km(
                prev.latitude, prev.longitude, row.latitude, row.longitude
            )

    duration_min = 0
    if len(rows) >= 2:
        t0 = rows[0].receive_time
        t1 = rows[-1].receive_time
        duration_min = max(1, int(round((t1 - t0) / 60)))

    return {
        "date": target,
        "points": points,
        "totalDistanceKm": round(total_km, 2),
        "durationMinutes": duration_min,
    }
