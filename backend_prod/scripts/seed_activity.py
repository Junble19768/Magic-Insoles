#!/usr/bin/env python3
"""Seed daily activity summaries (steps / active minutes / distance)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as `python scripts/seed_activity.py` from backend_prod/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from database import DailyActivity, SessionLocal, init_db

DEFAULT_ROWS: list[tuple[str, int, int, float]] = [
    ("2026-07-01", 8634, 51, 6.690),
    ("2026-07-02", 1029, 6, 0.740),
    ("2026-07-03", 2641, 12, 1.848),
    ("2026-07-04", 4301, 17, 3.062),
    ("2026-07-05", 9264, 57, 7.241),
    ("2026-07-06", 4722, 18, 3.447),
    ("2026-07-07", 3328, 14, 2.329),
    ("2026-07-08", 1258, 8, 0.855),
]


def upsert_rows(db: Session, rows: list[tuple[str, int, int, float]]) -> int:
    count = 0
    for date_str, steps, active_minutes, distance_km in rows:
        row = db.query(DailyActivity).filter(DailyActivity.date == date_str).first()
        if row is None:
            row = DailyActivity(
                date=date_str,
                steps=steps,
                active_minutes=active_minutes,
                distance_km=distance_km,
            )
            db.add(row)
        else:
            row.steps = steps
            row.active_minutes = active_minutes
            row.distance_km = distance_km
        count += 1
    db.commit()
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed daily activity summaries")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete all seeded daily_activity rows before insert",
    )
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        if args.clear:
            db.query(DailyActivity).delete()
            db.commit()
        written = upsert_rows(db, DEFAULT_ROWS)
        print(f"Seeded {written} daily activity rows")
        for date_str, steps, active_minutes, distance_km in DEFAULT_ROWS:
            print(
                f"  {date_str}: {steps} steps, "
                f"{active_minutes} min, {distance_km:.3f} km"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
