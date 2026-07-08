# Task: Base长轴OBB扩边与坐标重映射

- **日期**：2026-07-07
- **状态**：已完成

## Problem / 目标

将 `base` 轮廓按指定长轴 `(1883,609)->(1763,3643)` 计算 OBB，并在长轴/短轴两侧各扩边 `1cm`，将该新矩形作为统一图像范围，批量重映射 `base + 1..16` 的 `mask/contour` 到新坐标系，且保持 `cm/px` 比例不变。

## 核心思路

- 通过给定长轴单位向量 `u_long` 与法向 `u_short` 建立局部坐标系。
- 以 `base.json` 采样曲线投影得到 `min/max`，再按 `margin_px = 1cm / pixel_scale_cm` 扩展四向。
- 构建统一仿射矩阵 `old->new`，用于：
  - `masks/*.png` 的 `warpAffine`（近邻插值，保留二值语义）
  - `contours/*.json` 控制点批量变换
- 重渲染 `contours_obb` 并与 `masks_obb` 计算 IOU。

## 受影响文件

- `src/insoles/obb_transform.py`（新增）
- `scripts/reframe_by_base_obb.py`（新增）
- `masks_obb/*.png`（新增）
- `contours_obb/*.json`（新增）
- `verification_obb/*.png`（新增）
- `reports/obb_frame.json`（新增）
- `reports/iou_summary_obb.json`（新增）

## 结果

- 输出范围：`3272 x 1325`
- 像素比例：保持 `pixel_scale_cm = 0.00855`
- 验证 IOU：`mean=0.989531`, `min=0.984972`, `max=0.998079`

## Debug Notes

- 2026-07-07 18:22：`Glob` 没有返回 PNG，但本地目录存在文件；处理时改为按真实路径读取并继续执行。

## Lessons Learned

- 固定主轴方向可稳定定义 OBB 局部坐标系，便于统一变换全量 mask/contour。
- mask 重采样必须使用 `INTER_NEAREST`，避免边界灰阶污染导致二值误差放大。
