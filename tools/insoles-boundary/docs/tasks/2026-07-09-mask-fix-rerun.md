# Task: 修正 masks 全 pipeline 重跑

- **日期**：2026-07-09
- **状态**：已完成
- **关联**：`tools/insoles-boundary/`；源项目 `ignored/insoles-boundary/`

## Problem / 目标

手动抠图得到的 `masks/` 中传感器区域标记有误（region 1 与 region 2 几何相同，payload 中 region 2 被标注为 `dup:"1"`）。修正 Photoshop 抠图后，需要：

1. 用修正掩码重跑完整 pipeline（含 OBB + CW90）
2. 将代码变更与结果同步到 `tools/insoles-boundary/`（父仓库可追踪副本）
3. 更新下游 `fsr_calibrate` 所依赖的 `render_payload.json`

## 核心思路

- 修正源：`ignored/insoles-boundary/ignored/masks/`（3072×4096）
- 新增 OBB 后 **顺时针 90° 旋转**（`--rotate-cw90`，默认 True）→ 竖版画布 1318×3244 → scaled 132×324
- 主线 5 阶段：全分辨率 adaptive → OBB+CW90 → scale → scaled adaptive → export payload
- 保留 `tools/` 版 `render_payload.py` 的 runtime 渲染函数（`fsr_calibrate` 依赖）

## 受影响的文件 / 模块

- `src/insoles/obb_transform.py` — 新增 `rotate_*` 函数
- `scripts/reframe_by_base_obb.py` — 新增 `--rotate-cw90`
- `masks/`、`contours/`、`masks_obb/`、`contours_obb/`、`masks_scaled/`、`contours_scaled_adaptive/`
- `reports/render_payload.json` 及全部验收报告
- `docs/PIPELINE.md`、`README.md`、`docs/memories/*`

## 分步计划

- [x] 从 `ignored/` 移植 CW90 代码
- [x] 复制修正掩码到 `tools/insoles-boundary/masks/`
- [x] 重跑 5 阶段 pipeline
- [x] 验收：132×324、region 2 无 dup、mean IOU ≈ 0.968（全分辨率）
- [x] 更新文档与父仓库 activeContext

## Debug Notes

- 2026-07-09 scaled adaptive 本次重跑 mean boundary=0.290 px（略优于 ignored 独立仓库记录的 0.349 px），属正常波动；画布尺寸与 region 几何与 ignored 一致。

## Lessons Learned

- OBB 横版画布（3272×1325）不适合下游竖版显示；CW90 后 1318×3244 → scaled 132×324 为正确交付尺寸。
- `tools/` 与 `ignored/` 分叉时，以 `ignored/` 数字记忆 + 重跑验收为准同步；`render_payload.py` 的 tools 独有扩展需手动合并而非整文件覆盖。
