# Progress（进展记录）

## 里程碑

- 2026-07-09 **修正 masks 全 pipeline 重跑**（已同步至 `tools/insoles-boundary/`）
  - 源：`masks/`（3072×4096，传感器区域标记已修正）
  - 流程：全分辨率 adaptive 拟合 → OBB 裁切 + **顺时针 90° 旋转** → 10× 缩小 → adaptive 拟合
  - 输出：`masks_obb/`（1318×3244）→ `masks_scaled/`（132×324）→ `contours_scaled_adaptive/`
  - 交付：`reports/render_payload.json`（132×324，`pixel_scale_cm=0.0855`）
  - 验收：mean boundary 0.290 px，mean IOU 0.917
- 2026-07-09 **Render Payload 交付（仓库最终目标）**
  - 工具：`python scripts/export_render_payload.py`
- 2026-07-09 **掩码缩放 + 自适应 B-spline**（首次，旧 masks）
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
| OBB + CW90 重映射 | 完成（主线必经） |
| 缩放 + adaptive 拟合 | 完成 |
| **Render Payload 导出** | **完成（主交付）** |
| 外部重绘参考实现 | 未开始 |
| 压力可视化 / 传感器映射 | `fsr_calibrate` 已接入 |

## 已知问题

- `scaled_record.json` 为 QA 对比用；**外部集成请用 `render_payload.json`**
- `contours_scaled/`（uniform）为旧流水线遗留，与当前主线无关
