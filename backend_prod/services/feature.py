"""Daily feature extraction: step frequency, COP, symmetry."""

from __future__ import annotations

import json
import math
from typing import Any

from sqlalchemy.orm import Session

from database import DailyFeatures, DeviceEvent, ForceBatch, day_bounds
from protocol.payloads import EVENT_ID_HEARTBEAT

# 4x4 uniform grid placeholder (TBD-1/TBD-2)
_SENSOR_COORDS: list[tuple[float, float]] = []
for row in range(4):
    for col in range(4):
        x = -0.75 + col * 0.5
        y = -0.75 + row * 0.5
        _SENSOR_COORDS.append((x, y))


def compute_daily_features(date_str: str, db: Session) -> DailyFeatures:
    start_ts, end_ts = day_bounds(date_str)

    batches = (
        db.query(ForceBatch)
        .filter(
            ForceBatch.receive_time >= start_ts,
            ForceBatch.receive_time <= end_ts,
        )
        .order_by(ForceBatch.receive_time)
        .all()
    )

    events = (
        db.query(DeviceEvent)
        .filter(
            DeviceEvent.receive_time >= start_ts,
            DeviceEvent.receive_time <= end_ts,
            DeviceEvent.event_id != EVENT_ID_HEARTBEAT,
        )
        .order_by(DeviceEvent.stamp)
        .all()
    )

    walk_min = _estimate_walk_minutes(batches)
    step_count = _estimate_step_count(events, batches)
    step_freq = _estimate_step_freq(events, walk_min, batches)
    gait_summary, abnormal_pct = _estimate_gait(events)
    symmetry_desc = _compute_symmetry(batches)

    return DailyFeatures(
        walk_min=walk_min,
        step_count=step_count,
        step_freq=step_freq,
        gait_summary=gait_summary,
        abnormal_pct=abnormal_pct,
        symmetry_desc=symmetry_desc,
    )


def compute_cop_points(
    batches: list[ForceBatch], foot_offset: int
) -> list[dict[str, float]]:
    """Return COP trajectory points for one foot (16 sensors)."""
    points: list[dict[str, float]] = []
    for batch in batches:
        samples = json.loads(batch.samples_json)
        if not samples:
            continue
        sample = samples[-1]
        foot_values = sample[foot_offset : foot_offset + 16]
        total = sum(foot_values)
        if total <= 0:
            continue
        cx = 0.0
        cy = 0.0
        for index, value in enumerate(foot_values):
            x, y = _SENSOR_COORDS[index]
            cx += x * value
            cy += y * value
        cx /= total
        cy /= total
        points.append({"x": round(cx, 4), "y": round(cy, 4), "pressure": total})
    return points


def average_foot_pressures(
    batches: list[ForceBatch], foot_offset: int
) -> list[int]:
    """Average per-sensor pressure for one foot across batches."""
    if not batches:
        return [0] * 16
    sums = [0.0] * 16
    count = 0
    for batch in batches:
        samples = json.loads(batch.samples_json)
        if not samples:
            continue
        sample = samples[-1]
        foot_values = sample[foot_offset : foot_offset + 16]
        for index, value in enumerate(foot_values):
            sums[index] += value
        count += 1
    if count == 0:
        return [0] * 16
    return [int(sums[i] / count) for i in range(16)]


def _estimate_walk_minutes(batches: list[ForceBatch]) -> int:
    if len(batches) < 2:
        return max(1, len(batches)) if batches else 0
    duration_sec = batches[-1].receive_time - batches[0].receive_time
    return max(1, int(round(duration_sec / 60)))


def _estimate_step_count(
    events: list[DeviceEvent], batches: list[ForceBatch]
) -> int:
    if events:
        return len(events)
    if not batches:
        return 0
    peaks = 0
    prev_total = 0
    for batch in batches:
        samples = json.loads(batch.samples_json)
        if not samples:
            continue
        total = sum(samples[-1])
        if total > 5000 and prev_total <= 5000:
            peaks += 1
        prev_total = total
    return max(peaks, len(batches) // 10)


def _estimate_step_freq(
    events: list[DeviceEvent],
    walk_min: int,
    batches: list[ForceBatch],
) -> int:
    if walk_min <= 0:
        return 0
    if events:
        return int(round(len(events) / walk_min))
    step_count = _estimate_step_count(events, batches)
    return int(round(step_count / walk_min)) if walk_min > 0 else 0


def _estimate_gait(events: list[DeviceEvent]) -> tuple[str, float]:
    if not events:
        return "数据不足", 0.0
    abnormal = sum(1 for event in events if event.event_id in (1, 2))
    pct = round(abnormal / len(events) * 100, 1)
    if pct < 5:
        return "步态整体正常", pct
    if pct < 15:
        return "轻度异常", pct
    return "需关注", pct


def _compute_symmetry(batches: list[ForceBatch]) -> str:
    if not batches:
        return "暂无对称性数据"
    left_sum = 0.0
    right_sum = 0.0
    count = 0
    for batch in batches:
        samples = json.loads(batch.samples_json)
        if not samples:
            continue
        sample = samples[-1]
        left_sum += sum(sample[0:16])
        right_sum += sum(sample[16:32])
        count += 1
    if count == 0 or left_sum + right_sum <= 0:
        return "暂无对称性数据"
    ratio = left_sum / right_sum if right_sum > 0 else 1.0
    diff_pct = abs(1.0 - ratio) * 100
    if diff_pct < 10:
        return "左右脚压力分布基本对称"
    if diff_pct < 20:
        return "左右脚压力略有差异"
    return "左右脚压力分布不对称，建议关注"


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
