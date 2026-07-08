# Progress（进展记录）

## 里程碑

- 2026-07-09 **Render Payload 交付（仓库最终目标）**
  - 输出：`reports/render_payload.json`（`insoles.render_payload/v1`）
  - 内容：17 区域 adaptive_bspline `cp` + `knots`，画布 132×327，`pixel_scale_cm=0.0855`
  - 工具：`python scripts/export_render_payload.py`
- 2026-07-09 **掩码缩放 + 自适应 B-spline**
  - 缩放：`masks_scaled/`（10× 缩小，最近邻）
  - 拟合：`contours_scaled_adaptive/`
  - 验收：`reports/boundary_summary_scaled.json`（mean boundary 0.35 px）
- 2026-07-07 **掩码轮廓参数化完成**
  - 输出：`contours/*.json`（uniform_bspline，mean IOU 0.992）
- 2026-07-07 **Base长轴 OBB 重映射完成**
  - 输出：`masks_obb/`、`contours_obb/`
- 2026-07-07 **左下角 row/col 坐标系完成**
  - 输出：`masks_bl/`、`contours_bl/`

## 当前状态

| 模块 | 状态 |
|------|------|
| 掩码 → B-spline JSON | 完成 |
| 缩放 + adaptive 拟合 | 完成 |
| **Render Payload 导出** | **完成（主交付）** |
| 外部重绘参考实现 | 未开始 |
| 压力可视化 / 传感器映射 | 未开始 |

## 已知问题

- `1.png` 与 `2.png` 完全相同（payload 中 `dup` 标注）
- `scaled_record.json` 为 QA 对比用；**外部集成请用 `render_payload.json`**
