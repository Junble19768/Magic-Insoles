---
name: git-commit-propose
description: >-
  Analyze uncommitted working-tree changes (staged and unstaged), summarize themes and
  key details by module, propose 1-3 Conventional Commit messages with split plans, and
  after user confirmation batch git add and git commit. Use when the user asks to propose
  commit, compose commit, draft commit, generate commit message, 提交当前修改, commit 建议,
  提交助手, uncommitted changes, or 工作区提交. Not for rewriting existing commit history
  (use git-commit-reorganize).
disable-model-invocation: true
---

# Git Commit Propose

分析工作区未提交改动，按模块归纳主题与细节，建议 1～3 条 commit message 及分批提交方案；**用户确认前只分析与建议，确认后才执行 `git add` + `git commit`。**

## 关键约束（优先遵守）

1. **Skill 接受 ≠ 提交授权。** Cursor 弹出「是否运行/接受 skill」只表示加载本 workflow；**绝不**据此进入 Step 7 或执行 `git add` / `git commit`。
2. **Step 6 必须用 `AskQuestion`。** 完成分析后调用 `AskQuestion` 展示选项卡；不要仅用文字列表追问。若工具不可用，再退回文字询问。
3. **AskQuestion 后立刻结束本回合。** 调用 `AskQuestion` 是本回合的**最后一步**；同一回合内不得继续 Shell 写操作，不得假设用户已授权。
4. **Step 7 仅在 AskQuestion 明确选择「授权执行提交」后**（且用户在后续回合未改口）才可运行。

不写 `docs/changelog.md`。Git commit 格式标准与安全准则见 [`.cursor/rules/git-workflow.mdc`](../../rules/git-workflow.mdc)。

已有 commit 历史需整理时，使用 [git-commit-reorganize](../git-commit-reorganize/SKILL.md)，勿与本 skill 混用。

## 触发后先确认范围

默认分析**全部**未提交改动（staged + unstaged + untracked）；若用户指定路径或文件，以其为准。

可选：运行工作区摘要脚本快速按模块分组：

```powershell
# Windows（优先）
.\.cursor\skills\git-commit-propose\scripts\summarize-working-tree.ps1 [-Paths <path1>,<path2>]
```

```bash
# Git Bash / Linux / macOS
.cursor/skills/git-commit-propose/scripts/summarize-working-tree.sh [path1 path2 ...]
```

## Workflow

复制 checklist 并逐项完成：

```
- [ ] Step 1: 读取工作区
- [ ] Step 2: 总结变更主题与关键细节
- [ ] Step 3: 分组生成目标 commit 列表
- [ ] Step 4: 输出推荐 commit message
- [ ] Step 5: 输出提交方案
- [ ] Step 6: 调用 AskQuestion 展示选项卡，结束本回合
- [ ] Step 7: AskQuestion 授权后分批提交（可选）
```

### Step 1 — 读取工作区（只读）

默认执行：

```bash
git status
git diff --stat
git diff --cached --stat
git diff
git diff --cached
```

记录：

- 当前分支
- 变更文件列表、各文件状态（`M` / `A` / `D` / `??`）
- 已 stage / 未 stage 分布

若 `git status` 无任何改动（含 untracked 也无）→ 告知用户并**终止**。

### Step 2 — 总结修改主题与关键细节

按**逻辑主题 / 功能模块**归纳（不要按文件字母序罗列）：

- 改了哪些模块、行为 / API / 数据流变化
- 关键实现细节（2～5 条 bullet，够写清 intent 即可）
- 是否含文档、测试、配置、依赖变更
- 模块间依赖顺序（例如：目录结构调整 → 后端能力 → 前端对接 → 文档）
- 有无不应提交的内容（`.env`、密钥、调试代码、临时文件）→ **标为排除并警告**

### Step 3 — 多 commit 分组策略

输出「目标 commit 列表」，每条包含：顺序、message 草案、涵盖路径 / 文件、排序理由、是否含已 stage 文件。

分组原则：

1. **按模块聚合**：`backend/`、`frontend/`、`docs/`、`3rdparty/`、`config.yml` 等分开；各模块独立意图时建议**多条 commit**。
2. **按依赖顺序排列**：结构 / 配置 / refactor 在前，功能 feat 居中，docs / chore 可置后。
3. **能拆则拆**：优先 **1～3 条**；仅当模块 / 阶段确实独立时才超过 3 条。
4. **强耦合例外**：同一功能跨模块且必须同批上线（如 API + 对应前端页面）→ 可合并为 1 条并说明原因。
5. **用户覆盖**：若用户明确要求「一条 commit 提交全部」→ 尊重，但注明 trade-off。

scope 从路径推断，参考映射：

```text
backend/          → backend
frontend/         → frontend
3rdparty/         → 3rdparty 或 crawler
docs/             → docs
config.yml        → config
根目录环境/CI      → chore
```

