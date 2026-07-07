#!/usr/bin/env python3
"""
FSR 标定客户端：同时订阅 USB-DAQ FSR（TCP）与 Modbus 压力传感器（WebSocket），
在同一曲线图中对比 ADC 电压与参考压力值；可加载 plot_fsr_grid_fit 导出的 YAML，
将电压反算为真实压力并做双脚热力图可视化。

用法：
  1. python server.py          # FSR 数据源
  2. python force_server.py    # 压力传感器 WebSocket 源
  3. python fsr_calibrate.py   # 本脚本
"""

import asyncio
import csv
import json
import struct
import socket
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from queue import Empty, SimpleQueue
from typing import Any

import numpy as np
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import yaml

try:
    import websockets
except ImportError as exc:
    raise SystemExit("请先安装 websockets: pip install websockets") from exc

# ── 连接配置 ───────────────────────────────────────────────
FSR_HOST = "127.0.0.1"
FSR_PORT = 6543
FSR_PACKET_SIZE = 320

FORCE_WS_URL = "ws://127.0.0.1:8765"

HISTORY = 500
UI_TIMER_MS = 16
PLOT_WINDOW_S = 5.0
STATUS_UPDATE_INTERVAL_S = 0.2
CSV_FLUSH_EVERY_ROWS = 20
# 压力锚点保留时长；FSR 帧在队列中等待后时间戳可能略早于当前锚点窗口
FORCE_ANCHOR_WINDOW_S = 60.0
FORCE_INTERP_MAX_SKEW_S = 2.0
# 压力值不变时，距上次接受读数超过该间隔仍写入锚点队列
FORCE_DEDUP_INTERVAL_S = 0.3

FORCE_CHANNEL_NAME = "Ch0_Reg0-1"

RECORD_DIR = Path(__file__).resolve().parent / "record"
DEFAULT_CALIB_YAML = RECORD_DIR / "9mm" / "result.yml"

MODEL_UI_TO_YAML: dict[str, str] = {
    "指数函数": "exponential",
    "幂函数": "power",
    "倒数函数": "inverse",
}

FOOT_GRID_ROWS = 25
FOOT_GRID_COLS = 60
FOOT_SCALE_UP = 8
FOOT_BLUR_SIGMA = 2.0

# 单脚 16 点布局（local index 0-15）：(idx, r0, r1, c0, c1)
FOOT_SENSOR_REGIONS: tuple[tuple[int, int, int, int, int], ...] = (
    (12, 2, 6, 3, 13),
    (13, 8, 12, 1, 13),
    (14, 14, 18, 1, 13),
    (15, 20, 24, 3, 13),
    (11, 20, 24, 21, 28),
    (0, 2, 6, 14, 24),
    (1, 8, 12, 14, 24),
    (2, 14, 18, 14, 24),
    (10, 16, 23, 36, 46),
    (4, 6, 12, 25, 35),
    (5, 14, 18, 25, 35),
    (6, 20, 24, 29, 35),
    (8, 16, 23, 47, 57),
    (9, 8, 15, 36, 46),
    (3, 20, 24, 14, 20),
    (7, 8, 15, 47, 57),
)


@dataclass
class ChannelFit:
    ok: bool
    params: dict[str, float] = field(default_factory=dict)


