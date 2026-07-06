# Tasks（任务过程留痕）

本目录保存**大型任务的 Plan、Debug 笔记与经验教训**，让计划与踩坑过程不再随聊天记录消失，可被后续任务与 commit 检索复用。

## 何时建文件

满足任一条件即在开工前建一份 Plan 文档：

- 预计修改 > ~30 行代码，或涉及多个文件 / 模块；
- 需要多轮 Debug 的问题排查；
- 任何值得留痕的架构调整或关键功能开发。

小改动（单文件、几行）无需建档。

## 命名

```
.cursor/tasks/YYYY-MM-DD-<slug>.md
```

例：`.cursor/tasks/2026-07-01-auth-oauth-flow.md`。同日多任务用不同 slug。

## 生命周期

1. **开工**：复制 [`TEMPLATE.md`](TEMPLATE.md) 生成文档，填 Problem / 思路 / 受影响文件 / 分步计划，经用户确认后动手（可用 `task-plan` skill 自动生成）。
2. **过程**：卡点或设计变更时，追加到 `## Debug Notes`。
3. **收尾**：填写 `## Lessons Learned`，并回写 `.cursor/memories/activeContext.md`（下一步）与 `progress.md`（进展）。
4. **提交**：commit 时在 message 的 `Refs:` 引用本文件路径（见 `rules/safety/git-permissions.mdc`，或调用 `git-agent`）。

## 归档

任务完成且经验已沉淀进 Memory Bank 后，Plan 文档可保留作为历史检索；无需删除。数量过多时可移入 `.cursor/tasks/archive/`。