### Step 4 — 推荐 commit message

为**每个目标 commit** 给出 1 条首选 + 最多 1 条备选，格式严格遵守 [git-workflow.mdc](../../rules/git-workflow.mdc)：

```
type(scope): subject
```

- subject 动词开头、≤50 字；细节放在「变更总结」，不要塞进 subject
- type 从变更性质推断（`feat` / `fix` / `docs` / `refactor` / `chore` 等）

在回复中按目标 commit 分组列出「首选」与「备选」。

### Step 5 — 提交方案

**Step 6 之前只输出计划，不执行。** 默认策略：按组顺序 `git add <paths>` → `git commit -m "..."`。

方案须包含：

1. **操作表**：顺序、message、路径 / 文件、说明
2. **staging 说明**：未 stage 文件在各步 add；已 stage 文件归属哪一组；避免重复 add 或漏 add
3. **预期结果**：最终 commit 数量、顺序与 message 列表
4. **风险**：是否有不应提交文件、未跟踪大文件、与分支命名 / 规范冲突

执行示例（计划阶段仅展示，不运行）：

```bash
git add <paths-for-commit-1>
git commit -m "type(scope): subject"
git add <paths-for-commit-2>
git commit -m "type(scope): subject"
```

**在用户确认之前，不得运行：** `git add`、`git commit`、`git push`。

### Step 6 — 用 AskQuestion 收集确认并结束本回合

完成 Step 1～5 后，在回复中输出完整分析，然后**必须**调用 `AskQuestion`（不要仅用文字追问）。若 `AskQuestion` 不可用，再退回 Step 6 末尾的文字确认清单。

**`AskQuestion` 须作为本回合最后一次 tool call。** 调用后不得再运行 Shell、`git add`、`git commit` 或任何写操作。

一次 `AskQuestion` 调用包含以下 **3 个 single-select 问题**（`title` 建议：`提交方案确认`）：

| id | prompt | options（按 Step 3～5 结果动态填写 label） |
|----|--------|-------------------------------------------|
| `split_plan` | 采用哪种拆分方案？ | **采纳推荐拆分（N 条）**（N 与条数写入 label）/ **合并为更少条数** / **单条 commit 提交全部** / **其他（下一条消息说明）** |
| `message_choice` | 各组 commit message 用哪套？ | **全部首选** / **全部备选** / **部分自定义（下一条消息说明）** |
| `execute` | 下一步？ | **仅分析，暂不提交（推荐）** / **授权执行 git add + git commit** |

规则：

- `split_plan` 的「采纳推荐拆分」option label 须含实际条数（如 `采纳推荐拆分（5 条）`）。
- 默认推荐 `execute` = **仅分析**；用户选此项时结束，不进入 Step 7。
- 仅当 `execute` = **授权执行 git add + git commit** 时，下一回合才可进入 Step 7。
- 用户选「其他」或「部分自定义」→ 等待下一条消息补充，仍不得自动提交。
- **禁止**把 Cursor 加载 skill 的确认弹窗、或 agent 自行推断的「已授权」，当作 Step 7 许可。

若 `AskQuestion` 不可用，在回复末尾用文字等价询问上述 3 点，并同样结束本回合。

### Step 7 — AskQuestion 授权后分批提交

仅在 AskQuestion 的 `execute` 选择了 **授权执行 git add + git commit**（且用户未在后续消息中撤回）后：

1. 再次 `git status`；工作区若已变化则重新核对或中止。
2. 按 Step 5 方案顺序，每组：
   - `git add <paths>`
   - `git diff --cached --stat`（展示即将提交内容）
   - `git commit`（使用 HEREDOC 传 message，与用户 commit 规则一致）
3. 完成后 `git log --oneline -n <N>` 对照预期。
4. **不自动** `git push`。

**禁止运行：** `git commit --amend`（除非用户另提）、`git reset --hard`、`git push`。

## 回复结构（给用户）

```markdown
## 工作区状态
- 分支 / staged vs unstaged 概览

## 变更总结
- 主题化要点 + 关键细节

## 目标 commit 列表
- 顺序 / message / 路径 / 排序理由

## 推荐 commit message
- 每组：首选 / 备选

## 提交方案
- 分批 add 顺序 / staging 说明 / 预期结果 / 风险

---
（Step 6：此处不文字追问；须调用 AskQuestion 展示上述 3 个选项卡，然后结束本回合）
```

Step 7 完成后追加：

```markdown
## 执行结果
- 实际 git log
- 与预期的差异（如有）
```

## 附加资源

- 工作区摘要（Windows）：[scripts/summarize-working-tree.ps1](scripts/summarize-working-tree.ps1)
- 工作区摘要（Bash）：[scripts/summarize-working-tree.sh](scripts/summarize-working-tree.sh)
