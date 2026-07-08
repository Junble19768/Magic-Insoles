import threading
from pathlib import Path
from typing import Protocol

import numpy as np

from .hub import DataHub
from .io_readers import force_reader_thread, fsr_reader
from .pipeline import AlignPipeline


class PipelineLike(Protocol):
    def enqueue_fsr(self, stamp: float, data: np.ndarray) -> None: ...

    def update_force(self, stamp: float, value: float) -> None: ...

    def interp_force(self, stamp: float) -> float | None: ...

    def clear_anchors(self) -> None: ...

    def shutdown(self) -> None: ...

    def snapshot(self) -> tuple[list[tuple[float, float]], Path | None, bool, int]: ...


class NoOpPipeline:
    """Minimal pipeline for visualize-only mode (FSR reader requires enqueue_fsr)."""

    def enqueue_fsr(self, stamp: float, data: np.ndarray) -> None:
        del stamp, data

    def update_force(self, stamp: float, value: float) -> None:
        del stamp, value

    def interp_force(self, stamp: float) -> float | None:
        del stamp
        return None

    def request_start_record(self) -> Path:
        raise RuntimeError("此模式不支持录制")

    def request_stop_record(self) -> int:
        return 0

    def clear_anchors(self) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def snapshot(self) -> tuple[list[tuple[float, float]], Path | None, bool, int]:
        return [], None, False, 0


class ReaderRuntime:
    def __init__(
        self,
        hub: DataHub,
        *,
        with_force: bool = True,
        pipeline: PipelineLike | None = None,
    ) -> None:
        self.hub = hub
        self.with_force = with_force
        if pipeline is not None:
            self.pipeline = pipeline
        elif with_force:
            self.pipeline = AlignPipeline()
        else:
            self.pipeline = NoOpPipeline()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        self._threads.append(
            threading.Thread(
                target=fsr_reader,
                args=(self.hub, self.pipeline, self._stop),
                daemon=True,
            )
        )
        if self.with_force:
            self._threads.append(
                threading.Thread(
                    target=force_reader_thread,
                    args=(self.hub, self.pipeline, self._stop),
                    daemon=True,
                )
            )
        for thread in self._threads:
            thread.start()

    def stop(self) -> None:
        self._stop.set()
        self.pipeline.shutdown()
