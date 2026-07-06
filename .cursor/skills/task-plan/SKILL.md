---
name: task-plan
description: >-
  Scaffold a task plan document before starting a large task. Read the Memory Bank for
  context, then create .cursor/tasks/YYYY-MM-DD-<slug>.md from the template with Problem,
  approach, affected files, and a step-by-step plan, and wait for user confirmation before
  coding. Use when the user starts a big/multi-file task or asks to plan a task, 立 plan,
  任务计划, 开工前建计划, task plan, plan this task, 建任务文档. Not for generating commit
  workflows (use git-agent) or refreshing the Memory Bank (use memory-update).
disable-model-invocation: true
---

# Task Plan

大型任务开工前的脚手架：先读 Memory Bank 建立上下文，再依模板在 `.cursor/tasks/` 生成 Plan 文档，输出分步计划**待用户确认后再写代码**。

配套约定见 [`.cursor/rules/workflow/ai-workflow.mdc`](../../rules/workflow/ai-workflow.mdc)；文档结构见 [`.cursor/tasks/TEMPLATE.md`](../../tasks/TEMPLATE.md)。

## 关键约束

1. **本 skill 只产出 Plan 文档，不写业务代码。** 生成计划后停下，等用户确认。
2. **不执行任何 git 写操作。** Git 工作流交给 `git-agent`。
3. 若任务确属小改动（单文件、几行），提示用户可跳过建档，直接实现。

## Workflow

复制 checklist 并逐项完成：

```
- [ ] Step 1: 读取 Memory Bank 上下文
- [ ] Step 2: 与用户确认任务范围与命名
- [ ] Step 3: 依模板生成 Plan 文档
- [ ] Step 4: 输出分步计划，等待确认
```

### Step 1 — 读取 Memory Bank（只读）

至少读 `.cursor/memories/activeContext.md`；涉及架构/新模块再读 `projectbrief.md`、`systemPatterns.md`、`techContext.md`。
提炼：与本任务相关的现有约束、模式、进行中工作、待决问题。若 `.cursor/memories/` 不存在，提示用户是否先初始化（参考 memories/README.md），可继续但记忆上下文缺失。

### Step 2 — 确认范围与命名

- 归纳任务的 Problem 与目标（1～2 句）。
- 生成文件名 `.cursor/tasks/YYYY-MM-DD-<slug>.md`：日期取当天，slug 用简短英文短横线（如 `auth-oauth-flow`）。
- 若同名已存在，slug 追加序号或改用更具体描述。

### Step 3 — 生成 Plan 文档

复制 [`TEMPLATE.md`](../../tasks/TEMPLATE.md) 内容写入新文件并填充：

- **Problem / 目标**：结合 Memory Bank 给足背景。
- **核心思路**：方案与关键取舍，说明为什么这么做。
- **受影响的文件 / 模块**：尽量具体到路径。
- **分步计划**：可勾选的有序步骤。
- `## Debug Notes` 与 `## Lessons Learned` 留空骨架，供后续追加。

### Step 4 — 输出并等待确认

在回复中展示 Plan 摘要与文件路径，明确询问：是否认可计划、是否可以开始实现。**得到确认前不写业务代码。**

## 回复结构

```markdown
## 上下文摘要
- 来自 Memory Bank 的相关约束 / 进行中工作

## 已创建 Plan 文档
- 路径：.cursor/tasks/YYYY-MM-DD-<slug>.md

## 分步计划
- Step 1 / Step 2 / ...

---
请确认：是否认可该计划？是否可以开始实现？（确认前不会写业务代码）
```
