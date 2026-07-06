"""Feature extraction unit tests."""

from __future__ import annotations

import json
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, DeviceEvent, ForceBatch
from protocol.payloads import EVENT_ID_HEARTBEAT
from services.feature import compute_cop_points, compute_daily_features


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _add_force_batch(session, pressures: list[int], receive_time: float) -> None:
    row = ForceBatch(
        seq=1,
        start_stamp=int(receive_time * 1000),
        receive_time=receive_time,
        samplecount=1,
        samples_json=json.dumps([pressures]),
    )
    session.add(row)
    session.commit()


def test_symmetry_balanced(db_session) -> None:
    now = time.time()
    left_heavy = [1000] * 16 + [1000] * 16
    _add_force_batch(db_session, left_heavy, now)
    features = compute_daily_features(
        time.strftime("%Y-%m-%d", time.localtime(now)), db_session
    )
    assert "对称" in features.symmetry_desc


def test_step_count_from_events(db_session) -> None:
    now = time.time()
    date_str = time.strftime("%Y-%m-%d", time.localtime(now))
    for index in range(5):
        db_session.add(
            DeviceEvent(
                seq=index,
                receive_time=now,
                event_id=10,
                stamp=int(now * 1000) + index * 500,
                reserved=0,
            )
        )
    db_session.commit()
    features = compute_daily_features(date_str, db_session)
    assert features.step_count == 5


def test_cop_points_generated(db_session) -> None:
    now = time.time()
    pressures = [0] * 32
    pressures[0] = 5000
    pressures[16] = 3000
    _add_force_batch(db_session, pressures, now)
    batches = db_session.query(ForceBatch).all()
    left = compute_cop_points(batches, 0)
    right = compute_cop_points(batches, 16)
    assert len(left) == 1
    assert len(right) == 1
    assert left[0]["pressure"] == 5000
