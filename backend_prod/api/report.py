"""Report query and generation endpoints."""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.deps import verify_api_key
from database import Report, get_db
from services.llm import generate_and_save_report, report_generated_at

router = APIRouter(prefix="/api/report", tags=["report"])


def _report_to_today_dict(row: Report) -> dict[str, Any]:
    summary = json.loads(row.summary_json) if row.summary_json else {}
    return {
        "date": row.date,
        "report_text": row.report_text,
        "step_count": summary.get("step_count", 0),
        "gait_summary": summary.get("gait_summary", "数据不足"),
        "generated_at": report_generated_at(row.date),
    }


def _report_to_history_item(row: Report) -> dict[str, Any]:
    summary = json.loads(row.summary_json) if row.summary_json else {}
    return {
        "date": row.date,
        "step_count": summary.get("step_count", 0),
        "gait_summary": summary.get("gait_summary", "数据不足"),
        "report_text": row.report_text,
    }


@router.get("/today")
def get_today_report(
    _: None = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    today = date.today().isoformat()
    row = db.query(Report).filter(Report.date == today).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Report not found for today")
    return _report_to_today_dict(row)


@router.get("/history")
def get_report_history(
    days: int = 7,
    _: None = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    safe_days = max(1, min(days, 30))
    reports: list[dict[str, Any]] = []
    for offset in range(safe_days):
        target = (date.today() - timedelta(days=offset)).isoformat()
        row = db.query(Report).filter(Report.date == target).first()
        if row is not None:
            reports.append(_report_to_history_item(row))
    return {"reports": reports}


@router.get("")
def get_report_by_period(
    period: str = Query(default="today"),
    _: None = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if period not in ("today", "week", "month"):
        raise HTTPException(
            status_code=400, detail="period must be today, week, or month"
        )
    today = date.today()
    if period == "week":
        start = today - timedelta(days=7)
    elif period == "month":
        start = today.replace(day=1)
    else:
        start = today

    row = db.query(Report).filter(Report.date == today.isoformat()).first()
    summary = json.loads(row.summary_json) if row and row.summary_json else {}
    report_text = row.report_text if row else "暂无报告，请先通过设备采集数据并生成报告。"
    step_count = summary.get("step_count", 0)
    gait_summary = summary.get("gait_summary", "数据不足")

    return {
        "period": period,
        "dateRange": {"start": start.isoformat(), "end": today.isoformat()},
        "reportText": report_text,
        "stepCount": step_count,
        "gaitSummary": gait_summary,
        "generatedAt": report_generated_at(today.isoformat()),
    }


@router.post("/generate")
def generate_report(
    _: None = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    today = date.today().isoformat()
    row = generate_and_save_report(today, db)
    return _report_to_today_dict(row)
