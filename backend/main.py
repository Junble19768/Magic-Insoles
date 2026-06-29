"""FastAPI test stub for frontend integration."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from fastapi import FastAPI, Header, HTTPException
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
