# System Patterns（架构与关键决策）

> 系统怎么搭起来的、为什么这么搭。

## 架构总览

```mermaid
flowchart LR
    masks[masks PNG] --> scale[scale_masks.py]
    scale --> masks_scaled[masks_scaled]
    masks_scaled --> fit[process_masks.py adaptive]
    fit --> contours[contours_scaled_adaptive JSON]
    contours --> export[export_render_payload.py]
    export --> payload[render_payload.json]
    payload --> consumer[Web / Embedded]
```

**最终交付物**：`reports/render_payload.json`（`insoles.render_payload/v1`）

## 关键技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 轮廓表示 | 周期三次 B-spline | 平滑、存储小、易采样成多边形 |
| 拟合模式 | `adaptive_bspline` | 误差驱动 knot 插入，同 CP 预算边界更贴 |
| 优化目标 | `boundary_mean` | 比 IOU 更贴近视觉边界偏差 |
| 缩放策略 | 10× 缩小 + 最近邻 | 减小数据量；`pixel_scale_cm` 同比放大 |
| 外部交换格式 | 单文件 render payload | 复制即用，不依赖仓库内多目录 JSON |

## render_payload 结构（v1）

| 字段 | 含义 |
|------|------|
| `schema` | `insoles.render_payload/v1` |
| `coordinate_system` | 左上原点，x 右、y 下，单位 px |
| `canvas` | `width`, `height`, `pixel_scale_cm` |
| `spline` | `type`, `degree`, `eval_n`, `closed` |
| `regions[]` | `id`, `role`, `cp`, `knots`（adaptive 必需）, 可选 `dup` |

重绘步骤：对每个 region 在 `u∈[0,1)` 采样 `eval_n` 点 → 闭合多边形 → `fillPoly`。

## 关键实现路径

- 拟合：`src/insoles/contour.py` → `mask_to_parametric_contour(fit_mode=adaptive)`
- 样条：`src/insoles/adaptive_bspline.py`
- 导出：`src/insoles/render_payload.py` + `scripts/export_render_payload.py`
- 验收：`verification_scaled_adaptive/`、`reports/boundary_summary_scaled.json`

## 已知的坑 / 约束

- `pixel_scale_cm` 随缩放变化：`scaled = source / dimension_scale`（10× 缩小 → 0.0855）
- `uniform_bspline` 旧 JSON 无 `knots`；render payload 当前仅导出 adaptive
- `1` 与 `2` 号传感器区域几何相同（`dup` 标注）
