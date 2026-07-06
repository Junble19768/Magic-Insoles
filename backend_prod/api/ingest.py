"""HTTP ingest endpoint (debug/simulation)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import verify_api_key
from database import IngestRequest, get_db
from services.ingest import ingest_http_frames

router = APIRouter(prefix="/api", tags=["ingest"])


@router.post("/ingest")
def ingest_frames(
    payload: IngestRequest,
    _: None = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    received = ingest_http_frames(payload.frames, db)
    return {"received": received, "status": "ok"}
