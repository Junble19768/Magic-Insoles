# .cursor 仓库模板说明

这是一个**仓库模板（scaffold）**，用于辅助未来所有 AI 主导开发的项目：先在这里沉淀一套通用的 Cursor 规则、Skill 与目录约定，新项目 clone/复制本模板即可直接获得一整套“AI 数字大脑”工作流，而不必每个项目重新摸索。

## 需求背景

模板的设计理念来自 [`inputs/ai-discusses/TALK-0001.md`](inputs/ai-discusses/TALK-0001.md) 中与 Gemini 的讨论，核心问题是：在“人负责决策、AI 负责实现”的开发模式下，代码库不再是理解项目的唯一真理来源——**架构意图、设计取舍、调试过程中的经验**同样关键，但传统上只存在于易丢失的聊天记录里。具体痛点有三个：

1. **上下文碎片化**：项目的设计理念、需求讨论散落在文档和聊天记录里，每次都要手动 `@` 文档喂给 AI，成本高且容易遗漏。
2. **过程留痕缺失**：大型任务的 Plan、Debug 过程只存在于聊天窗口，任务结束后即“石沉大海”，下次遇到类似问题 AI 还要重新踩坑。
3. **Git 提交质量低 & Issue 暂存诉求**：AI 生成的 commit message 流于表面、丢失背景；同时需要一个“需求冷钱包”——灵感/bug 可以先暂存，不打断当前开发主线，攒够了再批量处理，避免频繁碎片提交污染上下文。

## 做了什么工作

围绕上述痛点，仓库在 `.cursor/` 下搭建了一套**记忆（Memory）+ 留痕（Task）+ 冷钱包（Issue）+ 规则（Rules）+ 技能（Skills）**的协作体系：

| 目录 | 作用 |
|------|------|
| `.cursor/inputs/` | 人工输入区，AI 不可修改，承载外部需求与设计讨论，详见 [`inputs/README.md`](inputs/README.md) |
| `.cursor/memories/` | Memory Bank「数字大脑」：`projectbrief → productContext/systemPatterns/techContext → activeContext → progress`，逐层派生，记录“为什么这么做”而非代码本身；`decisions/` 存放重大决策 ADR |
| `.cursor/tasks/` | 任务留痕：大型任务开工前建 Plan 文档（Problem / 思路 / 受影响文件 / 分步计划），过程中追加 Debug Notes，收尾写 Lessons Learned |
| `.cursor/issues/` | 需求「冷钱包」：仅当用户明确要求暂存时才登记 issue，只捕获不修复；攒够后显式触发批量消灭 |
| `.cursor/pricing/` | Cursor 内各模型的定价与 Agent/Tab/Chat 场景收费指数、按 Tier 的选型建议（`pricing.md`/`pricing.csv`/`bak.md`），用于控制 AI 开发成本 |
| `.cursor/rules/` | 常驻规则（见下） |
| `.cursor/skills/` | 可调用技能（见下） |

这些目录里的文件目前多为**模板/占位骨架**（如 `memories/projectbrief.md` 中的 `<...>` 占位符），设计上是让新项目 clone 本模板后，随开发进度逐步填实，而不是一开始就有具体项目内容。

## Rules 简述（`.cursor/rules/`，常驻规则）

- **`workflow/ai-workflow.mdc`**（`alwaysApply: true`）：串联整套工作流的主规则——任务开始先读 Memory Bank；大任务先立 Plan 并留痕 Debug Notes/Lessons Learned；里程碑后增量刷新记忆；Git 按小步自主提交；Issue 仅在用户使用暂存类措辞时才登记，批量处理需显式触发。
- **`safety/operational-safety.mdc`**（`alwaysApply: true`）：文件、密钥、数据库、外部副作用等操作安全边界（不碰二进制/密钥、不做破坏性 DB 操作、生产环境改动需确认）。
- **`safety/git-permissions.mdc`**（`alwaysApply: true`）：Git 权限分层——`add`/`commit` 可自主执行；普通 `push`/分支操作需 `AskQuestion` 确认；改历史类操作（rebase/amend/reset/force）需先出方案再确认；统一 commit message 格式（`type(scope): subject` + `Why`/`How`/`Refs`）。
- **`safety/code-security.mdc`**（按语言文件类型触发）：输入校验、参数化查询、密钥不硬编码、错误信息不泄露内部细节、鉴权必须服务端校验。
- **`coding-guidelines/`**（按语言文件类型触发）：`code-quality.mdc`（函数聚焦、早返回、控制复杂度）、`documentation.mdc`（公共 API 注释规范，按语言区分 JSDoc/Docstring/Doxygen/Javadoc）、`naming-conventions.mdc`（命名风格）、`dependency-management.mdc`（依赖引入前的复用与健康度检查）、以及 `python.mdc`/`typescript.mdc`/`java.mdc`/`cpp.mdc` 等各语言专项规范。
- **`project-related/`**：当前为占位目录（含 `.gitkeep`），预留给具体项目落地时补充的专属规则（如 `website-design.mdc` 一类）。

## Skills 简述（`.cursor/skills/`，按需调用）

均为 `disable-model-invocation: true`，需用户明确意图触发：

- **`task-plan`**：大任务开工前的脚手架。读取 Memory Bank 建立上下文后，依模板在 `.cursor/tasks/` 生成 Plan 文档（Problem/思路/受影响文件/分步计划），产出后等待用户确认，不直接写代码。
- **`memory-update`**：里程碑时增量刷新 Memory Bank。扫描近期 commit/Task Plan，对比现状与记忆差异，出更新方案，确认后写入 `activeContext.md`/`progress.md`（架构变化则更新 `systemPatterns.md` 或新增 ADR），只做增量更新、不推倒重写。
- **`issue-log`**：需求冷钱包的「捕获」端。仅当用户使用“记个 issue / 先记下来 / 暂存”等措辞时触发，按模板在 `.cursor/issues/` 生成 `issue-NNNN-<slug>.md`，只登记不修复、不动代码、不提交。
- **`issue-sweep`**：需求冷钱包的「批量消灭」端。用户显式触发后，扫描所有 `open` issue、按关联性分组，委托 `task-plan` 出批量修复计划，确认后实现，修完后将 issue 置为 `closed` 并记录 `resolved-by`，最终交由 `git-agent` 提交（message 含 `Fixes: #NNNN`）。
- **`git-agent`**：统一 Git 代理，三种模式——`commit`（默认，读取工作区与最近 Task Plan，按小功能点分组自主 `add`+`commit`，message 含 Why/How/Refs/Fixes）、`reorganize`（整理 wip/临时提交，属改历史操作，须先出方案经 `AskQuestion` 确认）、`branch`（创建/切换/合并/删除分支，同样需确认）。