class CalibrationStore:
    """加载 plot_fsr_grid_fit 导出的 result.yml，提供 R(F) 反算。"""

    def __init__(self) -> None:
        self.vcc_v = 3.3
        self.r_fixed_ohm = 35_000.0
        self.channel_fits: dict[int, dict[str, ChannelFit]] = {}
        self.loaded_path: Path | None = None
        self.load_error: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self.loaded_path is not None and self.load_error is None

    def load(self, path: Path) -> None:
        self.loaded_path = None
        self.load_error = None
        self.channel_fits.clear()
        try:
            with open(path, encoding="utf-8") as f:
                payload = yaml.safe_load(f)
        except OSError as exc:
            self.load_error = str(exc)
            return
        except yaml.YAMLError as exc:
            self.load_error = f"YAML 解析失败: {exc}"
            return

        if not isinstance(payload, dict):
            self.load_error = "YAML 根节点不是字典"
            return

        meta = payload.get("meta", {})
        if isinstance(meta, dict):
            self.vcc_v = float(meta.get("vcc_v", self.vcc_v))
            self.r_fixed_ohm = float(meta.get("r_fixed_ohm", self.r_fixed_ohm))

        entries = payload.get("entries", [])
        if not isinstance(entries, list):
            self.load_error = "entries 不是列表"
            return

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            ch = entry.get("fsr_channel")
            fits = entry.get("fits")
            if ch is None or not isinstance(fits, dict):
                continue
            ch_int = int(ch)
            self.channel_fits[ch_int] = {}
            for model_key in ("exponential", "power", "inverse"):
                block = fits.get(model_key, {})
                if not isinstance(block, dict):
                    self.channel_fits[ch_int][model_key] = ChannelFit(ok=False)
                    continue
                ok = bool(block.get("ok", False))
                params_raw = block.get("params")
                params: dict[str, float] = {}
                if ok and isinstance(params_raw, dict):
                    params = {k: float(v) for k, v in params_raw.items()}
                    ok = all(np.isfinite(v) for v in params.values())
                self.channel_fits[ch_int][model_key] = ChannelFit(ok=ok, params=params)

        if not self.channel_fits:
            self.load_error = "YAML 中无有效通道拟合条目"
            return

        self.loaded_path = path
        print(f"标定 YAML 已加载: {path} ({len(self.channel_fits)} 通道)")

    def voltage_to_resistance(self, voltage_v: np.ndarray) -> np.ndarray:
        v = np.clip(voltage_v, 1e-6, self.vcc_v - 1e-6)
        return self.r_fixed_ohm * (self.vcc_v - v) / v

    def resistance_to_force(
        self, resistance_ohm: float, channel: int, model_key: str
    ) -> float:
        if not np.isfinite(resistance_ohm) or resistance_ohm <= 0:
            return float("nan")
        fits = self.channel_fits.get(channel, {})
        fit = fits.get(model_key)
        if fit is None or not fit.ok:
            return float("nan")

        p = fit.params
        try:
            if model_key == "exponential":
                a, b = p["a"], p["b"]
                if a <= 0 or b == 0:
                    return float("nan")
                ratio = resistance_ohm / a
                if ratio <= 0:
                    return float("nan")
                return float(np.log(ratio) / b)
            if model_key == "power":
                a, b = p["a"], p["b"]
                if a <= 0 or b == 0:
                    return float("nan")
                ratio = resistance_ohm / a
                if ratio <= 0:
                    return float("nan")
                return float(np.power(ratio, 1.0 / b))
            if model_key == "inverse":
                a, c = p["a"], p["c"]
                denom = resistance_ohm - c
                if abs(denom) < 1e-9:
                    return float("nan")
                force = a / denom
                return float(force) if force > 0 else float("nan")
        except (KeyError, ValueError, OverflowError):
            return float("nan")
        return float("nan")

    def voltages_to_forces(self, voltages: np.ndarray, model_key: str) -> np.ndarray:
        resistances = self.voltage_to_resistance(voltages)
        out = np.full(32, np.nan, dtype=float)
        for ch in range(32):
            out[ch] = self.resistance_to_force(float(resistances[ch]), ch, model_key)
        return out

    def channel_model_ok(self, channel: int, model_key: str) -> bool:
        fit = self.channel_fits.get(channel, {}).get(model_key)
        return fit is not None and fit.ok


def _gaussian_kernel_1d(sigma: float) -> np.ndarray:
    size = max(3, int(6 * sigma + 1) | 1)
    half = size // 2
    x = np.arange(-half, half + 1, dtype=float)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    return k / k.sum()


def _gaussian_blur_2d(arr: np.ndarray, sigma: float) -> np.ndarray:
    k = _gaussian_kernel_1d(sigma)
    pad = len(k) // 2
    padded = np.pad(arr, pad, mode="edge")
    tmp = np.apply_along_axis(lambda row: np.convolve(row, k, mode="valid"), 1, padded)
    return np.apply_along_axis(lambda col: np.convolve(col, k, mode="valid"), 0, tmp)


def _fill_foot_grid(foot_values: np.ndarray) -> np.ndarray:
    img = np.zeros((FOOT_GRID_ROWS, FOOT_GRID_COLS), dtype=float)
    for idx, r0, r1, c0, c1 in FOOT_SENSOR_REGIONS:
        img[r0:r1, c0:c1] = foot_values[idx]
    return img


def _sensor_label_positions() -> list[tuple[int, float, float]]:
    """按原始脚底网格（未转置）计算传感器文字中心。"""
    positions: list[tuple[int, float, float]] = []
    for idx, r0, r1, c0, c1 in FOOT_SENSOR_REGIONS:
        cx = (c0 + c1) * 0.5 * FOOT_SCALE_UP
        cy = (r0 + r1) * 0.5 * FOOT_SCALE_UP
        positions.append((idx, cx, cy))
    return positions


