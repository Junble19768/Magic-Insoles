"""API dependencies."""

from __future__ import annotations

from fastapi import Header, HTTPException

from config import settings


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
