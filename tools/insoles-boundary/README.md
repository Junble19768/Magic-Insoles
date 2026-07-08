# insoles-boundary · 鞋垫 FSR 阵列边界拟合工具

把**鞋垫照片手动抠图**得到的二值掩码，处理并拟合为**紧凑、连续、可参数化**的周期 B-spline 边界，最终导出一个**自包含单文件** `reports/render_payload.json`，复制即可在网页 / 嵌入式等外部环境重绘全部 17 个区域（鞋垫本体 base + 16 个传感器）。

> 这是从独立项目 `ignored/insoles-boundary/`（含独立 git 历史）整理留存到父仓库的副本，方便未来复用。完整的处理流程、算法细节、验收指标见 **[`docs/PIPELINE.md`](docs/PIPELINE.md)**。

## 快速上手

```bash
cd tools/insoles-boundary
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows PowerShell（Linux/mac: . .venv/bin/activate）
pip install -r requirements.txt

# 复现主线：缩放掩码 → 自适应 B-spline → 导出 render payload
python scripts/scale_masks.py --scale 0.1 --mask-dir masks --output-dir masks_scaled --source-pixel-scale-cm 0.00855
python scripts/process_masks.py --fit-mode adaptive --metric boundary_mean \
  --mask-dir masks_scaled --output-dir contours_scaled_adaptive \
  --report reports/boundary_summary_scaled.json --dimension-scale 0.1
python scripts/export_render_payload.py --contour-dir contours_scaled_adaptive --output reports/render_payload.json
```

## 目录速览

| 路径 | 内容 |
|------|------|
| `src/insoles/` | 核心算法库（轮廓提取、uniform/adaptive B-spline、边界指标、坐标变换、payload 导出） |
| `scripts/` | 命令行流水线（缩放 / 拟合 / 导出 / 重绘 / OBB / 左下角坐标） |
| `masks/` `masks_scaled/` | 原始 / 10× 缩小的二值掩码 PNG |
| `contours*/` | 各阶段轮廓参数 JSON（`contours_scaled_adaptive/` 为最终来源） |
| `reports/` | 各阶段验收报告 + **`render_payload.json`（最终交付物）** |
| `docs/` | `PIPELINE.md` 总览 + 阶段任务留痕 + 设计讨论 + 记忆快照 |

## 关键约定

- 物理尺度：原始掩码 `0.00855 cm/px`；10× 缩小后 `0.0855 cm/px`（缩放必须同步修正）。
- 拟合表示：周期三次 B-spline；adaptive 轮廓的 JSON 必须携带 `knot_params`。
- 最终交付：`reports/render_payload.json`（schema `insoles.render_payload/v1`）。

## 数据追踪说明

父仓库根 `.gitignore` 忽略 `*.png` / `*.jpg`。本目录内的 `.gitignore` 用否定规则**有意重新纳入掩码 PNG**，以保证数据集可复现。大体积原始素材（`insoles.psd` 等）不入 git，保留在 `ignored/insoles-boundary/ignored/`（见 `docs/PIPELINE.md` 第 8 节）。
