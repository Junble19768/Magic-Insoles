---
name: issue-log
description: >-
  Capture a lightweight local issue into .cursor/issues/ without fixing anything.
  Turn a one-line bug/idea into issue-NNNN-<slug>.md from the template, auto-assign
  the next NNNN. Use ONLY when the user wants to stash/defer: 记个 issue, 先记下来,
  以后再修, 暂存这个, log an issue, stash this, file an issue. Never triggers a fix,
  never edits code, never commits. For actually resolving issues use issue-sweep.
disable-model-invocation: true
---

# Issue Log（需求冷钱包 · 捕获）

把一个想法/bug 极轻量地锁进 `.cursor/issues/`，**只登记、不修复**——保护当下开发主线不被打断。理念见 [`.cursor/issues/README.md`](../../issues/README.md)。

## 关键约束
1. **只建文件**：绝不改业务代码、不 commit、不启动修复。
2. 若用户其实想"现在就修"，提示改走正常流程或 `task-plan`，不要建 issue。
3. 编号：扫描 `.cursor/issues/issue-*.md` 取现有最大 `id` + 1，四位零填充（0001 起）。

## Workflow
```
- [ ] Step 1: 一句话提炼标题 + 现象/期待
- [ ] Step 2: 分配下一个 NNNN
- [ ] Step 3: 依模板生成 .cursor/issues/issue-NNNN-<slug>.md
- [ ] Step 4: 汇报路径与编号，结束（不修复）
```

### Step 1 — 提炼内容（只读）
- 从用户输入中归纳：**一句话标题**、**现象**（发生了什么、在哪）、**期待**（应该怎样）。
- 询问/推断 `priority`（low/medium/high，默认 medium）和 `tags`（如 ui、auth、perf）。
- 相关联的已有 issue / task / ADR 可填 `related`。

### Step 2 — 分配编号
- 只读扫描 `cursor/issues/` 下 `issue-*.md` 的 frontmatter `id`。
- 取最大值 +1，格式化为四位零填充（如 0001、0012）。
- 生成 slug：标题转 kebab-case 短语（如 `login-button-dark-mode`）。
- 若同日/同名冲突，slug 追加序号或更具体描述。
- 文件名：`issue-NNNN-<slug>.md`

### Step 3 — 生成文件
- 复制 [`TEMPLATE.md`](../../issues/TEMPLATE.md) 内容写入新文件并填充：
  - frontmatter：`id`、`status: open`、`priority`、`tags`、`created: <今日>`、`related`
  - `# <标题>`
  - `- **现象**：...`
  - `- **期待**：...`
  - `- **背景**：...`（可选）
- 关闭字段注释留在文件内，供后续使用。

### Step 4 — 汇报并结束
- 在回复中展示创建的 issue 编号、路径、摘要。
- **明确说明：未做任何代码改动、不提交。**
- 提示：攒够一批后可用 `issue-sweep` 批量处理。

## 回复结构
```markdown
已登记 issue #NNNN：<标题>
- 路径：.cursor/issues/issue-NNNN-<slug>.md
- 状态：open / 优先级：<low|medium|high> / tags: [...]
（未做任何代码改动。攒够了用 issue-sweep 批量处理。）
```
```