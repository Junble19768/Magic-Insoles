#!/usr/bin/env python3
"""
FSR 标定拟合（逐 CSV 自动选通道）

目标：
  - 扫描 record 目录下全部 CSV（按文件名排序）
  - 每个 CSV 自动选取电压变化幅值最大的 FSR 通道作为标定点
  - 在有效压力区间内筛选施力变化最剧烈阶段的采样点，再分箱聚合
  - 对该通道的 (压力|F|, FSR 阻值 R) 用指数 / 幂函数 / 倒数三种模型各自拟合
  - 输出固定 4 列、行数自适应的子图 PNG，每格独立三条拟合曲线

分压反算：
  Vcc -- FSR -- 节点 -- R_fixed -- GND
  fsr_xx 为 R_fixed 35k 两端电压（节点到地的电压），由：
    R_fsr = R_fixed * (Vcc - V) / V
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit


# ── 硬件参数 ───────────────────────────────────────────────
VCC = 3.3  # ADC 参考电压 (V)
R_FIXED_OHM = 35_000.0  # 固定电阻 (Ω)

# ── 选择/过滤参数 ──────────────────────────────────────────
FORCE_COL_DEFAULT = "force_ch0"
FORCE_BIN_N_DEFAULT = 0.5  # 压力分箱宽度 (N)
FORCE_MIN_N_DEFAULT = 0.5  # 过滤掉低压噪声
FORCE_MAX_N_DEFAULT = 150.0  # 过滤掉无效/异常值
DYNAMIC_WINDOW_DEFAULT = 7  # 施力变化率滑动窗口（采样点数）
DYNAMIC_PERCENTILE_DEFAULT = 50.0  # 保留 |dF/dt| 处于该百分位以上的样本

FSR_CHANNEL_COUNT = 32
PLOT_COLS = 4


def voltage_to_fsr_resistance(voltage_v: np.ndarray) -> np.ndarray:
    """由固定电阻分压电压反算 FSR 阻值 (Ω)。"""
    v = np.clip(voltage_v, 1e-6, VCC - 1e-6)
    return R_FIXED_OHM * (VCC - v) / v


def r_squared(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    if ss_tot == 0:
        return float("nan")
    return 1.0 - ss_res / ss_tot


# ── 拟合模型（R = a*...，其中 R 单位 Ω，F 单位 N） ─────────────────
def model_exponential(force: np.ndarray, a: float, b: float) -> np.ndarray:
    return a * np.exp(b * force)


def model_power(force: np.ndarray, a: float, b: float) -> np.ndarray:
    return a * np.power(force, b)


def model_inverse(force: np.ndarray, a: float, c: float) -> np.ndarray:
    return a / force + c


@dataclass(frozen=True)
class FitResult:
    params: np.ndarray
    r2: float
    ok: bool


def safe_fit_curve(
    x: np.ndarray,
    y: np.ndarray,
    model_func,
    p0: tuple[float, ...],
    bounds: tuple[list[float], list[float]] | None,
) -> FitResult:
    """curve_fit 包一层错误处理，失败返回 ok=False。"""
    try:
        popt, _pcov = curve_fit(
            model_func,
            x,
            y,
            p0=p0,
            bounds=bounds if bounds is not None else (-np.inf, np.inf),
            maxfev=25_000,
        )
        y_hat = model_func(x, *popt)
        return FitResult(params=np.asarray(popt, dtype=float), r2=r_squared(y, y_hat), ok=True)
    except Exception:
        # 拟合失败（数据量少/数值不稳定）时不要让脚本中断
        return FitResult(params=np.full(len(p0), np.nan, dtype=float), r2=float("nan"), ok=False)


def aggregate_by_force_bins(
    force_abs_n: np.ndarray,
    resistance_ohm: np.ndarray,
    force_bin_n: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    将同一压力分箱内的数据聚合为中位数：
      - 输出 force_bins：每箱的中位压力（N）
      - 输出 res_bins：每箱的中位阻值（B, 32）
    """
    bins = np.floor(force_abs_n / force_bin_n) * force_bin_n
    # 稳定：只取出现过的箱
    unique_bins = np.unique(bins)
    unique_bins.sort()
    b = len(unique_bins)

    force_bins = np.empty(b, dtype=float)
    res_bins = np.empty((b, resistance_ohm.shape[1]), dtype=float)

    for bi, bval in enumerate(unique_bins):
        mask = bins == bval
        if not np.any(mask):
            force_bins[bi] = np.nan
            res_bins[bi, :] = np.nan
            continue
        force_bins[bi] = float(np.median(force_abs_n[mask]))
        res_bins[bi, :] = np.median(resistance_ohm[mask, :], axis=0)

    valid = np.isfinite(force_bins) & (force_bins > 0)
    force_bins = force_bins[valid]
    res_bins = res_bins[valid, :]
    return force_bins, res_bins


