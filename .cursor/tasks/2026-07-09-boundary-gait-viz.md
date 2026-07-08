# Task: Boundary 脚型 + 步态轨迹密度可视化

- **日期**：2026-07-09
- **状态**：已完成
- **关联**：`tools/win-datacap/fsr_visualize.py`、Plan boundary_gait_viz

## Problem / 目标

前端脚部可视化使用 4×4 占位网格，与 win-datacap boundary 脚型不一致；步态分析页需展示全天 COP 轨迹密度热力叠加。

## 核心思路

预导出 boundary masks/centroids → 前端 Canvas 合成三层（压力底图 + 轨迹 splat + 折线/拟合）→ 后端 COP 坐标对齐。

## 受影响的文件 / 模块

- `tools/scripts/export_boundary_assets.py`
- `frontend/src/viz/boundary/*`
- `frontend/src/viz/FootAnalysisCanvas.tsx`
- `backend_prod/services/feature.py`

## 分步计划

- [x] Step 1: export_boundary_assets.py
- [x] Step 2: frontend boundary module
- [x] Step 3: COP align + FootAnalysisCanvas
- [x] Step 4: pages + tests

## Lessons Learned

- 浏览器侧用预导出 RLE masks 比移植 adaptive B-spline 更稳；COP/热力图共用 plot 坐标 (width=324, height=132)。
