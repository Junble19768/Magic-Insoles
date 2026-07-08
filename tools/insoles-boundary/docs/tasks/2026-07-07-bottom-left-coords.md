# Task: 左下角 row/col 坐标系重规划

- **日期**：2026-07-07
- **状态**：已完成

## Problem / 目标

将 OBB 重映射后的 `masks_obb/contours_obb` 从左上角 `(x,y)` 坐标系，转换为以图片左下角为 `(0,0)`、`col` 向上递增、`row` 向左递增的坐标系。

## 核心思路

- 点变换：`(row, col) = (W - 1 - x, H - 1 - y)`
- 掩码变换：等价于先转置再水平翻转，`mask_bl[row, col] = mask_tl[H - 1 - col, W - 1 - row]`
- `image_size` 数值保持 `[W, H]`，语义改为 `[n_rows, n_cols]`
- `pixel_scale_cm` 不变

## 受影响文件

- `src/insoles/coord_transform.py`（新增）
- `scripts/reorient_to_bottom_left.py`（新增）
- `masks_bl/*.png`（新增）
- `contours_bl/*.json`（新增）
- `verification_bl/*.png`（新增）
- `reports/iou_summary_bl.json`（新增）

## 结果

- 输出 17 项（base + 1..16）
- IOU：`mean=0.989531`, `min=0.984972`, `max=0.998079`

## Lessons Learned

- 坐标系重定义与像素重排需分离处理：点用仿射换算，mask 用索引重映射，验证时通过往返变换接入现有渲染器。