def build_foot_heatmap(
    foot_values: np.ndarray, flip_horizontal: bool
) -> tuple[np.ndarray, np.ndarray]:
    """生成放大后的脚底热力图与用于着色的原始 16 点值。"""
    grid = _fill_foot_grid(foot_values)
    blurred = _gaussian_blur_2d(grid, FOOT_BLUR_SIGMA)
    if flip_horizontal:
        blurred = np.flip(blurred, axis=0)
    scaled = np.repeat(np.repeat(blurred, FOOT_SCALE_UP, axis=0), FOOT_SCALE_UP, axis=1)
    return scaled, foot_values.copy()


class FootPressurePanel(pg.GraphicsLayoutWidget):
    """双脚压力/电压热力图，叠加 1 位小数数值标注。"""

    def __init__(self) -> None:
        super().__init__()
        self._left_labels: list[pg.TextItem] = []
        self._right_labels: list[pg.TextItem] = []
        self._sensor_positions = _sensor_label_positions()

        self.left_plot = self.addPlot(row=0, col=0, title="左脚")
        self.right_plot = self.addPlot(row=0, col=1, title="右脚")
        for plot in (self.left_plot, self.right_plot):
            plot.setAspectLocked(True)
            plot.hideAxis("left")
            plot.hideAxis("bottom")
            plot.invertY(True)

        self.left_image = pg.ImageItem()
        self.right_image = pg.ImageItem()
        self.left_plot.addItem(self.left_image)
        self.right_plot.addItem(self.right_image)

        self._cmap = pg.colormap.get("viridis")
        self._show_pressure = False

    def set_value_mode(self, show_pressure: bool) -> None:
        self._show_pressure = show_pressure

    def update_feet(
        self,
        display_values: np.ndarray,
        raw_foot_values: tuple[np.ndarray, np.ndarray],
    ) -> None:
        left_raw, right_raw = raw_foot_values
        left_img, _ = build_foot_heatmap(display_values[:16], flip_horizontal=True)
        right_img, _ = build_foot_heatmap(display_values[16:32], flip_horizontal=False)

        max_data = float(np.nanmax([left_img.max(), right_img.max(), 0.0]))
        if self._show_pressure:
            denom = max(max_data, 100.0)
            left_img = left_img / denom
            right_img = right_img / denom
            vmax = 1.0
        else:
            vmax = float(np.nanmax([left_img.max(), right_img.max(), 0.01]))
        for image, img_data in ((self.left_image, left_img), (self.right_image, right_img)):
            image.setImage(img_data, autoLevels=False)
            image.setLevels((0.0, vmax))
            image.setLookupTable(self._cmap.getLookupTable(0, vmax))

        self._update_labels(
            self.left_plot, self._left_labels, left_raw, flip_horizontal=True
        )
        self._update_labels(
            self.right_plot, self._right_labels, right_raw, flip_horizontal=False
        )

    def _update_labels(
        self,
        plot: pg.PlotItem,
        label_pool: list[pg.TextItem],
        foot_values: np.ndarray,
        flip_horizontal: bool,
    ) -> None:
        needed = len(self._sensor_positions)
        while len(label_pool) < needed:
            text = pg.TextItem(anchor=(0.5, 0.5), color=(255, 255, 255))
            text.setFont(QtGui.QFont("Arial", 8, QtGui.QFont.Bold))
            plot.addItem(text)
            label_pool.append(text)

        width = FOOT_GRID_COLS * FOOT_SCALE_UP
        height = FOOT_GRID_ROWS * FOOT_SCALE_UP
        for i, (local_idx, cx, cy) in enumerate(self._sensor_positions):
            text_item = label_pool[i]
            val = float(foot_values[local_idx])
            # x_pos = (width - cx) if flip_horizontal else cx
            x_pos = cx
            y_pos = (height - cy) if flip_horizontal else cy
            if self._show_pressure:
                label = f"{val:.1f}" if np.isfinite(val) else "—"
            else:
                label = f"{val:.2f}" if np.isfinite(val) else "—"
            text_item.setText(label)
            text_item.setPos(y_pos, x_pos)
            text_item.setVisible(True)


def can_interp_force(fsr_stamp: float, anchor_t: np.ndarray) -> bool:
    if len(anchor_t) < 2:
        return False
    t_min, t_max = float(anchor_t[0]), float(anchor_t[-1])
    if t_min <= fsr_stamp <= t_max:
        return True
    # FSR 在队列中等待时锚点窗口已前移，允许小范围外推
    skew = FORCE_INTERP_MAX_SKEW_S
    return (t_min - skew) <= fsr_stamp <= (t_max + skew)


