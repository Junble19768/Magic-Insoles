---
name: issue-sweep
description: >-
  Batch-resolve open local issues. Scan .cursor/issues/ for status:open, assess
  relatedness, group them, then delegate to task-plan for a batch fix plan; after
  fixing, flip each issue to closed with resolved-by, and commit via git-agent with
  Fixes: #NNNN. Use when the user says 清理 issues, 批量修 issue, 消灭 issues, sweep
  issues, resolve open issues, 处理 issue. For capturing a new issue use issue-log.
disable-model-invocation: true
---

# Issue Sweep（批量消灭）

阶段性把 `.cursor/issues/` 里 `open` 的 issue 打包解决，践行"批量处理优于单点突破、避免过度开发"。

配套理念见 [`.cursor/issues/README.md`](../../issues/README.md)；触发时机与规则见 [`.cursor/rules/workflow/ai-workflow.mdc`](../../rules/workflow/ai-workflow.mdc)。

## 关键约束
1. **只在用户显式触发时执行**：默认不主动消灭 issue。
2. **先立计划**：必须通过 `task-plan` skill 生成批量修复 Plan，**得到用户确认后**才实现。
3. **不直接写业务代码**：本 skill 负责协调扫描、分组、状态更新与提交委托。
4. 仅当有可复用教训时才调用 `memory-update` 回流，避免记忆膨胀。

## Workflow
```
- [ ] Step 1: 扫描 open issues（只读）
- [ ] Step 2: 按关联性分组、排优先级
- [ ] Step 3: 调 task-plan 生成批量修复 Plan（关联列出各 issue 路径），待确认
- [ ] Step 4: 确认后实现
- [ ] Step 5: 每个已修 issue：status→closed，追加 closed / resolved-by
- [ ] Step 6: 调 git-agent 提交（message 带 Fixes: #NNNN, #NNNN）；有可复用教训则 memory-update
```

### Step 1 — 扫描（只读）
- 列出 `.cursor/issues/issue-*.md` 中 `status: open` 的文件。
- 读取每个的 frontmatter（id, priority, tags, created, related）与标题、现象/期待。
- 同时可读近期 `.cursor/tasks/` Plan 与 `git log` 了解上下文（可选）。

### Step 2 — 分组与优先级
- 按模块/主题/关联性分组（例如同属 auth 模块的多个 UI issue 合并成一次重构）。
- 避免把互相冲突的改动拆成多次修复。
- 输出分组结果 + 建议优先级（尊重原 issue priority）。

### Step 3 — 委托立计划
- 调用 `task-plan` skill（或手动依 TEMPLATE），让它为本次批量修复生成一个 Plan 文档。
- Plan 中「关联」字段必须列出本批所有 issue 路径（如 `.cursor/issues/issue-0001-*.md`）。
- 在 Plan 的 Problem / 核心思路中体现“一次性解决以下 issues”。
- **输出 Plan 路径后，等待用户明确确认**，确认前不写业务代码。

### Step 4 — 实现
- 按确认后的 Plan 写代码、测试。
- 过程中如需，可将相关 issue 临时标为 `in-progress`（可选，便于追踪）。
- 保持小步提交（可用 `git-agent` 的 commit 模式）。

### Step 5 — 关闭 issue
- 对每个已解决的 issue：
  - 把 `status` 改为 `closed`
  - 在 frontmatter 追加：
    ```
    closed: <YYYY-MM-DD>
    resolved-by: .cursor/tasks/<本次plan>.md
    ```
- `wontfix` 的 issue 在 sweep 时可集中询问是否关闭（不改代码）。
- 不删除文件；数量多时提示用户是否归档到 `archive/`。

### Step 6 — 提交与回流
- 调用 `git-agent`（或按其规范手动）生成提交：
  - message 包含 `Fixes: #0001, #0002`（列出本次关闭的所有 issue）。
- 若本次修复沉淀了可复用的模式、坑或决策，调用 `memory-update` skill 增量刷新 `.cursor/memories/`。
- 否则仅提交即可，避免不必要的记忆更新。

## 回复结构
```markdown
## 本批 open issues
- #0001 <标题> [tags] / #0002 ...

## 分组与计划
- 组 A（同属 auth）：#0001 #0003 → 一次重构
- → 交由 task-plan 生成 Plan：.cursor/tasks/YYYY-MM-DD-<slug>.md

（确认计划后实现；修完自动关闭 issue 并经 git-agent 提交）
```
```