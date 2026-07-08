import threading

import numpy as np


def fsr_label(index: int) -> str:
    foot = "左脚" if index < 16 else "右脚"
    return f"FSR {index:02d} ({foot} #{index % 16})"


class DataHub:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.fsr_data = np.zeros(32, dtype=float)
        self.fsr_stamp = 0.0
        self.fsr_connected = False
        self.force_values = [0.0]
        self.force_stamp = 0.0
        self.force_connected = False

    def set_fsr(self, data: np.ndarray, stamp: float) -> None:
        with self._lock:
            self.fsr_data = data.copy()
            self.fsr_stamp = stamp
            self.fsr_connected = True

    def set_force(self, values: list[float], stamp: float) -> None:
        with self._lock:
            self.force_values = list(values)
            self.force_stamp = stamp
            self.force_connected = True

    def set_fsr_disconnected(self) -> None:
        with self._lock:
            self.fsr_connected = False

    def set_force_disconnected(self) -> None:
        with self._lock:
            self.force_connected = False

    def snapshot(self) -> tuple[np.ndarray, float, bool, list[float], float, bool]:
        with self._lock:
            return (
                self.fsr_data.copy(),
                self.fsr_stamp,
                self.fsr_connected,
                list(self.force_values),
                self.force_stamp,
                self.force_connected,
            )
