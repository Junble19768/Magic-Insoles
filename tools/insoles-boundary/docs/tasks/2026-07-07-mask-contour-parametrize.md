# Task: 掩码轮廓平滑与参数化

- **日期**：2026-07-07
- **状态**：已完成
- **关联**：[TALK-0002.md](../inputs/ai-discusses/TALK-0002.md)

## Problem / 目标

将 `masks/` 中 17 张二值掩码（鞋垫 base + 16 个传感器区域）转为可参数化的闭合 B-spline 轮廓 JSON，替代直接存储 mask；并通过重渲染 IOU 验证保真度。

## 核心思路

- `findContours` → 弧长均匀重采样 (N=500) → `splprep(per=True)` 闭合 B-spline
- 禁止 `approxPolyDP`
- 自适应选择平滑参数 `s`：在候选列表中选满足 IOU ≥ 0.995 的最大 s
- 输出 JSON（control_points + knots + degree + 元数据）

## 受影响的文件 / 模块

- `requirements.txt` — Python 依赖
- `src/insoles/contour.py` — 核心算法
- `src/insoles/schema.py` — JSON 序列化
- `scripts/process_masks.py` — 批量处理 CLI
- `scripts/render_contour.py` — 单张重渲染 CLI
- `contours/*.json` — 输出参数
- `reports/iou_summary.json` — 验收报告
- `verification/` — 对比可视化

## 分步计划

- [x] Step 1: 创建任务文档
- [x] Step 2: 添加 requirements.txt
- [x] Step 3: 实现核心库
- [x] Step 4: 实现 CLI 脚本
- [x] Step 5: 批量处理并验证 IOU
- [x] Step 6: 更新 memory 并 commit

## Debug Notes

- 2026-07-07 调研：`1.png` 与 `2.png` 完全相同；B-spline s=20 时小区域 IOU ~0.992，需自适应 s
- 2026-07-07 实现：`splprep` 周期样条的 `tck[1]` 为 `[x_ctrl, y_ctrl]` 列表，非扁平数组
- 2026-07-07 IOU v2：控制点预算约束——传感器 10–100、base 10–150；在预算内最大化 IOU（粗搜 step=5 + 局部精搜）

## Lessons Learned

- 闭合 B-spline 重渲染应使用 `splprep` 返回的 `parameter_samples`，而非 `linspace(u)`，否则高曲率段采样不足
- 控制点预算下应搜索 `(resample_n, s)` 最大化 IOU，而非无上限提高 resample_n
- 周期样条控制点数 ≈ `resample_n + 2`，预算需按实际 `control_point_count(tck)` 校验