def select_dynamic_force_samples(
    force_abs_n: np.ndarray,
    window: int,
    percentile: float,
) -> np.ndarray:
    """
    在单个 CSV 内保留施力变化最剧烈阶段的采样点。

    用 |dF/dt| 的滑动均值衡量变化剧烈程度，保留高于给定百分位的样本。
    """
    n = force_abs_n.size
    if n < max(window, 3):
        return np.ones(n, dtype=bool)

    delta_force = np.abs(np.diff(force_abs_n, prepend=force_abs_n[0]))
    kernel = np.ones(window, dtype=float) / float(window)
    dynamic_score = np.convolve(delta_force, kernel, mode="same")
    threshold = float(np.percentile(dynamic_score, percentile))
    return dynamic_score >= threshold


def fit_three_models(force: np.ndarray, resistance_ohm: np.ndarray) -> dict[str, FitResult]:
    """对单个通道数据分别拟合三种模型。"""
    # 过滤数值
    mask = np.isfinite(force) & np.isfinite(resistance_ohm) & (force > 1e-6)
    x = force[mask]
    y = resistance_ohm[mask]
    if x.size < 3:
        return {
            "指数": FitResult(params=np.array([np.nan, np.nan]), r2=float("nan"), ok=False),
            "幂函数": FitResult(params=np.array([np.nan, np.nan]), r2=float("nan"), ok=False),
            "倒数": FitResult(params=np.array([np.nan, np.nan]), r2=float("nan"), ok=False),
        }

    y_max = float(np.nanmax(y))
    y_min = float(np.nanmin(y))
    x_min = float(np.nanmin(x))

    # 指数：b 通常为负（阻值随压力增大而下降），但允许边界外的失败时也捕获
    exp_res = safe_fit_curve(
        x,
        y,
        model_exponential,
        p0=(y_max, -0.05),
        bounds=([0.0, -10.0], [np.inf, 0.0]),
    )
    # 幂函数：F^b，b 可能为负
    pow_res = safe_fit_curve(
        x,
        y,
        model_power,
        p0=(y_max, -1.0),
        bounds=([0.0, -10.0], [np.inf, 10.0]),
    )
    # 倒数：R = a/F + c
    inv_res = safe_fit_curve(
        x,
        y,
        model_inverse,
        p0=(y_max * x_min, y_min),
        bounds=([0.0, -np.inf], [np.inf, np.inf]),
    )

    return {"指数": exp_res, "幂函数": pow_res, "倒数": inv_res}


def plot_point_subplot(
    ax: plt.Axes,
    force_bins: np.ndarray,
    res_bins_ohm: np.ndarray,
    fsr_idx: int,
    csv_name: str,
) -> None:
    """在单个子图绘制散点 + 三模型拟合曲线。"""
    ax.scatter(force_bins, res_bins_ohm / 1000.0, s=10, alpha=0.9, edgecolors="white", linewidths=0.3)

    fits = fit_three_models(force_bins, res_bins_ohm)
    force_line = np.linspace(float(np.nanmin(force_bins)), float(np.nanmax(force_bins)), 250)

    colors = {"指数": "#E74C3C", "幂函数": "#3498DB", "倒数": "#27AE60"}
    for name in ["指数", "幂函数", "倒数"]:
        fit = fits[name]
        if not fit.ok:
            continue
        if name == "指数":
            curve = model_exponential(force_line, *fit.params)
        elif name == "幂函数":
            curve = model_power(force_line, *fit.params)
        else:
            curve = model_inverse(force_line, *fit.params)
        ax.plot(force_line, curve / 1000.0, color=colors[name], linewidth=1.6)

    r2_text = []
    for name in ["指数", "幂函数", "倒数"]:
        r2_text.append(f"{name}:{fits[name].r2:.3f}" if np.isfinite(fits[name].r2) else f"{name}:nan")

    ax.text(
        0.02,
        0.98,
        "\n".join(r2_text),
        transform=ax.transAxes,
        fontsize=8,
        va="top",
        ha="left",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85, edgecolor="#CCCCCC"),
    )

    ax.grid(True, alpha=0.25)
    ax.set_title(f"fsr_{fsr_idx:02d}\n{csv_name}", fontsize=9)


