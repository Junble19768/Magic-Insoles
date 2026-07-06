# Changelog 写入模板

写入 [`docs/changelog.md`](../../../docs/changelog.md) 时，在文件**顶部**插入以下结构（保留下方历史记录）：

```markdown
## Reorganize YYYY-MM-DD

### 重组范围

| Hash | 原 Subject | 判定 |
|------|------------|------|
| `abc1234` | com1 | 临时标记 |
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
| 1 | `refactor(3rdparty): move legacy crawler` | `abc1234`, `def5678` | 3rdparty | 结构调整优先 |
| 2 | `feat(oauth): implement Luogu OAuth flow` | `ghi9012` | backend | 依赖目录就位后 |

### 推荐 commit message

**目标 commit 1 — 首选**

```
type(scope): subject
```

**目标 commit 1 — 备选**

```
type(scope): subject
```

### 重组方案

**策略**：soft reset 重提（默认） / rebase -i

| 原 Hash | 操作 | 说明 |
|---------|------|------|
| `abc1234` | → commit 1 | soft reset 后第一批 add |
| `def5678` | → commit 1 | 与上合并 |
| `ghi9012` | → commit 2 | 独立功能 commit |

```bash
# soft reset 路径（需用户确认后执行）
git reset --soft <parent-hash>
git add <paths-for-commit-1>
git commit -m "type(scope): subject"
```

```bash
# rebase -i 路径（中间有需保留 commit 时）
git rebase -i <parent-hash>
```

预期：N 个 commit → M 个 commit

### 状态

- [ ] 用户已确认 changelog
- [ ] 用户已选定各组 commit message
- [ ] 用户已授权执行重组
- [ ] 重组执行完成
- [ ] 最终 git log 已对照预期

---

```

若 `docs/changelog.md` 不存在，创建文件并加上一级标题 `# Changelog`。
