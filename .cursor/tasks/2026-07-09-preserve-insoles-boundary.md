# Task: 鞋垫边界拟合项目留存与文档化

- **日期**：2026-07-09
- **状态**：已完成
- **关联**：`tools/insoles-boundary/`；原始项目 `ignored/insoles-boundary/`（独立 git 仓库，位于父仓库 `ignored/` 之下，父仓库不追踪）

## Problem / 目标

`ignored/insoles-boundary/` 是一个自成一体的 Python 项目：把鞋垫照片手动抠图得到的二值掩码，处理并拟合为可携带的 B-spline 重绘载荷（`render_payload.json`）。它有**独立的 `.git`**，且整体位于父仓库 `ignored/`（被父仓库 `.gitignore` 排除），因此**父仓库完全不追踪它**，未来容易随 `ignored/` 一起丢失。

目标：把该项目的**代码、处理过程文档、可复现数据集**整理并留存到父仓库中一个不起眼但能被 git 记录的位置，方便未来复用；大体积原始素材（PSD/照片/验证图）保留在原 `ignored/` 位置，不入 git。

## 核心思路

- 目标位置：`tools/insoles-boundary/`（用户确认；语义清晰的工具目录）。
- 入 git 范围（用户确认）：代码 + 处理文档 + 报告 JSON + 可复现数据集（掩码 PNG / 轮廓 JSON）。
- 父仓库 `.gitignore` 全局忽略 `*.png`/`*.jpg`，故在 `tools/insoles-boundary/` 放一个**嵌套 `.gitignore`** 用 `!` 重新纳入所需 PNG。
- 不复制原项目的 `.git`、`__pycache__`、`ignored/`；只从原项目按需拷贝。
- `data/` 经校验为 `masks/`+`contours/` 的完全重复，跳过以避免冗余。
- 原始大文件（`insoles.psd` 65MB、原始照片、验证图 ~80MB）保留在 `ignored/insoles-boundary/ignored/`，仅在文档中记录其位置与用途。
- 新增一份**汇总处理文档** `docs/PIPELINE.md`，把散落在 memories/tasks/TALK 的需求、算法、命令、验收指标整合为单一可读文档。

## 受影响的文件 / 模块

- `tools/insoles-boundary/src/insoles/*.py` — 核心算法库（拷贝）
- `tools/insoles-boundary/scripts/*.py` — 处理流水线脚本（拷贝）
- `tools/insoles-boundary/{masks,masks_scaled,contours,contours_scaled,contours_scaled_adaptive,reports}/` — 数据与报告（拷贝）
- `tools/insoles-boundary/docs/` — 处理过程文档（新增 PIPELINE.md + 拷贝 memories/tasks/TALK）
- `tools/insoles-boundary/README.md`、`requirements.txt`、`.gitignore` — 新增/拷贝
- `.cursor/tasks/2026-07-09-preserve-insoles-boundary.md` — 本文档

## 分步计划

- [x] Step 0: 阅读原项目全部代码、脚本、文档，理解 pipeline
- [x] Step 1: 拷贝代码（src/scripts/requirements.txt）
- [x] Step 2: 拷贝可复现数据集（masks/contours/reports，跳过 data/ 重复）
- [x] Step 3: 拷贝过程文档到 docs/（memories/tasks/TALK-0002）
- [x] Step 4: 编写 docs/PIPELINE.md 汇总文档
- [x] Step 5: 编写 README.md 与嵌套 .gitignore
- [x] Step 6: 校验 git 追踪，更新父仓库记忆

## Debug Notes

- 2026-07-09 校验：`data/masks/base.png` 与 `masks/base.png`、`data/contours/base.json` 与 `contours/base.json` 哈希一致，`data/` 为冗余副本，跳过。

## Lessons Learned

- 父仓库根 `.gitignore` 的 `*.png` 会传导到子目录；用**嵌套 `.gitignore` 的否定规则 `!*.png`** 即可把工具目录内的数据 PNG 重新纳入追踪（`git check-ignore -v` 显示匹配到 `!*.png` 即成功）。因 `tools/` 本身未被忽略，否定生效不受「父目录被忽略则无法再纳入」的限制。
- 校验 `git add -n` 干跑：共 125 个文件将入库（34 PNG + 59 JSON + 16 py + 文档），确认数据集完整可复现。
- 只从原独立仓库**按需拷贝**，不带 `.git`/`__pycache__`/`ignored/`；原项目保持原样作为本地全量备份。
- 大体积二进制（`insoles.psd` 65MB 等）不入 git，避免污染历史；在 `docs/PIPELINE.md` 记录其位置与用途即可满足「未来复用」。