def load_csv_numeric(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, skipinitialspace=True)
    df.columns = df.columns.str.strip()
    return df


def select_active_fsr_channel(
    df: pd.DataFrame,
    force_col: str,
    force_min_n: float,
    force_max_n: float,
) -> tuple[int, float]:
    """
    在有效压力区间内，选取电压变化幅值 (max - min) 最大的 FSR 通道。

    返回 (通道号, 幅值 V)。
    """
    if force_col not in df.columns:
        raise KeyError(f"CSV 缺少列: {force_col}")

    force = pd.to_numeric(df[force_col], errors="coerce").to_numpy()
    force_abs = np.abs(force)
    valid = (
        np.isfinite(force_abs)
        & (force_abs >= force_min_n)
        & (force_abs < force_max_n)
    )
    if not np.any(valid):
        raise ValueError("过滤后无有效压力数据，无法选择 FSR 通道")

    best_idx = -1
    best_swing = -1.0
    for ch in range(FSR_CHANNEL_COUNT):
        col = f"fsr_{ch:02d}"
        if col not in df.columns:
            continue
        voltage = pd.to_numeric(df[col], errors="coerce").to_numpy()
        mask = valid & np.isfinite(voltage)
        if not np.any(mask):
            continue
        v = voltage[mask]
        swing = float(np.max(v) - np.min(v))
        if swing > best_swing:
            best_swing = swing
            best_idx = ch

    if best_idx < 0:
        raise ValueError("未找到有效 FSR 通道数据")
    return best_idx, best_swing


def compute_force_and_resistance_for_point(
    df: pd.DataFrame,
    fsr_idx: int,
    force_col: str,
    force_min_n: float,
    force_max_n: float,
    dynamic_window: int,
    dynamic_percentile: float,
) -> tuple[np.ndarray, np.ndarray]:
    fsr_col = f"fsr_{fsr_idx:02d}"
    if force_col not in df.columns:
        raise KeyError(f"CSV 缺少列: {force_col}")
    if fsr_col not in df.columns:
        raise KeyError(f"CSV 缺少列: {fsr_col}")

    force = pd.to_numeric(df[force_col], errors="coerce").to_numpy()
    voltage = pd.to_numeric(df[fsr_col], errors="coerce").to_numpy()
    force_abs = np.abs(force)

    valid = (
        np.isfinite(force_abs)
        & np.isfinite(voltage)
        & (force_abs >= force_min_n)
        & (force_abs < force_max_n)
    )
    force_abs = force_abs[valid]
    voltage = voltage[valid]
    if force_abs.size == 0:
        raise ValueError("过滤后无有效压力数据，请检查 FORCE_MIN/FORCE_MAX")

    dynamic_mask = select_dynamic_force_samples(
        force_abs,
        window=dynamic_window,
        percentile=dynamic_percentile,
    )
    force_abs = force_abs[dynamic_mask]
    voltage = voltage[dynamic_mask]
    if force_abs.size < 3:
        raise ValueError("施力变化筛选后样本不足，请降低 dynamic-percentile")

    resistance = voltage_to_fsr_resistance(voltage)
    return force_abs, resistance


