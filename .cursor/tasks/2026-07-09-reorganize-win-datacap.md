# Task: win-datacap 迁入 tools/ 并补充标定拟合文档

- **日期**：2026-07-09
- **状态**：已完成
- **关联**：`tools/win-datacap/`（原仓库根目录 `win-datacap/`）；姊妹任务 `.cursor/tasks/2026-07-09-preserve-insoles-boundary.md`

## Problem / 目标

`win-datacap/`（USB 采集卡、压力传感器、标定与拟合算法）此前位于仓库根目录，与新建的 `tools/insoles-boundary/` 不一致；且新增的 `best_rx.ipynb`（基于 FSR 标定/ADC 反推合理参考电阻 Rx）尚未入库、也没有文档说明其原理。目标：把 `win-datacap/` 整体迁入 `tools/` 目录，纳入 `best_rx.ipynb`，并补充一份把「采集 → 标定 → 拟合 → 复用 → Rx 选型」串起来的说明文档，同时更新父仓库记忆。

## 核心思路

- 用 `git mv` 逐个顶层条目迁移（而非对整个目录一次性 `git mv`），因为根目录本身被某个正在运行的进程/终端占用句柄导致整体重命名 `Permission denied`；子项逐一移动不受影响。
- `best_rx.ipynb` 此前未跟踪，`git mv` 对其静默失败，改用文件系统 `Move-Item` 迁移后再 `git add`。
- `win-datacap/doc/` 下的说明书 PDF、演示 MP4、PPTX **实际已被历史提交跟踪**（初次用 `git ls-files` 因中文文件名在 PowerShell 管道中显示异常而被误判为「未跟踪的大文件」）；核实后确认应作为正常 rename 迁移，不做特殊排除。
- `record/.gitignore`（`*` 全忽略 + `!.gitignore`）、根 `.gitignore` 的 `*.exe`/`*.dll` 规则在新路径下用 `git check-ignore -v` 校验依然生效，行为不变。
- 新增 `tools/win-datacap/docs/CALIBRATION_PIPELINE.md`：串联分压电路模型、`fsr_calibrate/` 实时采集与时间对齐、`plot_fsr_grid_fit.py` 批量拟合、`calibration_store.py` 标定复用、`best_rx.ipynb` 的 Rx 选型仿真方法。README.md 顶部结构图与新增小节链接该文档。
- 更新父仓库记忆（`systemPatterns.md` 架构树、`techContext.md`、`progress.md`、`activeContext.md`）中的路径引用与状态描述；`.cursor/bakup/` 内的归档文档保持原样，不追溯更新。

## 受影响的文件 / 模块

- `win-datacap/**` → `tools/win-datacap/**`（54 个已跟踪文件 rename + `best_rx.ipynb` 新增）
- `tools/win-datacap/docs/CALIBRATION_PIPELINE.md` — 新增
- `tools/win-datacap/README.md` — 新增「离线拟合与参考电阻（Rx）选型」小节、结构图更新、相关文档链接
- `.cursor/memories/systemPatterns.md` — 代码仓库结构树：`win-datacap/` → `tools/{win-datacap,insoles-boundary}/`
- `.cursor/memories/techContext.md` — 路径与状态表更新
- `.cursor/memories/progress.md` — 状态表更新、里程碑追加、过期 TODO 订正
- `.cursor/memories/activeContext.md` — 近期变更追加

## 分步计划

- [x] Step 1: 通读 `best_rx.ipynb`、`plot_fsr_grid_fit.py`、`fsr_calibrate/*`、`usb_daq_v20/constants.py`，理解分压模型与标定拟合全链路
- [x] Step 2: 清理 `__pycache__`，逐条目 `git mv` 迁移至 `tools/win-datacap/`
- [x] Step 3: 迁移并 `git add` 此前未跟踪的 `best_rx.ipynb`
- [x] Step 4: 校验暂存区（54 rename + 1 add，无孤立 D/A），校验 `.gitignore` 规则在新路径下依然生效
- [x] Step 5: 新增 `docs/CALIBRATION_PIPELINE.md`，更新 README
- [x] Step 6: 更新父仓库记忆四个文件

## Debug Notes

- 2026-07-09 03:xx `git mv win-datacap tools/win-datacap` 报 `Permission denied`；逐一探测顶层条目发现每个子项均可单独重命名，说明是 `win-datacap` 目录本身被某进程（很可能是终端 3 中仍在重试 WebSocket/TCP 连接的 `fsr_calibrate`/`force_server` 相关脚本）持有句柄，而非具体文件被锁。改为逐条目 `git mv` 绕过。
- 2026-07-09 03:xx 迁移后 `win-datacap` 变为空目录但仍无法删除（同一句柄占用），确认为无害残留（git 不跟踪空目录），留待用户关闭对应终端/进程后手动清理。
- 2026-07-09 03:xx 误判 `doc/` 下 3 个大文件（PDF/MP4/PPTX，共约 50MB）为未跟踪文件并执行了 `git restore --staged`，导致暂存区出现「孤立 D（仅删除无新增）」；用 `git ls-tree HEAD` 核实这些文件其实已在历史提交中，随即重新 `git add` 恢复为正常 rename，避免了错误地把已入库文件变成未跟踪状态。

## Lessons Learned

- Windows 下整目录 `git mv`/`Remove-Item` 若报 `Permission denied`，优先怀疑「目录本身被某进程的句柄占用」（常见于遗留的开发服务器终端），而非文件被锁；用「逐个子项探测重命名」可快速定位并绕过，无需强行结束用户进程。
- 中文/宽字符文件名在 PowerShell 管道（`Select-String`/`Select-Object`）中可能显示为空白或被截断，容易被误判为「命令未返回结果」甚至「文件不存在/未跟踪」；关键判断（是否已被 git 跟踪）应改用 `git ls-tree`/`git diff --cached --name-status` 等确定性命令交叉验证，而不是仅凭一次管道显示下结论。
- `git status --porcelain --ignored` 中同一文件在移动前后可能因编码问题呈现不一致的前缀标记；对不确定的条目应二次核实再执行 `restore`/`rm` 等会改变跟踪状态的操作。