def interp_force_at(
    fsr_stamp: float, anchor_t: np.ndarray, anchor_v: np.ndarray
) -> float:
    return float(np.interp(fsr_stamp, anchor_t, anchor_v))


def _csv_header() -> list[str]:
    cols = ["timestamp"]
    cols.extend(f"fsr_{i:02d}" for i in range(32))
    cols.append("force_ch0")
    return cols


class CsvRecorder:
    """按 FSR 帧节拍写入 CSV，文件名取开始录制时的系统时间。"""

    def __init__(self):
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
        name = datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"
        self._path = RECORD_DIR / name
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
        path = self._path
        if self._file is not None:
            self._file.flush()
            self._file.close()
        self._file = None
        self._writer = None
        self._last_fsr_stamp = None
        print(f"录制结束: {path} ({count} 行)")
        return count

    def write_row(
        self,
        fsr_stamp: float,
        fsr_data: np.ndarray,
        force_value: float,
    ) -> bool:
        if not self.is_active or self._writer is None:
            return False
        if self._last_fsr_stamp is not None and fsr_stamp == self._last_fsr_stamp:
            return False
        self._last_fsr_stamp = fsr_stamp
        row: list[float | str | int] = [fsr_stamp]
        row.extend(float(fsr_data[i]) for i in range(32))
        row.append(float(force_value))
        self._writer.writerow(row)
        self._pending_flush += 1
        if self._pending_flush >= CSV_FLUSH_EVERY_ROWS and self._file is not None:
            self._file.flush()
            self._pending_flush = 0
        self._row_count += 1
        return True


class AlignPipeline:
    """后台对齐管道：去重推拉力锚点，仅对可插值 FSR 时间戳写 CSV。"""

    def __init__(self):
        self._queue: SimpleQueue = SimpleQueue()
        self._lock = threading.Lock()
        self._anchors: deque[tuple[float, float]] = deque()
        self._recorder = CsvRecorder()
        self._record_path: Path | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def update_force(self, stamp: float, value: float) -> None:
        """压力采样在采集线程直接更新锚点，避免 ~kHz 入队淹没 FSR 事件。"""
        with self._lock:
            if self._anchors:
                last_stamp, last_value = self._anchors[-1]
                if (
                    value == last_value
                    and (stamp - last_stamp) < FORCE_DEDUP_INTERVAL_S
                ):
                    return
            self._anchors.append((stamp, value))
            self._prune_anchors_locked(stamp)

    def interp_force(self, stamp: float) -> float | None:
        """在压力锚点队列上对给定时间戳做线性插值。"""
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
            return (
                list(self._anchors),
                self._record_path,
                self._recorder.is_active,
                self._recorder.row_count,
            )

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

    def _dispatch(self, item: tuple) -> None:
        kind = item[0]
        if kind == "fsr":
            _, stamp, data = item
            self._on_fsr(stamp, data)
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


def _fsr_label(index: int) -> str:
    foot = "左脚" if index < 16 else "右脚"
    local = index % 16
    return f"FSR {index:02d} ({foot} #{local})"


class DataHub:
    """后台线程写入，UI 线程读取的最新采样缓存。"""

    def __init__(self):
        self._lock = threading.Lock()
        self.fsr_data = np.zeros(32, dtype=float)
        self.fsr_stamp = 0.0
        self.fsr_connected = False
        self.force_values = [0.0]
        self.force_stamp = 0.0
        self.force_connected = False

    def set_fsr(self, data: np.ndarray, stamp: float):
        with self._lock:
            self.fsr_data = data.copy()
            self.fsr_stamp = stamp
            self.fsr_connected = True

    def set_force(self, values: list, stamp: float):
        with self._lock:
            self.force_values = list(values)
            self.force_stamp = stamp
            self.force_connected = True

    def snapshot(self):
        with self._lock:
            return (
                self.fsr_data.copy(),
                self.fsr_stamp,
                self.fsr_connected,
                list(self.force_values),
                self.force_stamp,
                self.force_connected,
            )


