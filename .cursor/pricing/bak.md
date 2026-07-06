| **任务级别**                               | **核心业务场景定义**                                         | **包含模型 (你提供的 29 款)**                                | **选型底层逻辑**                                             | **备注与避坑指南**                                           |
| ------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| Tier 1 微调与高频改动 *(Micro-Edits)*      | • 行内代码单行补全 (Tab) • 单一函数的单元测试 (UT) • 正则表达式生成 / JSON 转换 • 修改简单的 Lint 语法报错 | * **GPT-5 Mini / 5.4 Mini / 5.4 Nano** * **Codex 5.1 Mini / 5.2 / 5.3** * **Gemini 3 Flash / 3.5 Flash** * **Gemini 2.5 Flash** * **Haiku 4.5** | **追求毫秒级响应与极限低成本。** 这个级别的模型通常被 IDE 部署在网络边缘端或高频流式传输通道（如 Tab 预测）。它们不需要进行逻辑思考，只要“背过”海量语法树即可。 | **【选型避坑】** • `Codex 5.3` 和 `GPT-5 Mini` 是高频 Tab 补全的黄金组合。 • `Gemini Flash` 系列虽然在这一层，但它因拥有巨量上下文，常被用作“项目文档扫描器”。 |
| Tier 2 标准模块开发 *(Everyday Dev)*       | • 编写标准 CURD 业务代码 • 前端通用组件抽离与拼装 • 熟练框架（Next.js/Spring）的常规 API 编写 • 侧边栏 Chat 日常代码答疑 | * **Sonnet 4 / 4.5** * **GPT-5.1 / 5.2** * **Codex 5.1 Max** * **Grok 4.3** * **Kimi K2.5** * **GLM 5.2** | **日常主力开发，性价比与规范性的黄金平衡。** 这些模型是日常编码的“中流砥柱”。它们的上下文遵从度极高，输出的代码格式非常规范，极少出现低级语法幻觉。 | **【选型避坑】** • 国内自备 API 推荐首选 `Kimi K2.5` 和 `GLM 5.2`，对中文注释和国内魔改框架（如微服务生态）理解极好。 • `Sonnet 4.5` 是日常常驻 Chat 面板最不容易出错的万金油。 |
| Tier 3 跨文件复杂重构 *(Deep Refactor)*    | • 涉及 3 个以上文件的 Bug 追踪 • 复杂老旧代码的依赖解耦 • 接入大型第三方复杂 SDK • 开启 **Agent 自动修 Bug** 循环 | * **Composer 2.5** *(Cursor 自研主力)* * **Sonnet 4.6 / 5** * **GPT-5.4** * **Grok Build 0.1** | **利用强化学习(RL)或中等推理，打赢 Agent 报错循环。** 这类任务需要模型频繁使用本地工具（读写文件、运行终端测试）。模型必须能在执行报错后，自动看懂报错并进行第二轮、第三轮的自我修正。 | **【选型避坑】** • `Composer 2.5` 是目前 Cursor 里的绝对核心。它通过 25 倍的合成任务强化学习训练，在工程多文件 Apply 成功率上极为恐怖，且速度极快。 • `Grok Build 0.1` 则是 X 平台阵营针对智能体编译推出的新秀，适合自动化流水线。 |
| Tier 4 盲区探索与高级架构 *(Arch & Logic)* | • 底层复杂算法设计（如多线程锁、协议重写） • 从零到一的全新项目技术选型与脚手架设计 • 排查极其隐蔽的内存泄漏、死锁、分布式事务故障 | * **Opus 4.5 / 4.6 / 4.7 / 4.8** * **GPT-5.5**               | **不计时间成本与 Token 价格，换取绝对的慢思考（Thinking）深度。** 这一层是研发的最后防线。模型在输出前会通过思维链（CoT）进行长达数秒甚至数十秒的逻辑推导。只有它们能看透复杂的抽象逻辑，避免普通模型在面对底层逻辑时的无限死循环。 | **【选型避坑】** • `Opus 4.8` 和 `GPT-5.5`（高推理模式）是目前的纯逻辑天花板。 • **严禁**将它们挂载为行内 Tab 补全或日常闲聊，因为不仅贵，且每说一句话都要让你等它“思考”好几秒，极度影响开发流畅度。 |

