#!/usr/bin/env python3
"""
Legacy sample: FSR 标定曲线拟合（单通道）。

当前推荐使用：
- `plot_fsr_grid_fit.py` 做全通道拟合导出；
- `fsr_calibrate.py` 做实时标定/可视化。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

VCC = 3.3
R_FIXED_OHM = 35_000.0

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "record" / "20260706_212154.csv"
FSR_COL = "fsr_00"
FORCE_COL = "force_ch0"
FORCE_BIN_N = 0.5


def voltage_to_fsr_resistance(voltage_v: np.ndarray) -> np.ndarray:
    v = np.clip(voltage_v, 1e-6, VCC - 1e-6)
    return R_FIXED_OHM * (VCC - v) / v


def load_and_aggregate(csv_path: Path) -> tuple[np.ndarray, np.ndarray]:
    df = pd.read_csv(csv_path, skipinitialspace=True)
    df.columns = df.columns.str.strip()
    df = df[[FSR_COL, FORCE_COL]].apply(pd.to_numeric, errors="coerce").dropna()
    force = df[FORCE_COL].to_numpy()
    voltage = df[FSR_COL].to_numpy()
    resistance = voltage_to_fsr_resistance(voltage)
    force_mag = np.abs(force)
    mask = (force_mag >= 0.5) & (force_mag < 150.0)
    force_mag = force_mag[mask]
    resistance = resistance[mask]
    bins = np.floor(force_mag / FORCE_BIN_N) * FORCE_BIN_N
    agg = (
        pd.DataFrame({"force": force_mag, "resistance": resistance, "bin": bins})
        .groupby("bin", as_index=False)
        .median(numeric_only=True)
        .sort_values("force")
    )
    return agg["force"].to_numpy(), agg["resistance"].to_numpy()


def model_exponential(force: np.ndarray, a: float, b: float) -> np.ndarray:
    return a * np.exp(b * force)


def model_power(force: np.ndarray, a: float, b: float) -> np.ndarray:
    return a * np.power(force, b)


def model_inverse(force: np.ndarray, a: float, c: float) -> np.ndarray:
    return a / force + c


def r_squared(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return float("nan")
    return 1.0 - ss_res / ss_tot


def fit_curve(
    force: np.ndarray,
    resistance: np.ndarray,
    model_func,
    p0: tuple[float, ...],
    bounds: tuple[list[float], list[float]] | None = None,
) -> tuple[np.ndarray, float]:
    popt, _ = curve_fit(model_func, force, resistance, p0=p0, bounds=bounds, maxfev=20_000)
    y_hat = model_func(force, *popt)
    return popt, r_squared(resistance, y_hat)


def format_params(name: str, params: np.ndarray) -> str:
    if name == "exponential":
        a, b = params
        return f"R = {a:.3g}·exp({b:.4g}·F)"
    if name == "power":
        a, b = params
        return f"R = {a:.3g}·F^({b:.4g})"
    a, c = params
    return f"R = {a:.3g}/F + {c:.3g}"


def plot_fit(csv_path: Path, output_path: Path | None, show: bool) -> None:
    force, resistance = load_and_aggregate(csv_path)
    if len(force) < 3:
        raise ValueError("有效标定点不足，请检查 CSV 或分箱参数")

    force_line = np.linspace(force.min(), force.max(), 300)
    fits: list[tuple[str, str, np.ndarray, str]] = []

    p_exp, r2_exp = fit_curve(
        force,
        resistance,
        model_exponential,
        p0=(resistance.max(), -0.05),
        bounds=([0, -5], [np.inf, 0]),
    )
    fits.append(("指数", "#E74C3C", model_exponential(force_line, *p_exp), f"R²={r2_exp:.4f}"))

    p_pow, r2_pow = fit_curve(
        force,
        resistance,
        model_power,
        p0=(resistance.max(), -1.0),
        bounds=([0, -10], [np.inf, 0]),
    )
    fits.append(("幂函数", "#3498DB", model_power(force_line, *p_pow), f"R²={r2_pow:.4f}"))

    p_inv, r2_inv = fit_curve(
        force,
        resistance,
        model_inverse,
        p0=(resistance.max() * force.min(), resistance.min()),
        bounds=([0, 0], [np.inf, np.inf]),
    )
    fits.append(("倒数", "#27AE60", model_inverse(force_line, *p_inv), f"R²={r2_inv:.4f}"))

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(
        force,
        resistance / 1000,
        s=36,
        c="#2C3E50",
        alpha=0.85,
        edgecolors="white",
        linewidths=0.5,
        label="标定数据（分箱中位数）",
        zorder=3,
    )

    for label, color, curve, r2_text in fits:
        ax.plot(force_line, curve / 1000, color=color, linewidth=2, label=f"{label}  {r2_text}")

    ax.set_xlabel("参考压力 |F| (N)")
    ax.set_ylabel("FSR 阻值 (kΩ)")
    ax.set_title(
        f"fsr_00 压力-阻值标定  "
        f"(R_fixed={R_FIXED_OHM/1000:.0f} kΩ, Vcc={VCC} V)\n"
        f"数据: {csv_path.name}"
    )
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=9)

    eq_lines = [
        f"指数: {format_params('exponential', p_exp)}",
        f"幂函数: {format_params('power', p_pow)}",
        f"倒数: {format_params('inverse', p_inv)}",
    ]
    ax.text(
        0.98,
        0.98,
        "\n".join(eq_lines),
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85, edgecolor="#CCCCCC"),
    )

    fig.tight_layout()
    if output_path is None:
        output_path = csv_path.with_suffix(".fsr_fit.png")
    fig.savefig(output_path, dpi=150)
    print(f"图像已保存: {output_path}")
    print("\n拟合参数:")
    print(f"  指数   {format_params('exponential', p_exp)}  R2={r2_exp:.6f}")
    print(f"  幂函数 {format_params('power', p_pow)}  R2={r2_pow:.6f}")
    print(f"  倒数   {format_params('inverse', p_inv)}  R2={r2_inv:.6f}")

    if show:
        plt.show()
    else:
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="FSR 压力-阻值标定曲线拟合（legacy sample）")
    parser.add_argument("csv", nargs="?", default=str(DEFAULT_CSV), help="标定 CSV 路径")
    parser.add_argument("-o", "--output", help="输出 PNG 路径")
    parser.add_argument("--show", action="store_true", help="显示交互窗口")
    args = parser.parse_args()
    csv_path = Path(args.csv)
    output_path = Path(args.output) if args.output else None
    plot_fit(csv_path, output_path, show=args.show)


if __name__ == "__main__":
    main()