def _fsr_reader(
    hub: DataHub, pipeline: AlignPipeline, stop_event: threading.Event
):
    while not stop_event.is_set():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((FSR_HOST, FSR_PORT))
            sock.settimeout(1.0)
            print(f"FSR 已连接 {FSR_HOST}:{FSR_PORT}")
            buf = b""
            while not stop_event.is_set():
                try:
                    chunk = sock.recv(FSR_PACKET_SIZE - len(buf))
                except socket.timeout:
                    continue
                if not chunk:
                    break
                buf += chunk
                if len(buf) < FSR_PACKET_SIZE:
                    continue
                packet, buf = buf[:FSR_PACKET_SIZE], buf[FSR_PACKET_SIZE:]
                values = struct.unpack("40d", packet)
                fsr_data = np.array(values[:32], dtype=float)
                fsr_stamp = values[32]
                hub.set_fsr(fsr_data, fsr_stamp)
                pipeline.enqueue_fsr(fsr_stamp, fsr_data)
        except OSError as e:
            with hub._lock:
                hub.fsr_connected = False
            print(f"FSR 连接失败，1 秒后重试: {e}")
            time.sleep(1.0)
        finally:
            sock.close()


async def _force_ws_loop(
    hub: DataHub, pipeline: AlignPipeline, stop_event: threading.Event
):
    while not stop_event.is_set():
        try:
            async with websockets.connect(FORCE_WS_URL) as ws:
                print(f"压力传感器已连接 {FORCE_WS_URL}")
                async for msg in ws:
                    if stop_event.is_set():
                        break
                    payload = json.loads(msg)
                    values = payload.get("values", [])
                    if not values:
                        continue
                    stamp = float(payload.get("timestamp", time.time()))
                    value = -float(values[0])
                    hub.set_force([value], stamp)
                    pipeline.update_force(stamp, value)
        except Exception as e:
            with hub._lock:
                hub.force_connected = False
            print(f"压力 WebSocket 断开，1 秒后重试: {e}")
            await asyncio.sleep(1.0)


def _force_reader_thread(
    hub: DataHub, pipeline: AlignPipeline, stop_event: threading.Event
):
    asyncio.run(_force_ws_loop(hub, pipeline, stop_event))


class FsrCalibrateApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FSR 标定 — 压力 vs ADC")
        self.resize(1400, 720)

        self.calibration = CalibrationStore()
        self._model_key = MODEL_UI_TO_YAML["幂函数"]
        self._use_pressure_mode = False

        self.hub = DataHub()
        self.pipeline = AlignPipeline()
        self._stop = threading.Event()
        threading.Thread(
            target=_fsr_reader,
            args=(self.hub, self.pipeline, self._stop),
            daemon=True,
        ).start()
        threading.Thread(
            target=_force_reader_thread,
            args=(self.hub, self.pipeline, self._stop),
            daemon=True,
        ).start()

        self.fsr_channel = 0
        self._t_origin: float | None = None
        self._last_fsr_stamp = -1.0
        self._last_status_update = 0.0
        self._ui_fps_count = 0
        self._last_ui_fps_report = time.monotonic()
        self._ui_fps = 0.0
        self._force_interp_now = float("nan")

        self.adc_t_buf: deque[float] = deque(maxlen=HISTORY)
        self.adc_v_buf: deque[float] = deque(maxlen=HISTORY)
        self.force_interp_t_buf: deque[float] = deque(maxlen=HISTORY)
        self.force_interp_v_buf: deque[float] = deque(maxlen=HISTORY)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)

        # ── 控制栏 ─────────────────────────────────────────
        ctrl = QtWidgets.QHBoxLayout()

        ctrl.addWidget(QtWidgets.QLabel("FSR 通道:"))
        self.fsr_combo = QtWidgets.QComboBox()
        for i in range(32):
            self.fsr_combo.addItem(_fsr_label(i), i)
        self.fsr_combo.currentIndexChanged.connect(self._on_fsr_changed)
        ctrl.addWidget(self.fsr_combo)

        ctrl.addSpacing(12)
        ctrl.addWidget(QtWidgets.QLabel("标定 YAML:"))
        self.yaml_path_label = QtWidgets.QLabel("(未加载)")
        self.yaml_path_label.setStyleSheet("color: #666;")
        ctrl.addWidget(self.yaml_path_label)
        self.load_yaml_btn = QtWidgets.QPushButton("加载 YAML…")
        self.load_yaml_btn.clicked.connect(self._on_load_yaml)
        ctrl.addWidget(self.load_yaml_btn)

        ctrl.addSpacing(12)
        ctrl.addWidget(QtWidgets.QLabel("拟合模型:"))
        self.model_combo = QtWidgets.QComboBox()
        for label in MODEL_UI_TO_YAML:
            self.model_combo.addItem(label)
        self.model_combo.setCurrentText("幂函数")
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        ctrl.addWidget(self.model_combo)

        self.pressure_mode_chk = QtWidgets.QCheckBox("真实压力替换电压读数")
        self.pressure_mode_chk.toggled.connect(self._on_pressure_mode_toggled)
        ctrl.addWidget(self.pressure_mode_chk)

        ctrl.addSpacing(12)
        ctrl.addWidget(QtWidgets.QLabel(f"压力: {FORCE_CHANNEL_NAME}"))

        self.clear_btn = QtWidgets.QPushButton("清空曲线")
        self.clear_btn.clicked.connect(self._clear_buffers)
        ctrl.addWidget(self.clear_btn)

        ctrl.addSpacing(12)
        self.start_record_btn = QtWidgets.QPushButton("开始录制")
        self.start_record_btn.clicked.connect(self._on_start_record)
        ctrl.addWidget(self.start_record_btn)

        self.stop_record_btn = QtWidgets.QPushButton("停止录制")
        self.stop_record_btn.clicked.connect(self._on_stop_record)
        self.stop_record_btn.setEnabled(False)
        ctrl.addWidget(self.stop_record_btn)

        ctrl.addStretch()
        root.addLayout(ctrl)

        self.status_label = QtWidgets.QLabel("状态: 等待连接...")
        self.status_label.setStyleSheet("font: 13px;")
        root.addWidget(self.status_label)

        # ── 左侧热力图 + 右侧折线图 ─────────────────────────
        content = QtWidgets.QHBoxLayout()
        self.foot_panel = FootPressurePanel()
        self.foot_panel.setMinimumWidth(420)
        content.addWidget(self.foot_panel, stretch=2)

        self.plot_widget = pg.GraphicsLayoutWidget()
        content.addWidget(self.plot_widget, stretch=3)
        root.addLayout(content)

        self.plot = self.plot_widget.addPlot(title="FSR ADC vs 参考压力")
        self.plot.setLabel("bottom", "时间 (s)")
        self.plot.setLabel("left", "ADC 电压 (V)", color="#0080FF")
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.addLegend(offset=(10, 10))

        self.force_view = pg.ViewBox()
        self.plot.showAxis("right")
        self.plot.scene().addItem(self.force_view)
        self.plot.getAxis("right").linkToView(self.force_view)
        self.force_view.setXLink(self.plot)
        self.plot.getAxis("right").setLabel("压力 (N)", color="#FF6600")

        self.adc_curve = self.plot.plot(
            pen=pg.mkPen(color=(0, 128, 255), width=2),
            name="FSR ADC (V)",
        )
        self.force_curve = pg.PlotCurveItem(
            pen=pg.mkPen(color=(255, 102, 0), width=2),
            name="参考压力(插值)",
        )
        self.force_view.addItem(self.force_curve)

        def _sync_views():
            self.force_view.setGeometry(self.plot.vb.sceneBoundingRect())
            self.force_view.linkedViewChanged(self.plot.vb, self.force_view.XAxis)

        self.plot.vb.sigResized.connect(_sync_views)
        _sync_views()
        self.plot.enableAutoRange(axis="x", enable=False)
        self.plot.enableAutoRange(axis="y", enable=False)
        self.force_view.enableAutoRange(axis="y", enable=False)
        self.plot.setXRange(0, PLOT_WINDOW_S, padding=0)

        if DEFAULT_CALIB_YAML.is_file():
            self.calibration.load(DEFAULT_CALIB_YAML)
            self._update_yaml_status()

        self.timer = QtCore.QTimer()
        self.timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(UI_TIMER_MS)

    def _update_yaml_status(self) -> None:
        if self.calibration.is_loaded and self.calibration.loaded_path is not None:
            self.yaml_path_label.setText(self.calibration.loaded_path.name)
            self.yaml_path_label.setStyleSheet("color: #163B31;")
        elif self.calibration.load_error:
            self.yaml_path_label.setText(f"加载失败: {self.calibration.load_error}")
            self.yaml_path_label.setStyleSheet("color: #CC3300;")
        else:
            self.yaml_path_label.setText("(未加载)")
            self.yaml_path_label.setStyleSheet("color: #666;")

    def _on_load_yaml(self) -> None:
        start_dir = str(RECORD_DIR)
        path_str, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择标定 YAML",
            start_dir,
            "YAML 文件 (*.yml *.yaml);;所有文件 (*)",
        )
        if not path_str:
            return
        self.calibration.load(Path(path_str))
        self._update_yaml_status()
        self._update_plot_axis_labels()
        self._clear_buffers()

    def _on_model_changed(self, label: str) -> None:
        self._model_key = MODEL_UI_TO_YAML.get(label, "power")
        self._update_plot_axis_labels()
        if self._use_pressure_mode:
            self._rebuild_adc_buffer_from_hub()

    def _on_pressure_mode_toggled(self, checked: bool) -> None:
        self._use_pressure_mode = checked
        self.foot_panel.set_value_mode(checked)
        self._update_plot_axis_labels()
        self._rebuild_adc_buffer_from_hub()

    def _update_plot_axis_labels(self) -> None:
        if self._use_pressure_mode:
            self.plot.setLabel("left", "FSR 估算压力 (N)", color="#0080FF")
            self.adc_curve.opts["name"] = "FSR 估算压力 (N)"
        else:
            self.plot.setLabel("left", "ADC 电压 (V)", color="#0080FF")
            self.adc_curve.opts["name"] = "FSR ADC (V)"

    def _fsr_display_value(self, fsr_data: np.ndarray, channel: int) -> float:
        if self._use_pressure_mode and self.calibration.is_loaded:
            forces = self.calibration.voltages_to_forces(fsr_data, self._model_key)
            return float(forces[channel])
        return float(fsr_data[channel])

    def _foot_display_values(self, fsr_data: np.ndarray) -> np.ndarray:
        if self._use_pressure_mode and self.calibration.is_loaded:
            return self.calibration.voltages_to_forces(fsr_data, self._model_key)
        return fsr_data.copy()

    def _rebuild_adc_buffer_from_hub(self) -> None:
        fsr_data, fsr_stamp, fsr_ok, _, _, _ = self.hub.snapshot()
        if not fsr_ok:
            return
        self.adc_t_buf.clear()
        self.adc_v_buf.clear()
        if self._t_origin is not None and fsr_stamp >= self._t_origin:
            self.adc_t_buf.append(self._rel_time(fsr_stamp))
            self.adc_v_buf.append(self._fsr_display_value(fsr_data, self.fsr_channel))
        self._update_plot()

    def _rel_time(self, stamp: float) -> float:
        if self._t_origin is None:
            self._t_origin = stamp
        return stamp - self._t_origin

    def _window_bounds(self) -> tuple[float, float]:
        if self._t_origin is None:
            return 0.0, PLOT_WINDOW_S
        t_now = time.time() - self._t_origin
        win_end = max(PLOT_WINDOW_S, t_now)
        return win_end - PLOT_WINDOW_S, win_end

    def _series_for_window(
        self,
        t_buf: deque[float],
        v_buf: deque[float],
        win_start: float,
        win_end: float,
    ) -> tuple[list[float], list[float]]:
        """仅返回窗口内真实采样点，无数据则不绘制。"""
        xs: list[float] = []
        ys: list[float] = []
        for t, v in zip(t_buf, v_buf):
            if win_start <= t <= win_end:
                xs.append(t)
                ys.append(v)
        return xs, ys

    def _apply_y_range(self, viewbox: pg.ViewBox, values: list[float]) -> None:
        """按当前窗口内真实采样值自动缩放 Y 轴。"""
        if not values:
            viewbox.setYRange(-0.01, 0.01, padding=0)
            return
        lo, hi = min(values), max(values)
        if lo == hi:
            pad = max(abs(lo) * 0.1, 0.01)
            viewbox.setYRange(lo - pad, hi + pad, padding=0)
            return
        margin = (hi - lo) * 0.1
        viewbox.setYRange(lo - margin, hi + margin, padding=0)

    def _update_plot(self) -> None:
        win_start, win_end = self._window_bounds()
        adc_x, adc_y = self._series_for_window(
            self.adc_t_buf, self.adc_v_buf, win_start, win_end
        )
        force_x, force_y = self._series_for_window(
            self.force_interp_t_buf, self.force_interp_v_buf, win_start, win_end
        )
        self.adc_curve.setData(adc_x, adc_y)
        self.force_curve.setData(force_x, force_y)
        self.plot.setXRange(win_start, win_end, padding=0)
        self._apply_y_range(self.plot.vb, adc_y)
        self._apply_y_range(self.force_view, force_y)

    def _on_fsr_changed(self, index: int):
        self.fsr_channel = self.fsr_combo.itemData(index)
        self._clear_buffers()

    def _clear_buffers(self):
        self.adc_t_buf.clear()
        self.adc_v_buf.clear()
        self.force_interp_t_buf.clear()
        self.force_interp_v_buf.clear()
        self.pipeline.clear_anchors()
        self._t_origin = None
        self._last_fsr_stamp = -1.0
        self._force_interp_now = float("nan")
        self.plot.setXRange(0, PLOT_WINDOW_S, padding=0)
        self._update_plot()

    def _on_start_record(self):
        path = self.pipeline.request_start_record()
        self.start_record_btn.setEnabled(False)
        self.stop_record_btn.setEnabled(True)
        print(f"录制文件: record/{path.name}")

    def _on_stop_record(self):
        count = self.pipeline.request_stop_record()
        self.start_record_btn.setEnabled(True)
        self.stop_record_btn.setEnabled(False)
        print(f"已保存 {count} 行")

    def _refresh(self):
        fsr_data, fsr_stamp, fsr_ok, _, force_stamp, force_ok = (
            self.hub.snapshot()
        )
        _, record_path, recording, row_count = self.pipeline.snapshot()

        data_changed = False
        if fsr_ok and fsr_stamp != self._last_fsr_stamp:
            self.adc_t_buf.append(self._rel_time(fsr_stamp))
            self.adc_v_buf.append(self._fsr_display_value(fsr_data, self.fsr_channel))
            self._last_fsr_stamp = fsr_stamp
            data_changed = True

        ui_stamp = time.time()
        force_interp = self.pipeline.interp_force(ui_stamp)
        if force_interp is not None:
            self.force_interp_t_buf.append(self._rel_time(ui_stamp))
            self.force_interp_v_buf.append(force_interp)
            self._force_interp_now = force_interp
            data_changed = True

        if fsr_ok:
            foot_display = self._foot_display_values(fsr_data)
            self.foot_panel.update_feet(
                foot_display,
                (foot_display[:16], foot_display[16:32]),
            )

        self._update_plot()
        if data_changed:
            self._ui_fps_count += 1

        now = time.monotonic()
        if now - self._last_ui_fps_report >= 1.0:
            elapsed = now - self._last_ui_fps_report
            self._ui_fps = self._ui_fps_count / elapsed if elapsed > 0 else 0.0
            self._ui_fps_count = 0
            self._last_ui_fps_report = now

        if now - self._last_status_update >= STATUS_UPDATE_INTERVAL_S:
            fsr_state = "已连接" if fsr_ok else "未连接"
            force_state = "已连接" if force_ok else "未连接"
            adc_now = fsr_data[self.fsr_channel] if fsr_ok else float("nan")
            est_now = (
                self._fsr_display_value(fsr_data, self.fsr_channel)
                if fsr_ok
                else float("nan")
            )
            force_now = (
                self._force_interp_now
                if np.isfinite(self._force_interp_now)
                else float("nan")
            )
            skew_ms = (
                abs(fsr_stamp - force_stamp) * 1000.0
                if fsr_ok and force_ok
                else float("nan")
            )
            calib_state = "已加载" if self.calibration.is_loaded else "未加载"
            model_label = self.model_combo.currentText()
            ch_fit_ok = (
                self.calibration.channel_model_ok(self.fsr_channel, self._model_key)
                if self.calibration.is_loaded
                else False
            )
            parts = [
                f"FSR TCP ({FSR_HOST}:{FSR_PORT}): {fsr_state}",
                f"压力 WS ({FORCE_WS_URL}): {force_state}",
                f"标定 YAML: {calib_state}",
                f"模型: {model_label}" + (" ✓" if ch_fit_ok else " ✗"),
                f"当前 FSR[{self.fsr_channel}] ADC={adc_now:.4f} V",
            ]
            if self._use_pressure_mode:
                parts.append(
                    f"估算压力={est_now:.1f} N"
                    if np.isfinite(est_now)
                    else "估算压力=—"
                )
            parts.extend([
                f"参考压力={force_now:.3f} N",
                f"时间偏差={skew_ms:.0f} ms" if fsr_ok and force_ok else "时间偏差=—",
                f"UI FPS={self._ui_fps:.1f}",
            ])
            if recording and record_path is not None:
                parts.append(
                    f"录制中 → record/{record_path.name} ({row_count} 行)"
                )
            self.status_label.setText("  |  ".join(parts))
            self._last_status_update = now

    def closeEvent(self, event):
        self.timer.stop()
        _, record_path, recording, _ = self.pipeline.snapshot()
        if recording:
            count = self.pipeline.request_stop_record()
            if record_path is not None:
                print(f"窗口关闭，录制已自动保存: {record_path} ({count} 行)")
        self._stop.set()
        self.pipeline.shutdown()
        event.accept()


def main():
    app = pg.mkQApp("FsrCalibrate")
    win = FsrCalibrateApp()
    app.aboutToQuit.connect(win.close)
    win.show()
    app.exec_()


if __name__ == "__main__":
    main()
