---
name: memory-update
description: >-
  Refresh the project Memory Bank at a milestone. Scan recent changes, task plans and
  commits, then incrementally update .cursor/memories/activeContext.md and progress.md
  (and systemPatterns.md / decisions when architecture changed), archiving stale detail
  and keeping only conclusions. Use when the user says update memory bank, refresh context,
  刷新记忆, 更新数字大脑, 更新 memory bank, 里程碑总结, sync memory, or after finishing a
  milestone. Not for scaffolding a new task plan (use task-plan) or git workflows
  (use git-agent).
disable-model-invocation: true
---

# Memory Update

里程碑/重大节点时增量刷新 Memory Bank，让 `.cursor/memories/` 始终反映项目当前真实状态，同时把过时细节归档、只留结论，避免记忆膨胀。

记忆系统层级与维护原则见 [`.cursor/memories/README.md`](../../memories/README.md)；触发时机见 [`.cursor/rules/workflow/ai-workflow.mdc`](../../rules/workflow/ai-workflow.mdc)。

## 关键约束

1. **增量更新，不推倒重写。** 保留仍成立的内容，只改动确有变化处。
2. **写 rationale，不抄代码。** 能从代码读到的事实不重复；重点是“为什么”“下一步”。
3. **不执行 git 写操作**，不改业务代码。仅编辑 `.cursor/memories/` 下文档。
4. **改动前先展示 diff 计划**，重大删改经用户确认后再写。

## Workflow

复制 checklist 并逐项完成：

```
- [ ] Step 1: 收集近期信号（只读）
- [ ] Step 2: 对照现有记忆找差异
- [ ] Step 3: 提出更新方案
- [ ] Step 4: 确认后写入记忆文件
```

### Step 1 — 收集近期信号（只读）

- `git log --oneline -n 20` 与（如有）`git diff --stat`，了解近期变更主题。
- 读 `.cursor/tasks/` 最近的 Plan 文档，尤其 `Debug Notes` 与 `Lessons Learned`。
- 读现有 `.cursor/memories/activeContext.md`、`progress.md`（必要时 `systemPatterns.md`）。

### Step 2 — 找差异

对比“实际发生的变化”与“记忆里记录的状态”，列出：

- `activeContext.md`：当前焦点是否已转移？近期变更、下一步是否过时？
- `progress.md`：哪些从“进行中/待办”变为“已完成”？新增了哪些已知问题？是否达成里程碑？
- `systemPatterns.md`：是否有架构/关键决策变化？是否需要新增 ADR。
- 哪些旧细节应归档或模糊化。

### Step 3 — 更新方案

输出将要修改的文件与要点（分文件列出“加/改/删”），标注需用户确认的重大删改。

### Step 4 — 写入

用户确认后，逐文件增量编辑：

- 更新对应文件顶部的“最近更新：YYYY-MM-DD”。
- `activeContext.md`：刷新当前焦点 / 近期变更 / 下一步 / 待决问题。
- `progress.md`：迁移完成项、补充已知问题、必要时在“里程碑记录”加一行。
- 架构变化 → 更新 `systemPatterns.md`；重大决策 → 新增 `decisions/NNNN-*.md`。
- 关联的 Plan 文档若已收尾，将结论要点回流到记忆，并可将其状态标为“已完成”。

## 回复结构

```markdown
## 近期信号
- 来自 log / task 文档 / diff 的关键变化

## 记忆差异
- 各文件需更新的点

## 更新方案
- 逐文件：加 / 改 / 删（重大删改标注需确认）

---
（确认后写入；仅修改 .cursor/memories/ 文档，不动代码与 git 历史）
```
