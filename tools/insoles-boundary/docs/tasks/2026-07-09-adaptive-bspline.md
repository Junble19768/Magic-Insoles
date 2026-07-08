# Task: 自适应布点 B-spline + 边界距离优化

- **日期**：2026-07-09
- **状态**：已完成
- **关联**：[adaptive_b-spline_fitting plan](../plans/adaptive_b-spline_fitting_e2dd72d4.plan.md)

## Problem / 目标

`masks_scaled` 在 uniform B-spline + IOU 优化、CP 预算 20/40 下 mean IOU 仅 ~0.92，边界视觉偏差明显。需新增自适应布点拟合，以对称平均边界距离为优化目标。

## 核心思路

- 误差驱动 knot 插入：每轮在 target 轮廓最大误差点插入 `knot_param`，直至 `max_cp`。
- 非均匀周期三次 B-spline：`lstsq` 拟合，knot vector 由 `knot_params` 推导。
- 优化目标默认 `boundary_mean`；报告附带 `hausdorff_px` 与 `iou`。
- 保留 `uniform` 路径，`--fit-mode uniform` 可复现旧行为。

## 受影响的文件 / 模块

- `src/insoles/boundary_metrics.py` — 新增
- `src/insoles/adaptive_bspline.py` — 新增
- `src/insoles/contour.py` — `auto_select_fit_adaptive`
- `src/insoles/schema.py` — `FitMetadata` 扩展、`knot_params`
- `scripts/process_masks.py` — `--fit-mode` / `--metric`
- `contours_scaled_adaptive/`、`verification_scaled_adaptive/`、`reports/boundary_summary_scaled.json`

## 分步计划

- [x] Step 1: `boundary_metrics.py`
- [x] Step 2: `adaptive_bspline.py`
- [x] Step 3: `auto_select_fit_adaptive` + knot 插入
- [x] Step 4: schema 扩展与渲染分发
- [x] Step 5: CLI + `masks_scaled` 验收
- [x] Step 6: 本任务文档与 memory 更新

## Debug Notes

- 2026-07-09 单点 worst-index 插入在 12 CP 后易失败；改为 top-10 候选点后 base 可用至 32 CP，mean boundary 从 0.40 降至 0.35 px。

## Lessons Learned

- scaled 掩码为原图 **10× 缩小**（`dimension_scale=0.1`），`pixel_scale_cm` 应为 `0.00855 / 0.1 = 0.0855`。
- 汇总记录见 `reports/scaled_record.json`（uniform + adaptive 对比一张表）。
- **外部集成交付物**：`reports/render_payload.json`（`python scripts/export_render_payload.py`）。
- 在 CP 预算内优化 `boundary_mean` 时，算法会倾向较少 CP（10–12），需允许多候选插入点才能吃满预算。
- `masks_scaled` 对比：uniform mean IOU 0.924 vs adaptive 0.914；adaptive mean boundary 0.35 px、mean Hausdorff 1.79 px。
- 边界距离优化与 IOU 不完全一致；验收应同时看 verification diff 与 boundary 指标。

## 验收对比（masks_scaled, CP 20/40）

| 指标 | uniform_bspline | adaptive_bspline |
|------|-----------------|------------------|
| mean IOU | 0.924 | 0.914 |
| mean boundary | — | 0.352 px |
| mean Hausdorff | — | 1.790 px |
| mean CP | 17.5 | ~11–17（按 mask 自适应选取） |
| max CP | 31 | 32 |
