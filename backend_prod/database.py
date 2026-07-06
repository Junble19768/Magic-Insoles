"""SQLite connection, ORM models, and Pydantic schemas."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Generator

from pydantic import BaseModel, Field
from sqlalchemy import (
    Column,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import settings

# ── SQLAlchemy ORM ──


class Base(DeclarativeBase):
    pass


class ForceBatch(Base):
    __tablename__ = "force_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seq = Column(Integer, nullable=False)
    start_stamp = Column(Integer, nullable=False)
    receive_time = Column(Float, nullable=False)
    samplecount = Column(Integer, nullable=False)
    samples_json = Column(Text, nullable=False)


class GpsPoint(Base):
    __tablename__ = "gps_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seq = Column(Integer, nullable=False)
    timestamp = Column(Integer, nullable=False)
    receive_time = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, nullable=True)
    speed = Column(Float, nullable=True)
    heading = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    fix_type = Column(Integer, nullable=True)
    satellite_count = Column(Integer, nullable=True)


class DeviceStatusRow(Base):
    __tablename__ = "device_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seq = Column(Integer, nullable=False)
    receive_time = Column(Float, nullable=False)
    battery = Column(Integer, nullable=False)
    device_link = Column(Integer, nullable=False)


class DeviceEvent(Base):
    __tablename__ = "device_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seq = Column(Integer, nullable=False)
    receive_time = Column(Float, nullable=False)
    event_id = Column(Integer, nullable=False)
    stamp = Column(Integer, nullable=False)
    reserved = Column(Integer, nullable=True)


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, nullable=False, unique=True)
    report_text = Column(Text, nullable=False)
    summary_json = Column(Text, nullable=True)


# ── Pydantic request/response ──


class IngestFrame(BaseModel):
    timestamp: float
    pressures: list[int] = Field(min_length=32, max_length=32)
    gait_state: int
    ml_class: int
    ml_conf: float
    step_count: int


class IngestRequest(BaseModel):
    frames: list[IngestFrame]


class DailyFeatures(BaseModel):
    walk_min: int = 0
    step_count: int = 0
    step_freq: int = 0
    gait_summary: str = "数据不足"
    abnormal_pct: float = 0.0
    symmetry_desc: str = "暂无对称性数据"

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ── Database session ──

engine = create_engine(
    f"sqlite:///{settings.db_path_resolved}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    settings.db_path_resolved.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def day_bounds(date_str: str) -> tuple[float, float]:
    """Return [start, end) Unix timestamps for a local calendar date."""
    day = date.fromisoformat(date_str)
    start = datetime.combine(day, datetime.min.time()).timestamp()
    end = datetime.combine(day, datetime.max.time()).timestamp()
    return start, end


def samples_to_json(samples: list[list[int]]) -> str:
    return json.dumps(samples)
