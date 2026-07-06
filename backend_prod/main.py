"""magic-insoles production backend — FastAPI entry."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import activity, gait, gps, ingest, report
from config import settings
from database import init_db
from services import tcp_ingest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    logger.info("Database initialized at %s", settings.db_path_resolved)
    await tcp_ingest.start_tcp_server()
    try:
        yield
    finally:
        await tcp_ingest.stop_tcp_server()


app = FastAPI(
    title="magic-insoles API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(report.router)
app.include_router(activity.router)
app.include_router(gait.router)
app.include_router(gps.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
