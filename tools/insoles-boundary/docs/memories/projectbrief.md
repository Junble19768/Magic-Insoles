# Project Brief（项目基石）

> 所有其他记忆文件的源头。定义“做什么、边界在哪”。

## 一句话定位

将鞋垫 FSR 阵列的二值区域掩码转为**可携带的 B-spline 重绘载荷**，供网页、嵌入式等外部环境复现各传感器/基底区域轮廓。

## 核心目标

- 从 `masks/` 提取闭合轮廓，参数化为周期 B-spline（控制点 + knot 参数）
- 在控制点预算内优化边界贴合度（adaptive_bspline + boundary_mean）
- 输出**单一紧凑 JSON**（`reports/render_payload.json`），复制即可在外部重绘全部区域
- 保留 `pixel_scale_cm` 等物理尺度信息，便于后续压力热力图与坐标映射

## 范围边界

- **做**：掩码缩放、轮廓拟合、质量验收、导出 render payload
- **不做**：实时采集、固件驱动、完整 UI 产品（消费方自行实现重绘与可视化）

## 成功标准

- `render_payload.json` 自包含重绘所需的 schema、画布、样条参数、17 个区域 `cp`/`knots`
- 外部仅需实现 `adaptive_bspline` 采样 + 多边形填充即可还原区域
- 拟合验收：scaled 数据集 mean boundary < 2 px，verification diff 可接受

## 关键干系人 / 需求来源

- 用户：嵌入式/网页复用轮廓数据，避免传输完整 mask 位图
- 讨论记录：`.cursor/inputs/ai-discusses/TALK-0002.md`（B-spline 参数化思路）
