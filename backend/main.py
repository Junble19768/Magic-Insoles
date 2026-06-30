"""FastAPI test stub for frontend integration."""

from __future__ import annotations

import math
import random
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

API_KEY = "dev-magic-insoles-key"

app = FastAPI(title="magic-insoles test stub", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IngestFrame(BaseModel):
    timestamp: float
    pressures: list[int] = Field(min_length=32, max_length=32)
    gait_state: int
    ml_class: int
    ml_conf: float
    step_count: int


class IngestRequest(BaseModel):
    frames: list[IngestFrame]


def verify_api_key(x_api_key: str | None) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def build_report(target_date: date) -> dict[str, Any]:
    generated_at = int(datetime.combine(target_date, datetime.min.time()).timestamp())
    return {
        "date": target_date.isoformat(),
        "report_text": (
            f"{target_date.isoformat()} 宝贝今天活动了 42 分钟，步态整体平稳。"
            "建议继续保持户外步行，注意走路时脚尖朝前。"
            "今天表现很棒，继续加油！"
        ),
        "step_count": 3200 - (date.today() - target_date).days * 120,
        "gait_summary": "步态整体正常",
        "generated_at": generated_at,
    }


@app.get("/api/report/today")
def get_today_report(x_api_key: str | None = Header(default=None)) -> dict[str, Any]:
    verify_api_key(x_api_key)
    return build_report(date.today())


@app.get("/api/report/history")
def get_report_history(
    days: int = 7,
    x_api_key: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_api_key(x_api_key)
    safe_days = max(1, min(days, 30))
    reports = [
        build_report(date.today() - timedelta(days=offset))
        for offset in range(safe_days)
    ]
    return {"reports": reports}


@app.post("/api/ingest")
def ingest_frames(
    payload: IngestRequest,
    x_api_key: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_api_key(x_api_key)
    print(f"[ingest] received {len(payload.frames)} frames")
    return {"received": len(payload.frames), "status": "ok"}


# ── Activity ──


@app.get("/api/activity/today")
def get_activity_today(x_api_key: str | None = Header(default=None)) -> dict[str, Any]:
    verify_api_key(x_api_key)
    steps = random.randint(5000, 12000)
    return {
        "date": date.today().isoformat(),
        "steps": steps,
        "activeMinutes": random.randint(25, 70),
        "distanceKm": round(steps * 0.0006, 2),
    }


@app.get("/api/activity/history")
def get_activity_history(
    days: int = 7,
    x_api_key: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_api_key(x_api_key)
    safe_days = max(1, min(days, 90))
    day_list = []
    for offset in range(safe_days):
        d = date.today() - timedelta(days=safe_days - 1 - offset)
        is_weekend = d.weekday() >= 5
        base = random.randint(3000, 7000) if is_weekend else random.randint(6000, 13000)
        day_list.append({"date": d.isoformat(), "steps": base})
    return {"days": day_list}


# ── Gait ──


def _make_cop_points(num: int, in_toe: bool) -> list[dict[str, float]]:
    points = []
    for i in range(num):
        t = i / num
        if in_toe:
            x = 0.08 + math.sin(t * 3.5) * 0.12 + random.gauss(0, 0.025)
        else:
            x = -0.02 + math.sin(t * 2.8) * 0.06 + random.gauss(0, 0.02)
        y = -0.75 + t * 1.5 + random.gauss(0, 0.03)
        points.append({"x": round(x, 4), "y": round(y, 4), "pressure": random.randint(1400, 2400)})
    return points


def _make_static_pressures(in_toe: bool) -> list[int]:
    base = [180, 120, 40, 5, 200, 160, 80, 10, 220, 190, 60, 15, 100, 70, 30, 5]
    if in_toe:
        return [max(0, min(255, round(v * (0.72 if i % 4 < 2 else 1.35) + random.gauss(0, 10)))) for i, v in enumerate(base)]
    return [max(0, min(255, round(v + random.gauss(0, 15)))) for v in base]


@app.get("/api/gait/summary")
def get_gait_summary(
    date_param: str = Query(default=None, alias="date"),
    x_api_key: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_api_key(x_api_key)
    target = date.today().isoformat() if date_param is None else date_param
    return {
        "date": target,
        "leftFoot": {
            "pressures": _make_static_pressures(False),
            "copPoints": _make_cop_points(100, False),
            "classification": "normal",
            "confidence": 0.94,
        },
        "rightFoot": {
            "pressures": _make_static_pressures(True),
            "copPoints": _make_cop_points(100, True),
            "classification": "in_toe",
            "confidence": 0.78,
        },
    }


# ── GPS ──


@app.get("/api/gps/routes")
def get_gps_routes(
    date_param: str = Query(default=None, alias="date"),
    x_api_key: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_api_key(x_api_key)
    target = date.today().isoformat() if date_param is None else date_param
    center_lat = 40.02
    center_lng = 116.39
    count = 55
    now = datetime.now().timestamp()
    points = []
    for i in range(count):
        angle = (i / count) * math.pi * 2
        lat = center_lat + math.sin(angle) * 0.012 + random.gauss(0, 0.0003)
        lng = center_lng + math.cos(angle) * 0.018 + random.gauss(0, 0.0004)
        points.append({
            "timestamp": now - (count - i) * 45,
            "lat": round(lat, 6),
            "lng": round(lng, 6),
        })
    return {
        "date": target,
        "points": points,
        "totalDistanceKm": 5.1,
        "durationMinutes": 42,
    }


# ── Report (period) ──

_PERIOD_TEXTS = {
    "today": "宝贝今天活动了 42 分钟，步态整体平稳。建议继续保持户外步行，注意走路时脚尖朝前。今天表现很棒，继续加油！",
    "week": "过去一周，宝贝累计步行 21,430 步（日均 3,061 步），整体步态正常，偶有轻度内八（占比约 8%）。周末户外活动时间偏少，建议周末安排 30 分钟以上户外散步，有助于足弓发育和骨骼健康。",
    "month": "本月宝贝共完成 96,500 步，日均 3,117 步。步态评估整体良好，内八倾向从上月的 12% 下降至 8%，改善明显。建议继续保持当前运动习惯，注意书包重量和坐姿，帮助维持健康力线发育。",
}


@app.get("/api/report")
def get_report_by_period(
    period: str = Query(default="today"),
    x_api_key: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_api_key(x_api_key)
    if period not in ("today", "week", "month"):
        raise HTTPException(status_code=400, detail="period must be today, week, or month")
    today = date.today()
    if period == "week":
        start = today - timedelta(days=7)
    elif period == "month":
        start = today.replace(day=1)
    else:
        start = today
    return {
        "period": period,
        "dateRange": {"start": start.isoformat(), "end": today.isoformat()},
        "reportText": _PERIOD_TEXTS.get(period, _PERIOD_TEXTS["today"]),
        "stepCount": 3200 if period == "today" else (21430 if period == "week" else 96500),
        "gaitSummary": "步态整体正常",
        "generatedAt": int(datetime.combine(today, datetime.min.time()).timestamp()),
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
