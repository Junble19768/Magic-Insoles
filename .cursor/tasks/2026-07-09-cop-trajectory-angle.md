# Task: COP 轨迹直线拟合与竖直夹角

- **日期**：2026-07-09
- **状态**：已完成
- **关联**：`tools/win-datacap/fsr_visualize.py`、`fsr_calibrate/cop.py`

## Problem / 目标

在 `fsr_visualize.py` 压力解算模式下，统计左右脚各自 COP 轨迹（滑动窗口 10s），对轨迹做直线拟合，计算拟合线与竖直方向（跟→趾，plot +Y）的夹角，并在热力图与状态栏展示。

## 核心思路

- 纯函数放 `cop.py`：`CopTrajectoryTracker` + SVD 直线拟合 + `atan2(|dx|,|dy|)` 角度。
- `heatmap.py` 叠加轨迹折线与拟合虚线；`app_visualize.py` 传 `fsr_stamp` 并在状态栏显示 θ。
- 滑动窗口基于设备 `fsr_stamp` 裁剪；切回 ADC 模式清空缓冲。

## 受影响的文件 / 模块

- `tools/win-datacap/fsr_calibrate/cop.py` — 轨迹缓冲、拟合、角度
- `tools/win-datacap/fsr_calibrate/config.py` — `COP_TRAJECTORY_WINDOW_S`
- `tools/win-datacap/fsr_calibrate/heatmap.py` — 轨迹/拟合线绘制
- `tools/win-datacap/fsr_calibrate/app_visualize.py` — stamp 传递、状态栏
- `tools/win-datacap/fsr_calibrate/test_cop.py` — 单元测试

## 分步计划

- [x] Step 1: `cop.py` 数学层
- [x] Step 2: `config.py` 常量
- [x] Step 3: `heatmap.py` 可视化
- [x] Step 4: `app_visualize.py` 状态栏
- [x] Step 5: `test_cop.py` 测试

## Debug Notes

## Lessons Learned
