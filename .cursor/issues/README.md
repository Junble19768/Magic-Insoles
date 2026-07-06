# Issues（需求冷钱包）

本目录保存**本地 issue 作为“冷钱包”**，把灵感、bug、需求暂存起来，不立即修复、不打断当前开发主线。后期再批量评估、关联处理，避免过度开发与上下文污染。

核心理念：**捕获（capture）与消灭（resolve）分离**。批量处理优于单点突破。

## 何时建文件

仅当用户使用暂存类措辞时才建 issue：

- “记个 issue”、“先记下来”、“以后再修”、“暂存这个”、“log an issue”、“stash this”、“file an issue”等。

默认情况下，报告问题仍按正常流程处理（小改动直接做，大改动用 `task-plan`）。

小问题或即时可修的无需建 issue。

## 命名

```
.cursor/issues/issue-NNNN-<slug>.md
```

例：`.cursor/issues/issue-0001-login-dark-mode.md`。使用四位零填充编号（从 0001 开始），同批可不同 slug。

## 生命周期

1. **捕获**：使用 `issue-log` skill 生成文件，填 frontmatter（id/status/priority/tags/created/related）和现象/期待/背景。**只登记、不写代码、不 commit**。
2. **暂存期**：可追加讨论或上下文到 issue 文件（可选）。
3. **批量消灭**：用户显式触发（清理/批量修 issue 等），调用 `issue-sweep` skill。skill 会评估关联性、分组，然后委托 `task-plan` 生成批量修复 Plan；实现后将对应 issue 设为 `closed`，并写 `resolved-by`。
4. **提交**：经 `git-agent` 提交，message 包含 `Fixes: #0001, #0002`（自动关联）。

## 状态

- `open`：待处理
- `in-progress`：正在批量处理中
- `closed`：已解决
- `wontfix`：决定不修复（sweep 时可集中确认关闭）

## 归档

issue 完成（或明确 wontfix）后可保留作为历史检索；无需删除。数量过多时可移入 `.cursor/issues/archive/`。

## 关联

- issue 可在 `.cursor/tasks/` Plan 文档的「关联」字段引用。
- commit / git-agent 会自动在 message 引用 `Fixes: #NNNN`。
- 必要时在 `.cursor/memories/` 中记录可复用的教训（通过 `memory-update` skill）。

配套规则见 [`.cursor/rules/workflow/ai-workflow.mdc`](../rules/workflow/ai-workflow.mdc)；捕获用 `issue-log` skill，批量处理用 `issue-sweep` skill；模板见 [`TEMPLATE.md`](TEMPLATE.md)。