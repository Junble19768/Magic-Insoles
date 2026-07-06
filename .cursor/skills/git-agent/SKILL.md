---
name: git-agent
description: >-
  Autonomous git agent for small fast commits, commit cleanup, and branch/push workflows.
  Modes: commit (default: analyze working tree, split by small feature point, then git add
  and git commit autonomously), reorganize (clean up wip/temporary/non-standard commits with
  explicit high-risk confirmation), branch (create/switch/merge branches with AskQuestion
  confirmation). Use when the user asks commit, 提交当前修改, git agent, 整理 commit,
  squash wip, branch workflow, push, or git 工作流.
disable-model-invocation: true
---

# Git Agent

一个统一 Git 代理，集中处理提交、提交历史整理、分支与推送工作流。权限边界以 [git-permissions](../../rules/safety/git-permissions.mdc) 为准：`git add`/`git commit` 可自主执行；普通 `push` 与 branch 操作用 `AskQuestion`；改历史/force-with-lease 走高危确认流程。

## Mode Selection

- **commit（默认）**：处理工作区未提交改动，小步快跑地分组提交。
- **reorganize**：整理 `wip`、`tmp`、`comN`、`fixup`、不规范 message 等历史提交。属于改历史，必须先给方案并确认。
- **branch**：创建、切换、合并、删除、设置 upstream，必须用 `AskQuestion` 确认。

## Mode: commit（自主小步提交）

目标：一个小功能点/修复点/重构点一条 commit，避免“大而全”的提交。

Checklist：

```
- [ ] Step 1: 读取工作区与上下文
- [ ] Step 2: 按小功能点分组
- [ ] Step 3: 生成 commit message
- [ ] Step 4: 自主 git add + git commit
- [ ] Step 5: 汇报结果；如需 push，用 AskQuestion
```

### Step 1 — 读取

只读执行：

```bash
git status
git diff --stat
git diff --cached --stat
git diff
git diff --cached
```

可选摘要脚本：

```powershell
.\.cursor\skills\git-agent\scripts\summarize-working-tree.ps1 [-Paths <path1>,<path2>]
```

同时读取最近的 `.cursor/tasks/` Plan 文档（如有），提取 `Problem`、`核心思路`、`Lessons Learned`，作为 `Why`/`How`/`Refs` 来源。

### Step 2 — 分组

- 按逻辑主题/小功能点分组，不按文件字母序。
- 优先小而完整：一条 commit 应该能独立表达一个意图。
- 不提交 secrets、临时文件、大型生成物、无关用户改动。
- 若工作区含明显互不相关改动，拆成多条 commit；如存在冲突或不确定归属，先询问。

### Step 3 — Message

格式：

```text
type(scope): subject

Why: ...
How: ...
Refs: .cursor/tasks/<plan>.md
Fixes: #0001, #0002      # 若本次提交关闭了 issue
```

琐碎改动可省略 body。多行 message 必须用 HEREDOC。

### Step 4 — 执行

无需用户确认即可按组执行：

```bash
git add <paths-for-commit-1>
git diff --cached --stat
git commit -m "$(cat <<'EOF'
type(scope): subject

Why: ...
How: ...
Refs: .cursor/tasks/<plan>.md
Fixes: #0001, #0002      # 若本次提交关闭了 issue
EOF
)"
```

每条 commit 前确认 staged 内容只属于当前组。不得自动 `push`。

## Mode: reorganize（高危）

用于整理近期临时/不规范 commit。默认扫描最近 30 条，可用：

```powershell
.\.cursor\skills\git-agent\scripts\find-candidate-commits.ps1 [-Count 30]
```

流程：

1. 只读分析 `git log` / `git show` / 相关 `.cursor/tasks/` / `.cursor/memories/progress.md`。
2. 输出目标 commit 列表、message、基线、操作表、风险、完整命令。
3. 用 `AskQuestion` 确认是否执行。确认前不得运行 `rebase`、`reset`、`commit --amend`。
4. 执行后更新 `docs/changelog.md`（模板见 `changelog-template.md`）；若是里程碑，同步引用 `.cursor/memories/progress.md`。
5. 若分支已 push，只提示 `push --force-with-lease` 需要单独确认；禁止 `push --force`。

## Mode: branch（确认）

所有 branch 操作（create/switch/merge/delete/upstream）先给出：

- 当前分支与状态
- 目标操作与命令
- 风险（未提交改动、冲突、远程影响）

然后必须调用 `AskQuestion`。确认后才执行。

## Safety

- Never run `git reset --hard`.
- Never run `git push --force` without lease.
- Never update git config.
- Never skip hooks unless explicitly requested by the user.
- Do not push unless the user confirmed via `AskQuestion`.
