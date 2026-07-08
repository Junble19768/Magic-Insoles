"""Ingest service unit tests."""

from __future__ import annotations

import json
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, ForceBatch, GpsPoint, IngestFrame
from protocol.device_frame import DeviceFrame, build_frame
from protocol.payloads import DATA_TYPE_FORCE, DATA_TYPE_GPS, parse_gps
from services.ingest import build_force_payload, ingest_frame, ingest_http_frames
import struct

from pygcj.pygcj import GCJProj
trans = GCJProj()

@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_ingest_force_frame(db_session) -> None:
    payload = build_force_payload(12345, 1, [[42] * 32])
    frame = DeviceFrame(seq=7, data_type=DATA_TYPE_FORCE, payload=payload)
    ingest_frame(frame, db_session)
    rows = db_session.query(ForceBatch).all()
    assert len(rows) == 1
    assert rows[0].seq == 7
    samples = json.loads(rows[0].samples_json)
    assert samples[0][0] == 42


def test_ingest_gps_frame(db_session) -> None:
    payload = struct.pack(
        "<QddffffBB",
        1_700_000_000_000,
        40.02,
        116.39,
        50.0,
        1.2,
        90.0,
        3.5,
        3,
        8,
    )

    gcj_lat, gcj_lon = trans.wgs_to_gcj(40.02, 116.39)
    frame = DeviceFrame(seq=3, data_type=DATA_TYPE_GPS, payload=payload)
    ingest_frame(frame, db_session)
    rows = db_session.query(GpsPoint).all()
    assert len(rows) == 1
    assert abs(rows[0].latitude - gcj_lat) < 0.001


def test_http_ingest_path(db_session) -> None:
    frames = [
        IngestFrame(
            timestamp=time.time(),
            pressures=[100] * 32,
            gait_state=1,
            ml_class=0,
            ml_conf=0.9,
            step_count=10,
        )
    ]
    count = ingest_http_frames(frames, db_session)
    assert count == 1
    assert db_session.query(ForceBatch).count() == 1
