---
name: git-commit-reorganize
description: >-
  Reorganize recent non-standard or temporary git commits: summarize changes by module,
  write docs/changelog.md, propose grouped commit messages and reorganization plans,
  and after user confirmation replace commits via soft reset or rebase. Use when the
  user asks to reorganize commits, git commit reorganize, squash messy commits, merge
  com1/comN commits, clean up commits before push, 整理 commit, or 重组 commit history.
  Also applies for commit review when the goal is to clean up history before push.
  Not for uncommitted working-tree changes (use git-commit-propose).
disable-model-invocation: true
---

# Git Commit Reorganize

整理近期不规范或临时 commit，按模块分组输出重组方案；**用户确认前只分析与建议，确认后才执行改历史。**

工作区未提交改动需生成 commit message 时，使用 [git-commit-propose](../git-commit-propose/SKILL.md)，勿与本 skill 混用。

Git commit 格式标准与安全准则见 [`.cursor/rules/git-workflow.mdc`](../../rules/git-workflow.mdc)。

## 触发后先确认范围

若用户未指定 commit 范围，默认扫描最近 **30** 条；若用户给了数量或 hash 范围，以其为准。

可选：运行候选检测脚本缩小范围：

```powershell
# Windows（优先）
.\.cursor\skills\git-commit-reorganize\scripts\find-candidate-commits.ps1 [-Count 30]
```

```bash
# Git Bash / Linux / macOS
.cursor/skills/git-commit-reorganize/scripts/find-candidate-commits.sh [N]
```

## Workflow

复制 checklist 并逐项完成：

```
- [ ] Step 1: 选定并读取候选 commit
- [ ] Step 2: 总结变更
- [ ] Step 3: 生成分组与目标 commit 列表
- [ ] Step 4: 写入 docs/changelog.md
- [ ] Step 5: 输出推荐 commit message
- [ ] Step 6: 输出重组方案
- [ ] Step 7: 停止，等待用户确认
- [ ] Step 8: 用户确认后执行重组（可选）
```

### Step 1 — 选定并读取候选 commit

**纳入重组**的 commit 满足任一条件：

- subject 不符合 `type(scope): subject` 或 type 不在白名单（`feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`）
- 类型拼写错误（如 `refact` → 应建议 `refactor`）
- 含临时/占位标记：`com1`、`comN`、`tmp`、`wip`、`fixup`、`squash!`、`first`、`second`、`init` 等（大小写不敏感）
- 单词或无动词 subject（如 `doc`）
- 用户明确点名的 commit

**排除**（除非用户要求）：已符合规范且语义清晰的 commit（如 `feat(oauth): implement Luogu OAuth flow...`）。

对每个候选 commit 只读执行：

```bash
git log --format='%H %h %s' <range>
git show --stat <hash>
git show <hash> --no-color
```

记录：hash、原 subject、变更文件、功能归属（scope 推断）。

### Step 2 — 总结变更

按**逻辑主题 / 功能模块**归纳（不要按 commit 序号罗列），例如：

- 新增 / 修改了哪些模块
- 行为变化、API 变化、数据流变化
- 是否含文档、测试、配置
- 模块间依赖顺序（例如：目录结构调整 → 后端能力 → 前端对接 → 文档）
- 有无未完成或实验性内容（需 squash 的片段）

### Step 3 — 多 commit 分组策略

输出「目标 commit 列表」，每条包含：message、涵盖的原 commit、涉及路径、排序理由。

分组原则：

1. **按模块聚合**：`backend/`、`frontend/`、`docs/`、`3rdparty/`、`config.yml` 等分开。
2. **按依赖顺序排列**：结构/配置/refactor 在前，功能 feat 居中，docs/chore 可置后。
3. **能合并则合并**：同一模块、同一意图的临时 commit 合成 1 条；跨模块但强耦合的可保留在同一 commit 并说明原因。
4. **预期条数**：优先 1～3 条；只有模块/阶段确实独立时才拆更多。

scope 从路径推断，参考映射：

```text
backend/          → backend
frontend/         → frontend
3rdparty/         → 3rdparty 或 crawler
docs/             → docs
config.yml        → config
根目录环境/CI      → chore
```

### Step 4 — 写入 docs/changelog.md

