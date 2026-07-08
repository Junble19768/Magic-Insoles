from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml


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
            with open(path, encoding="utf-8") as file:
                payload = yaml.safe_load(file)
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
            channel = int(ch)
            self.channel_fits[channel] = {}
            for model_key in ("exponential", "power", "inverse"):
                block = fits.get(model_key, {})
                if not isinstance(block, dict):
                    self.channel_fits[channel][model_key] = ChannelFit(ok=False)
                    continue
                ok = bool(block.get("ok", False))
                params_raw = block.get("params")
                params: dict[str, float] = {}
                if ok and isinstance(params_raw, dict):
                    params = {k: float(v) for k, v in params_raw.items()}
                    ok = all(np.isfinite(v) for v in params.values())
                self.channel_fits[channel][model_key] = ChannelFit(ok=ok, params=params)

        if not self.channel_fits:
            self.load_error = "YAML 中无有效通道拟合条目"
            return

        self.loaded_path = path
        print(f"标定 YAML 已加载: {path} ({len(self.channel_fits)} 通道)")

    def voltage_to_resistance(self, voltage_v: np.ndarray) -> np.ndarray:
        v = np.clip(voltage_v, 1e-6, self.vcc_v - 1e-6)
        return self.r_fixed_ohm * (self.vcc_v - v) / v

    def resistance_to_force(self, resistance_ohm: float, channel: int, model_key: str) -> float:
        if not np.isfinite(resistance_ohm) or resistance_ohm <= 0:
            return float("nan")
        fit = self.channel_fits.get(channel, {}).get(model_key)
        if fit is None or not fit.ok:
            return float("nan")

        params = fit.params
        try:
            if model_key == "exponential":
                a, b = params["a"], params["b"]
                if a <= 0 or b == 0:
                    return float("nan")
                ratio = resistance_ohm / a
                if ratio <= 0:
                    return float("nan")
                force = float(np.log(ratio) / b)
            elif model_key == "power":
                a, b = params["a"], params["b"]
                if a <= 0 or b == 0:
                    return float("nan")
                ratio = resistance_ohm / a
                if ratio <= 0:
                    return float("nan")
                force = float(np.power(ratio, 1.0 / b))
            elif model_key == "inverse":
                a, c = params["a"], params["c"]
                denom = resistance_ohm - c
                if abs(denom) < 1e-9:
                    return float("nan")
                force = float(a / denom)
            else:
                return float("nan")
            return force if np.isfinite(force) and force > 0 else float("nan")
        except (KeyError, ValueError, OverflowError):
            return float("nan")

    def voltages_to_forces(self, voltages: np.ndarray, model_key: str) -> np.ndarray:
        resistances = self.voltage_to_resistance(voltages)
        out = np.full(32, np.nan, dtype=float)
        for channel in range(32):
            out[channel] = self.resistance_to_force(float(resistances[channel]), channel, model_key)
        return out

    def channel_model_ok(self, channel: int, model_key: str) -> bool:
        fit = self.channel_fits.get(channel, {}).get(model_key)
        return fit is not None and fit.ok
