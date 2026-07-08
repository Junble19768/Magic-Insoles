# Active Context（当前焦点）

> 最近更新：2026-07-09

## 当前焦点

**仓库最终交付物**：[`reports/render_payload.json`](../reports/render_payload.json) — 单一紧凑文件，包含在外部（网页/嵌入式）重绘全部 17 个区域所需的全部信息。

```bash
python scripts/export_render_payload.py
```

## 近期变更

- 2026-07-09 新增 `src/insoles/render_payload.py`、`scripts/export_render_payload.py`
- 2026-07-09 导出 `reports/render_payload.json`（schema `insoles.render_payload/v1`，~8KB）
- 2026-07-09 adaptive B-spline 拟合完成；`pixel_scale_cm=0.0855`（10× 缩小）
- 2026-07-07 OBB 重映射与左下角坐标系（`contours_bl/`，尚未并入 render payload）

## 下一步

- [ ] 外部消费方实现 `adaptive_bspline` 采样器（或提供 JS/C 参考实现）
- [ ] 视需要将 `contours_bl` 坐标系变换烘焙进 render payload
- [ ] 压力热力图：region id → 物理坐标映射

## 进行中的任务 Plan

- [2026-07-09-adaptive-bspline.md](../tasks/2026-07-09-adaptive-bspline.md)（已完成）

## 待决问题 / 阻塞

- 无
