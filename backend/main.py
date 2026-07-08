"""FastAPI test stub for frontend integration."""

from __future__ import annotations

import json
import math
import random
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

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

FootSide = Literal["left", "right"]

_BOUNDARY_ASSET_CANDIDATES = (
    Path(__file__).resolve().parents[1] / "backend_prod" / "data" / "boundary_assets.json",
    Path(__file__).resolve().parent / "data" / "boundary_assets.json",
)


@lru_cache(maxsize=1)
def _load_boundary_assets() -> dict[str, Any]:
    for path in _BOUNDARY_ASSET_CANDIDATES:
        if path.is_file():
            with path.open(encoding="utf-8") as handle:
                return json.load(handle)
    raise FileNotFoundError("boundary_assets.json not found for fake gait mock")


@lru_cache(maxsize=1)
def _boundary_centroids() -> list[tuple[int, float, float]]:
    payload = _load_boundary_assets()
    return [
        (int(item["fsrIndex"]), float(item["cx"]), float(item["cy"]))
        for item in payload.get("centroids", [])
    ]


@lru_cache(maxsize=1)
def _canvas_width() -> int:
    return int(_load_boundary_assets()["canvas"]["width"])


def _cop_display_coords(cx: float, cy: float, side: FootSide) -> tuple[float, float]:
    """Map sensor-field centroids to 132x324 display overlay coordinates."""
    canvas_width = _canvas_width()
    if side == "left":
        return canvas_width - 1 - cx, cy
    return cx, cy


def _seed_for_foot(target_date: str, side: FootSide) -> None:
    seed = sum(ord(ch) for ch in f"{target_date}:{side}") + 42
    random.seed(seed)


def _make_cop_points(
    num: int,
    in_toe: bool,
    side: FootSide,
    target_date: str,
) -> list[dict[str, float]]:
    _seed_for_foot(target_date, side)
    centroids = _boundary_centroids()
    cy_values = [cy for _, _, cy in centroids]
    cx_values = [cx for _, cx, _ in centroids]
    heel_cy = max(cy_values)
    toe_cy = min(cy_values)
    mid_cx = sum(cx_values) / len(cx_values)
    lateral_sign = -1.0 if side == "right" else 1.0
    in_toe_bias = 14.0 if in_toe else 0.0

    points: list[dict[str, float]] = []
    for i in range(num):
        t = i / max(num - 1, 1)
        cy = heel_cy + (toe_cy - heel_cy) * t + random.gauss(0, 3.5)
        cx = mid_cx + lateral_sign * in_toe_bias * (0.35 + 0.65 * t)
        cx += math.sin(t * math.pi * 2.4) * (4.0 if in_toe else 2.0)
        cx += random.gauss(0, 2.5)
        display_x, display_y = _cop_display_coords(cx, cy, side)
        points.append(
            {
                "x": round(display_x, 4),
                "y": round(display_y, 4),
                "pressure": round(1400 + random.random() * 1000, 1),
            }
        )
    return points


def _make_static_pressures(
    in_toe: bool,
    side: FootSide,
    target_date: str,
) -> list[int]:
    _seed_for_foot(f"{target_date}:pressures:{side}", side)
    centroids = _boundary_centroids()
    pressures = [0] * 16
    for fsr_index, cx, cy in centroids:
        toe_weight = 1.0 - (cy - 40.0) / 250.0
        medial_weight = 1.0
        if in_toe:
            medial_weight = 1.35 if (side == "right" and cx < 70) or (side == "left" and cx > 62) else 0.82
        base = max(20, min(255, round(90 + toe_weight * 110 * medial_weight + random.gauss(0, 12))))
        pressures[fsr_index] = base
    return pressures


def _foot_analysis(
    in_toe: bool,
    side: FootSide,
    classification: str,
    confidence: float,
    target_date: str,
) -> dict[str, Any]:
    return {
        "pressures": _make_static_pressures(in_toe, side, target_date),
        "copPoints": _make_cop_points(100, in_toe, side, target_date),
        "classification": classification,
        "confidence": confidence,
    }


@app.get("/api/gait/summary")
def get_gait_summary(
    date_param: str = Query(default=None, alias="date"),
    x_api_key: str | None = Header(default=None),
) -> dict[str, Any]:
    verify_api_key(x_api_key)
    target = date.today().isoformat() if date_param is None else date_param
    return {
        "date": target,
        "leftFoot": _foot_analysis(False, "left", "normal", 0.94, target),
        "rightFoot": _foot_analysis(True, "right", "in_toe", 0.78, target),
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