def main() -> None:
    parser = argparse.ArgumentParser(description="FSR 标定：逐 CSV 自动选通道，三模型拟合并导出 PNG")
    parser.add_argument(
        "--record-dir",
        default=str(Path(__file__).resolve().parent / "record"),
        help="record 目录",
    )
    parser.add_argument("--force-col", default=FORCE_COL_DEFAULT, help="压力列名（例如 force_ch0）")
    parser.add_argument("--bin-n", type=float, default=FORCE_BIN_N_DEFAULT, help="压力分箱宽度 N")
    parser.add_argument("--force-min", type=float, default=FORCE_MIN_N_DEFAULT, help="压力最小过滤 N")
    parser.add_argument("--force-max", type=float, default=FORCE_MAX_N_DEFAULT, help="压力最大过滤 N")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="仅处理前 N 个 CSV（调试用，默认处理全部）",
    )
    parser.add_argument(
        "--dynamic-window",
        type=int,
        default=DYNAMIC_WINDOW_DEFAULT,
        help="施力变化率滑动窗口（采样点数）",
    )
    parser.add_argument(
        "--dynamic-percentile",
        type=float,
        default=DYNAMIC_PERCENTILE_DEFAULT,
        help="保留 |dF/dt| 高于该百分位的样本（0~100）",
    )
    parser.add_argument("--output", default="", help="输出 PNG 路径（默认 record/fsr_fit.png）")
    parser.add_argument("--show", action="store_true", help="显示弹窗")
    args = parser.parse_args()

    record_dir = Path(args.record_dir)
    csv_files = sorted(record_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"未找到 CSV: {record_dir}")

    if args.limit is not None:
        csv_files = csv_files[: args.limit]

    out_path = Path(args.output) if args.output else (record_dir / "fsr_fit.png")

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    ncols = PLOT_COLS
    nrows = max(1, -(-len(csv_files) // ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(18, 4.5 * nrows), constrained_layout=False)
    axes_flat = np.atleast_1d(axes).flatten()

    for grid_idx, csv_path in enumerate(csv_files):
        ax = axes_flat[grid_idx]
        row, col = divmod(grid_idx, ncols)
        fsr_idx = -1
        try:
            df = load_csv_numeric(csv_path)
            fsr_idx, swing_v = select_active_fsr_channel(
                df,
                force_col=args.force_col,
                force_min_n=args.force_min,
                force_max_n=args.force_max,
            )
            print(f"{csv_path.name}: 选中 fsr_{fsr_idx:02d} (ΔV={swing_v:.4f} V)")
            force_abs, resistance = compute_force_and_resistance_for_point(
                df,
                fsr_idx=fsr_idx,
                force_col=args.force_col,
                force_min_n=args.force_min,
                force_max_n=args.force_max,
                dynamic_window=args.dynamic_window,
                dynamic_percentile=args.dynamic_percentile,
            )
            force_bins, res_bins = aggregate_by_force_bins(
                force_abs,
                resistance.reshape(-1, 1),
                force_bin_n=args.bin_n,
            )
            res_for_channel = res_bins[:, 0]

            plot_point_subplot(
                ax=ax,
                force_bins=force_bins,
                res_bins_ohm=res_for_channel,
                fsr_idx=fsr_idx,
                csv_name=csv_path.name,
            )

            ax.set_xlabel("F(N)" if row == nrows - 1 else "")
            ax.set_ylabel("R(kΩ)" if col == 0 else "")
        except Exception as e:
            ax.axis("off")
            fsr_label = f"fsr_{fsr_idx:02d}" if fsr_idx >= 0 else "fsr_??"
            ax.text(
                0.5,
                0.5,
                f"Fail\n{fsr_label}\n{csv_path.name}\n{e}",
                ha="center",
                va="center",
                fontsize=8,
            )

    for j in range(len(csv_files), len(axes_flat)):
        axes_flat[j].axis("off")

    fig.suptitle(
        f"FSR Pressure-Resistance Fit (R_fixed={R_FIXED_OHM/1000:.0f}kΩ, Vcc={VCC}V, "
        f"bin={args.bin_n}N, dynamic>={args.dynamic_percentile:.0f}%)\n"
        f"auto channel per CSV | {len(csv_files)} file(s) | source_dir={record_dir.name}",
        fontsize=14,
    )
    fig.tight_layout(rect=[0, 0.03, 1, 0.96])
    fig.savefig(out_path, dpi=180)
    print(f"已保存: {out_path}")

    if args.show:
        plt.show()
    else:
        plt.close(fig)


if __name__ == "__main__":
    main()