| 名称                                                         | 输入  | 缓存写入 | 缓存读取 | 输出  |
| :----------------------------------------------------------- | :---- | :------- | :------- | :---- |
| ![Anthropic](https://cursor.com/docs-static/images/providers/anthropic-light.svg)[Claude 4 Sonnet](https://cursor.com/docs/models/claude-4-sonnet) | $3    | $3.75    | $0.3     | $15   |
| ![Anthropic](https://cursor.com/docs-static/images/providers/anthropic-light.svg)[Claude 4 Sonnet 1M](https://cursor.com/docs/models/claude-4-sonnet-1m) | $6    | $7.5     | $0.6     | $22.5 |
| ![Anthropic](https://cursor.com/docs-static/images/providers/anthropic-light.svg)[Claude 4.5 Haiku](https://cursor.com/docs/models/claude-4-5-haiku) | $1    | $1.25    | $0.1     | $5    |
| ![Anthropic](https://cursor.com/docs-static/images/providers/anthropic-light.svg)[Claude 4.5 Opus](https://cursor.com/docs/models/claude-opus-4-5) | $5    | $6.25    | $0.5     | $25   |
| ![Anthropic](https://cursor.com/docs-static/images/providers/anthropic-light.svg)[Claude 4.5 Sonnet](https://cursor.com/docs/models/claude-4-5-sonnet) | $3    | $3.75    | $0.3     | $15   |
| ![Anthropic](https://cursor.com/docs-static/images/providers/anthropic-light.svg)[Claude 4.6 Opus](https://cursor.com/docs/models/claude-opus-4-6) | $5    | $6.25    | $0.5     | $25   |
| ![Anthropic](https://cursor.com/docs-static/images/providers/anthropic-light.svg)[Claude 4.6 Sonnet](https://cursor.com/docs/models/claude-4-6-sonnet) | $3    | $3.75    | $0.3     | $15   |
| ![Anthropic](https://cursor.com/docs-static/images/providers/anthropic-light.svg)[Claude 4.7 Opus](https://cursor.com/docs/models/claude-opus-4-7) | $5    | $6.25    | $0.5     | $25   |
| ![Anthropic](https://cursor.com/docs-static/images/providers/anthropic-light.svg)[Claude Fable 5](https://cursor.com/docs/models/claude-fable-5) | $10   | $12.5    | $1       | $50   |
| ![Anthropic](https://cursor.com/docs-static/images/providers/anthropic-light.svg)[Claude Opus 4.7 (fast mode)](https://cursor.com/docs/models/claude-opus-4-7-fast) | $30   | $37.5    | $3       | $150  |
| ![Anthropic](https://cursor.com/docs-static/images/providers/anthropic-light.svg)[Claude Opus 4.8](https://cursor.com/docs/models/claude-opus-4-8) | $5    | $6.25    | $0.5     | $25   |
| ![Anthropic](https://cursor.com/docs-static/images/providers/anthropic-light.svg)[Claude Sonnet 5](https://cursor.com/docs/models/claude-sonnet-5) | $3    | $3.75    | $0.3     | $15   |
| ![Cursor](https://cursor.com/docs-static/images/providers/cursor.svg)[Composer 1](https://cursor.com/docs/models/cursor-composer-1) | $1.25 | -        | $0.125   | $10   |
| ![Cursor](https://cursor.com/docs-static/images/providers/cursor.svg)[Composer 1.5](https://cursor.com/docs/models/cursor-composer-1-5) | $3.5  | -        | $0.35    | $17.5 |
| ![Cursor](https://cursor.com/docs-static/images/providers/cursor.svg)[Composer 2](https://cursor.com/docs/models/cursor-composer-2) | $0.5  | -        | $0.2     | $2.5  |
| ![Cursor](https://cursor.com/docs-static/images/providers/cursor.svg)[Composer 2.5](https://cursor.com/docs/models/cursor-composer-2-5) | $0.5  | -        | $0.2     | $2.5  |
| ![Google](https://cursor.com/docs-static/images/providers/google.svg)[Gemini 2.5 Flash](https://cursor.com/docs/models/gemini-2-5-flash) | $0.3  | -        | $0.03    | $2.5  |
| ![Google](https://cursor.com/docs-static/images/providers/google.svg)[Gemini 3 Flash](https://cursor.com/docs/models/gemini-3-flash) | $0.5  | -        | $0.05    | $3    |
| ![Google](https://cursor.com/docs-static/images/providers/google.svg)[Gemini 3 Pro](https://cursor.com/docs/models/gemini-3-pro) | $2    | -        | $0.2     | $12   |
| ![Google](https://cursor.com/docs-static/images/providers/google.svg)[Gemini 3 Pro Image Preview](https://cursor.com/docs/models/gemini-3-pro-image-preview) | $2    | -        | $0.2     | $12   |
| ![Google](https://cursor.com/docs-static/images/providers/google.svg)[Gemini 3.1 Pro](https://cursor.com/docs/models/gemini-3-1-pro) | $2    | -        | $0.2     | $12   |
| ![Google](https://cursor.com/docs-static/images/providers/google.svg)[Gemini 3.5 Flash](https://cursor.com/docs/models/gemini-3-5-flash) | $1.5  | -        | $0.15    | $9    |
| ![Z.ai](https://cursor.com/docs-static/images/providers/zai-light.svg)[GLM 5.2](https://cursor.com/docs/models/glm-5-2) | $1.4  | -        | $0.26    | $4.4  |
| ![OpenAI](https://cursor.com/docs-static/images/providers/openai-light.svg)[GPT-5](https://cursor.com/docs/models/gpt-5) | $1.25 | -        | $0.125   | $10   |
| ![OpenAI](https://cursor.com/docs-static/images/providers/openai-light.svg)[GPT-5 Fast](https://cursor.com/docs/models/gpt-5-fast) | $2.5  | -        | $0.25    | $20   |
| ![OpenAI](https://cursor.com/docs-static/images/providers/openai-light.svg)[GPT-5 Mini](https://cursor.com/docs/models/gpt-5-mini) | $0.25 | -        | $0.025   | $2    |
| ![OpenAI](https://cursor.com/docs-static/images/providers/openai-light.svg)[GPT-5-Codex](https://cursor.com/docs/models/gpt-5-codex) | $1.25 | -        | $0.125   | $10   |
| ![OpenAI](https://cursor.com/docs-static/images/providers/openai-light.svg)[GPT-5.1 Codex](https://cursor.com/docs/models/gpt-5-1-codex) | $1.25 | -        | $0.125   | $10   |
| ![OpenAI](https://cursor.com/docs-static/images/providers/openai-light.svg)[GPT-5.1 Codex Max](https://cursor.com/docs/models/gpt-5-1-codex-max) | $1.25 | -        | $0.125   | $10   |
| ![OpenAI](https://cursor.com/docs-static/images/providers/openai-light.svg)[GPT-5.1 Codex Mini](https://cursor.com/docs/models/gpt-5-1-codex-mini) | $0.25 | -        | $0.025   | $2    |
| ![OpenAI](https://cursor.com/docs-static/images/providers/openai-light.svg)[GPT-5.2](https://cursor.com/docs/models/gpt-5-2) | $1.75 | -        | $0.175   | $14   |
| ![OpenAI](https://cursor.com/docs-static/images/providers/openai-light.svg)[GPT-5.2 Codex](https://cursor.com/docs/models/gpt-5-2-codex) | $1.75 | -        | $0.175   | $14   |
| ![OpenAI](https://cursor.com/docs-static/images/providers/openai-light.svg)[GPT-5.3 Codex](https://cursor.com/docs/models/gpt-5-3-codex) | $1.75 | -        | $0.175   | $14   |
| ![OpenAI](https://cursor.com/docs-static/images/providers/openai-light.svg)[GPT-5.4](https://cursor.com/docs/models/gpt-5-4) | $2.5  | -        | $0.25    | $15   |
| ![OpenAI](https://cursor.com/docs-static/images/providers/openai-light.svg)[GPT-5.4 Mini](https://cursor.com/docs/models/gpt-5-4-mini) | $0.75 | -        | $0.075   | $4.5  |
| ![OpenAI](https://cursor.com/docs-static/images/providers/openai-light.svg)[GPT-5.4 Nano](https://cursor.com/docs/models/gpt-5-4-nano) | $0.2  | -        | $0.02    | $1.25 |
| ![OpenAI](https://cursor.com/docs-static/images/providers/openai-light.svg)[GPT-5.5](https://cursor.com/docs/models/gpt-5-5) | $5    | -        | $0.5     | $30   |
| ![xAI](https://cursor.com/docs-static/images/providers/xai-light.svg)[Grok 4.20](https://cursor.com/docs/models/grok-4-20) | $2    | -        | $0.2     | $6    |
| ![xAI](https://cursor.com/docs-static/images/providers/xai-light.svg)[Grok 4.3](https://cursor.com/docs/models/grok-4-3) | $1.25 | -        | $0.2     | $2.5  |
| ![xAI](https://cursor.com/docs-static/images/providers/xai-light.svg)[Grok Build 0.1](https://cursor.com/docs/models/grok-build-0-1) | $1    | -        | $0.2     | $2    |
| ![Moonshot](https://cursor.com/docs-static/images/providers/moonshot.png)[Kimi K2.5](https://cursor.com/docs/models/kimi-k2-5) | $0.6  | -        | $0.1     | $3    |



### [Composer 定价](https://cursor.com/cn/docs/models-and-pricing#composer)

Composer 2.5 是 Cursor 自研的模型，专门针对代理式编码 (agentic coding) 进行了强化训练。Auto 和 Composer 2.5 都从这个用量池中选取模型。

| 名称                                                         | 输入 | 缓存写入 | 缓存读取 | 输出 |
| :----------------------------------------------------------- | :--- | :------- | :------- | :--- |
| ![Cursor](https://cursor.com/docs-static/images/providers/cursor.svg)[Composer 2.5](https://cursor.com/docs/models/cursor-composer-2-5) | $0.5 | -        | $0.2     | $2.5 |
| ![Cursor](https://cursor.com/docs-static/images/providers/cursor.svg)[Composer 2.5 (Fast)](https://cursor.com/docs/models/cursor-composer-2-5) | $3   | -        | $0.5     | $15  |



### [Auto 定价](https://cursor.com/cn/docs/models-and-pricing#auto)

| Token type          | Price per 1M tokens |
| :------------------ | :------------------ |
| Input + Cache Write | $1.25               |
| Output              | $6.00               |
| Cache Read          | $0.25               |