# Memory Bank（项目数字大脑）

本目录是项目的**持久化记忆**：把“架构意图、设计理念、关键决策、当前进展”等无法从代码直接推断的信息，沉淀成结构化文档，供人和 AI 在每次会话开始时快速重建对项目的理解。

> 核心理念：代码是「怎么做」的真理来源；Memory Bank 是「为什么这么做」的真理来源。

## 文件层级

文件自上而下逐层派生，`activeContext.md` 更新最频繁：

```
projectbrief.md      ← 基石：目标、范围、核心需求
├── productContext.md   ← 为什么做、解决什么问题、设计理念
├── systemPatterns.md   ← 架构、关键技术决策、组件关系
└── techContext.md      ← 技术栈、依赖、环境约束
        └── activeContext.md  ← 当前焦点、近期变更、下一步（最常更新）
                └── progress.md   ← 已完成 / 待办 / 已知问题 / 里程碑
decisions/           ← ADR：单条重大决策的“为什么”，含被否决的备选方案
```

## 读写时机

- **任务开始**：至少读 `activeContext.md`；涉及架构/新模块再读 `projectbrief.md`、`systemPatterns.md`。
- **过程中**：重大决策 → 新增一条 `decisions/NNNN-*.md`；架构变化 → 更新 `systemPatterns.md`。
- **里程碑/收尾**：用 `memory-update` skill 增量刷新 `activeContext.md` 与 `progress.md`，把过时细节归档、只留结论。

## 维护原则

- **短而精**：单文件尽量精炼，最重要的信息放最前；过长会被模型忽略。
- **写 rationale，不罗列事实**：能从代码读到的别抄，重点写“为什么”“为什么不选另一方案”。
- **随代码演进**：这些文件纳入 git，和代码一起提交、一起 review。

## AI 会话入口

任务开始时优先读本目录（至少 `activeContext.md`），无需再读项目根目录下的旧文档。

历史文档已归档至 `.cursor/bakup/`：

| 备份路径 | 原内容 |
|----------|--------|
| `.cursor/bakup/doc/` | project-context、design-overview、software-architecture、data-protocol、deployment、frontend |
| `.cursor/bakup/TODO/` | backend 实施计划（已迁移为 `.cursor/tasks/2026-07-06-backend-implementation.md`） |
| `.cursor/bakup/ignored/TALK_WITH_AI.md` | 原始 AI 设计讨论（2000+ 行） |
