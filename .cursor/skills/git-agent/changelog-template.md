# Changelog 写入模板

写入 [`docs/changelog.md`](../../../docs/changelog.md) 时，在文件**顶部**插入以下结构（保留下方历史记录）：

```markdown
## Reorganize YYYY-MM-DD

### 重组范围

| Hash | 原 Subject | 判定 |
|------|------------|------|
| `abc1234` | wip: auth step | 临时标记 |
| `def5678` | refact: move old code | 类型拼写错误 |

基线（重组 parent）：`<parent-hash>` (`<short>`)

### 变更总结

- **主题 1**：…
- **主题 2**：…

### 涉及文件（按模块）

- `path/to/module`: 简述

### 目标 commit 列表（分组）

| 顺序 | 推荐 Message | 原 Commit 集合 | 涉及模块 | 排序理由 |
|------|--------------|----------------|----------|----------|
| 1 | `refactor(core): simplify auth flow` | `abc1234`, `def5678` | core | 同一意图合并 |

### 推荐 commit message

```
type(scope): subject

Why: ...
How: ...
Refs: .cursor/tasks/<plan>.md
```

### 重组方案

**策略**：soft reset 重提（默认） / rebase -i

| 原 Hash | 操作 | 说明 |
|---------|------|------|
| `abc1234` | → commit 1 | soft reset 后第一批 add |

```bash
# 需用户确认后执行
git reset --soft <parent-hash>
git add <paths-for-commit-1>
git commit -m "$(cat <<'EOF'
type(scope): subject

Why: ...
How: ...
Refs: .cursor/tasks/<plan>.md
EOF
)"
```

预期：N 个 commit → M 个 commit

### 状态

- [ ] 用户已确认重组方案
- [ ] 重组执行完成
- [ ] 最终 git log 已对照预期
- [ ] 如为里程碑，已同步 `.cursor/memories/progress.md`

---

```

若 `docs/changelog.md` 不存在，创建文件并加上一级标题 `# Changelog`。
