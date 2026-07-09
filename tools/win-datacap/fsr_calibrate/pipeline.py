import csv
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from queue import Empty, SimpleQueue
from typing import Any

import numpy as np

from .config import CSV_FLUSH_EVERY_ROWS, FORCE_ANCHOR_WINDOW_S, FORCE_DEDUP_INTERVAL_S, FORCE_INTERP_MAX_SKEW_S, HISTORY, RECORD_DIR


def can_interp_force(fsr_stamp: float, anchor_t: np.ndarray) -> bool:
    if len(anchor_t) < 2:
        return False
    t_min, t_max = float(anchor_t[0]), float(anchor_t[-1])
    if t_min <= fsr_stamp <= t_max:
        return True
    skew = FORCE_INTERP_MAX_SKEW_S
    return (t_min - skew) <= fsr_stamp <= (t_max + skew)


def interp_force_at(fsr_stamp: float, anchor_t: np.ndarray, anchor_v: np.ndarray) -> float:
    return float(np.interp(fsr_stamp, anchor_t, anchor_v))


def _csv_header() -> list[str]:
    return ["timestamp", *[f"fsr_{i:02d}" for i in range(32)], "force_ch0"]


class CsvRecorder:
    def __init__(self) -> None:
        self._file = None
        self._writer: Any | None = None
        self._path: Path | None = None
        self._last_fsr_stamp: float | None = None
        self._row_count = 0
        self._pending_flush = 0

    @property
    def is_active(self) -> bool:
        return self._file is not None

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def row_count(self) -> int:
        return self._row_count

    def start(self) -> Path:
        if self.is_active:
            return self._path  # type: ignore[return-value]
        RECORD_DIR.mkdir(parents=True, exist_ok=True)
        self._path = RECORD_DIR / (datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv")
        self._file = open(self._path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        self._writer.writerow(_csv_header())
        self._last_fsr_stamp = None
        self._row_count = 0
        self._pending_flush = 0
        print(f"录制开始: {self._path}")
        return self._path

    def stop(self) -> int:
        if not self.is_active:
            return 0
        count = self._row_count
        if self._file is not None:
            self._file.flush()
            self._file.close()
        self._file = None
        self._writer = None
        self._last_fsr_stamp = None
        print(f"录制结束: {self._path} ({count} 行)")
        return count

    def write_row(self, fsr_stamp: float, fsr_data: np.ndarray, force_value: float) -> bool:
        if not self.is_active or self._writer is None:
            return False
        if self._last_fsr_stamp is not None and fsr_stamp == self._last_fsr_stamp:
            return False
        self._last_fsr_stamp = fsr_stamp
        row: list[float] = [fsr_stamp, *[float(fsr_data[i]) for i in range(32)], float(force_value)]
        self._writer.writerow(row)
        self._pending_flush += 1
        if self._pending_flush >= CSV_FLUSH_EVERY_ROWS and self._file is not None:
            self._file.flush()
            self._pending_flush = 0
        self._row_count += 1
        return True


class FsrRecordPipeline:
    """FSR-only 录制管道（可视化模式，无需参考压力传感器）。"""

    def __init__(self) -> None:
        self._queue: SimpleQueue = SimpleQueue()
        self._lock = threading.Lock()
        self._recorder = CsvRecorder()
        self._record_path: Path | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def enqueue_fsr(self, stamp: float, data: np.ndarray) -> None:
        self._queue.put(("fsr", stamp, data.copy()))

    def update_force(self, stamp: float, value: float) -> None:
        del stamp, value

    def interp_force(self, stamp: float) -> float | None:
        del stamp
        return None

    def request_start_record(self) -> Path:
        done = threading.Event()
        result: dict[str, Path | None] = {"path": None}
        self._queue.put(("start_record", done, result))
        done.wait(timeout=5.0)
        path = result["path"]
        if path is None:
            raise RuntimeError("录制启动超时")
        return path

    def request_stop_record(self) -> int:
        done = threading.Event()
        result: dict[str, int] = {"count": 0}
        self._queue.put(("stop_record", done, result))
        done.wait(timeout=5.0)
        return result["count"]

    def clear_anchors(self) -> None:
        pass

    def shutdown(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2.0)

    def snapshot(self) -> tuple[list[tuple[float, float]], Path | None, bool, int]:
        with self._lock:
            return [], self._record_path, self._recorder.is_active, self._recorder.row_count

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=0.1)
            except Empty:
                continue
            self._dispatch(item)

    def _dispatch(self, item: tuple[Any, ...]) -> None:
        kind = item[0]
        if kind == "fsr":
            _, stamp, data = item
            self._on_fsr(float(stamp), data)
        elif kind == "start_record":
            _, done, result = item
            path = self._recorder.start()
            with self._lock:
                self._record_path = path
            result["path"] = path
            done.set()
        elif kind == "stop_record":
            _, done, result = item
            count = self._recorder.stop()
            with self._lock:
                if not self._recorder.is_active:
                    self._record_path = None
            result["count"] = count
            done.set()

    def _on_fsr(self, stamp: float, data: np.ndarray) -> None:
        with self._lock:
            recording = self._recorder.is_active
        if recording:
            self._recorder.write_row(stamp, data, 0.0)


class AlignPipeline:
    """后台对齐管道：去重推拉力锚点，仅对可插值 FSR 时间戳写 CSV。"""

    def __init__(self) -> None:
        self._queue: SimpleQueue = SimpleQueue()
        self._lock = threading.Lock()
        self._anchors: deque[tuple[float, float]] = deque()
        self._recorder = CsvRecorder()
        self._record_path: Path | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def update_force(self, stamp: float, value: float) -> None:
        with self._lock:
            if self._anchors:
                last_stamp, last_value = self._anchors[-1]
                if value == last_value and (stamp - last_stamp) < FORCE_DEDUP_INTERVAL_S:
                    return
            self._anchors.append((stamp, value))
            self._prune_anchors_locked(stamp)

    def interp_force(self, stamp: float) -> float | None:
        with self._lock:
            anchors = list(self._anchors)
        if not anchors:
            return None
        anchor_t = np.asarray([a[0] for a in anchors], dtype=float)
        if not can_interp_force(stamp, anchor_t):
            return None
        anchor_v = np.asarray([a[1] for a in anchors], dtype=float)
        return interp_force_at(stamp, anchor_t, anchor_v)

    def enqueue_fsr(self, stamp: float, data: np.ndarray) -> None:
        self._queue.put(("fsr", stamp, data.copy()))

    def request_start_record(self) -> Path:
        done = threading.Event()
        result: dict[str, Path | None] = {"path": None}
        self._queue.put(("start_record", done, result))
        done.wait(timeout=5.0)
        path = result["path"]
        if path is None:
            raise RuntimeError("录制启动超时")
        return path

    def request_stop_record(self) -> int:
        done = threading.Event()
        result: dict[str, int] = {"count": 0}
        self._queue.put(("stop_record", done, result))
        done.wait(timeout=5.0)
        return result["count"]

    def clear_anchors(self) -> None:
        self._queue.put(("clear",))

    def shutdown(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2.0)

    def snapshot(self) -> tuple[list[tuple[float, float]], Path | None, bool, int]:
        with self._lock:
            return list(self._anchors), self._record_path, self._recorder.is_active, self._recorder.row_count

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=0.1)
            except Empty:
                continue
            self._dispatch(item)

    def _prune_anchors_locked(self, now: float) -> None:
        cutoff = now - FORCE_ANCHOR_WINDOW_S
        while self._anchors and self._anchors[0][0] < cutoff:
            self._anchors.popleft()
        while len(self._anchors) > HISTORY:
            self._anchors.popleft()

    def _dispatch(self, item: tuple[Any, ...]) -> None:
        kind = item[0]
        if kind == "fsr":
            _, stamp, data = item
            self._on_fsr(float(stamp), data)
        elif kind == "start_record":
            _, done, result = item
            path = self._recorder.start()
            with self._lock:
                self._record_path = path
            result["path"] = path
            done.set()
        elif kind == "stop_record":
            _, done, result = item
            count = self._recorder.stop()
            with self._lock:
                if not self._recorder.is_active:
                    self._record_path = None
            result["count"] = count
            done.set()
        elif kind == "clear":
            with self._lock:
                self._anchors.clear()

    def _on_fsr(self, stamp: float, data: np.ndarray) -> None:
        force_value = self.interp_force(stamp)
        if force_value is None:
            return
        with self._lock:
            recording = self._recorder.is_active
        if recording:
            self._recorder.write_row(stamp, data, force_value)
