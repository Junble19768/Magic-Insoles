# Active Context（当前焦点）

> 最近更新：2026-07-09（修正 masks 重跑，已同步至 tools/）

## 当前焦点

**仓库最终交付物**：[`reports/render_payload.json`](../reports/render_payload.json) — 单一紧凑文件，包含在外部（网页/嵌入式）重绘全部 17 个区域所需的全部信息。

```bash
python scripts/export_render_payload.py
```

**数据源**：`masks/`（修正后的 17 张全分辨率掩码）→ 全分辨率 adaptive 拟合 → OBB 裁切 + **CW90** → `masks_scaled/` → adaptive 拟合。

## 近期变更

- 2026-07-09 **修正 masks 全 pipeline 重跑**（`masks/` → OBB + **CW90** → scale → adaptive）
  - `render_payload.json`：画布 **132×324**，`pixel_scale_cm=0.0855`，17 区域
  - OBB 输出经顺时针 90° 旋转（`reframe_by_base_obb.py --rotate-cw90`，默认开启）
  - region 1/2 几何已独立（旧版 region 2 曾错误 `dup:"1"`）
  - adaptive 验收：mean boundary **0.290 px**，mean IOU 0.917
- 2026-07-09 从 `ignored/insoles-boundary` 同步 CW90 代码至 `tools/insoles-boundary`
- 2026-07-09 新增 `src/insoles/render_payload.py`、`scripts/export_render_payload.py`（含 runtime 渲染，供 `fsr_calibrate` 使用）
- 2026-07-07 OBB 重映射与左下角坐标系（`contours_bl/`，尚未并入 render payload）

## 下一步

- [ ] 外部消费方实现 `adaptive_bspline` 采样器（或提供 JS/C 参考实现）
- [ ] 视需要将 `contours_bl` 坐标系变换烘焙进 render payload
- [ ] 压力热力图：region id → 物理坐标映射（`fsr_calibrate` 已接入 render payload）

## 进行中的任务 Plan

- [2026-07-09-mask-fix-rerun.md](../tasks/2026-07-09-mask-fix-rerun.md)（已完成）
- [2026-07-09-adaptive-bspline.md](../tasks/2026-07-09-adaptive-bspline.md)（已完成）

## 待决问题 / 阻塞

- 无