使用 [changelog-template.md](changelog-template.md) 结构写入或追加 [`docs/changelog.md`](../../../docs/changelog.md)。

- 每次重组在文件顶部插入新的 `## Reorganize YYYY-MM-DD` 区块
- **保留**历史重组记录，不要覆盖旧内容
- 若文件不存在则创建（含 `# Changelog` 一级标题）

### Step 5 — 推荐 commit message

为**每个目标 commit** 给出 1 条首选 + 最多 1 条备选，格式严格遵守 [git-workflow.mdc](../../rules/git-workflow.mdc)：

```
type(scope): subject
```

- subject 动词开头、≤50 字；细节放在 changelog 正文，不要塞进 subject
- 参考仓库早期规范 commit 风格，不要延续 `comN` 命名

在回复中按目标 commit 分组列出「首选」与「备选」。

### Step 6 — 重组方案

**Step 7 之前只输出计划，不执行。** 按场景选择策略：

| 场景 | 推荐方式 |
|------|----------|
| 连续 N 个待整理 commit | **soft reset 重提**（默认）：`git reset --soft <baseline>` → 按分组 `git add` + `git commit` |
| 仅需合并/改 message、中间有需保留 commit | `git rebase -i <baseline>`，表中标注 pick/squash/fixup/reword |
| 已推送分支 | 说明需用户确认后再考虑 `git push --force-with-lease`（**禁止 agent 自动执行**） |

方案须包含：

1. **基线 commit**（第一个待整理 commit 的 parent hash）
2. **操作表**：每个原 commit → `pick` / `squash` / `fixup` / `drop` / `reword`（rebase 路径）或对应的目标 commit 序号（soft reset 路径）
3. **预期结果**：最终 commit 数量、顺序与 message 列表
4. **风险**：是否已 push、是否有未提交改动、是否与其他分支冲突

soft reset 执行示例（计划阶段仅展示，不运行）：

```bash
git reset --soft <baseline>
git add <paths-for-commit-1>
git commit -m "type(scope): subject"
git add <paths-for-commit-2>
git commit -m "type(scope): subject"
```

### Step 7 — 停止并等待用户确认

完成 Step 1～6 后**必须停止**，在回复末尾明确询问：

- 是否同意 changelog 内容
- 是否采纳各组 commit message（首选或备选）
- 是否授权执行重组方案

**在用户确认之前，不得运行：** `git rebase`、`git commit --amend`、`git reset`、`git push --force`、`git push --force-with-lease`。

### Step 8 — 用户确认后执行重组

仅在用户逐条确认后：

1. 再次 `git status`；有未提交改动则先处理或中止。
2. 按 Step 6 方案执行（连续待整理 commit 优先 soft reset 路径）。
3. 每创建一个 commit 前展示 `git diff --cached --stat`。
4. 完成后 `git log --oneline` 对照预期。
5. 更新 `docs/changelog.md` 中对应重组区块的状态 checklist。
6. 若分支曾 push，提示用户自行决定是否 `git push --force-with-lease`（**禁止 agent 自动 force push**）。

**禁止运行：** `git reset --hard`、`git push --force`（不带 `-with-lease`）。

## 回复结构（给用户）

```markdown
## 重组范围
- 候选 commit 列表

## 变更总结
- 主题化要点（含模块依赖顺序）

## 目标 commit 列表（分组）
- 顺序 / message / 原 commit 集合 / 涉及模块

## Changelog
- 已写入 docs/changelog.md（附路径）

## 推荐 commit message
- 每组：首选 / 备选

## 重组方案
- 基线 / 策略（soft reset 或 rebase -i）/ 操作表 / 预期结果 / 风险

---
请确认：是否采纳 changelog 与各组 commit message？是否授权执行重组？（确认前不会修改 git 历史）
```

Step 8 完成后追加：

```markdown
## 执行结果
- 实际 git log
- 与预期的差异（如有）
- push 提示（如适用）
```

## 附加资源

- Changelog 模板：[changelog-template.md](changelog-template.md)
- 候选检测（Windows）：[scripts/find-candidate-commits.ps1](scripts/find-candidate-commits.ps1)
- 候选检测（Bash）：[scripts/find-candidate-commits.sh](scripts/find-candidate-commits.sh)
