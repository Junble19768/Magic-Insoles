# magic-insoles 文档索引

> 向 AI 提问时，提供 `doc/` 目录即可，无需附上 `ignored/TALK_WITH_AI.md`。

## 分工说明

| 角色 | 负责范围 | 说明 |
|------|---------|------|
| **本人（Junble）** | **嵌入式数据处理 + 前后端** | STM32 端数据采集处理、BLE/LTE 传输、前端 Web（React + Three.js）、后端 FastAPI 服务 |
| **硬件组** | 硬件设计 + STM32 底层固件 | PCB 打板、传感器驱动、TinyML 部署、LED/马达控制等底层实现 |

> **本人在嵌入式部分的边界**：负责数据协议设计、FSR 数据处理流程、BLE/LTE 通信逻辑、TinyML 输入输出接口定义，不负责 PCB 设计、传感器底层驱动、TinyML 模型训练部署等纯硬件/固件层面工作。

## 快速了解项目

先读 → **[project-context.md](project-context.md)**（项目全貌精炼摘要，~150行）

## 详细文档

| 文档 | 内容 |
|------|------|
| [project-context.md](project-context.md) | 项目全貌摘要（AI 会话入口，替代 TALK_WITH_AI.md） |
| [design-overview.md](design-overview.md) | 项目背景、设计思路、功能要点、待确认项（TBD） |
| [software-architecture.md](software-architecture.md) | 代码结构、数据流图、实体功能清单、开发优先级 |
| [data-protocol.md](data-protocol.md) | BLE 帧格式、HTTP 接口定义、前端解析示例 |
| [deployment.md](deployment.md) | 阿里云 ECS 方案 A 部署：路径规划、双项目共机、上云步骤与限制 |
