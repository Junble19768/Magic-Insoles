# ADR-0003: 以 backend_prod 为唯一后端，弃用测试桩

- **状态**：已采纳
- **日期**：2026-07-06

## 背景

项目曾保留 `backend/`（FastAPI 测试桩，mock 全部端点）供前端早期联调。`backend_prod/` 已实现 config、SQLite、TCP 二进制协议解析、ingest、feature、LLM、report 全链路，且 ECS 已具备一键部署能力。

继续维护双后端会增加部署脚本、文档与认知负担，且测试桩数据为假，无法验证真实设备与存储链路。

## 决策

1. **`backend_prod/` 为唯一权威后端**（本地开发与 ECS 生产均使用此目录）。
2. **`backend/` 标记弃用**，不再接受功能改动与部署同步；目录保留作历史参考。
3. **部署脚本** `deploy/deploy.ps1` 仅同步 `backend_prod/` 至 ECS `/var/www/magic-insoles/backend_prod/`。
4. **生产环境变量** 通过服务器 `backend_prod/.env` 管理（模板见 `backend_prod/.env.example`），不纳入 git。

## 备选方案

- **继续双轨维护** — 未选：重复劳动，易漂移。
- **删除 backend/** — 未选：保留只读参考，便于对比早期 mock 接口。

## 影响

- **正面**：单一真相源；部署与文档简化；生产可接真机 TCP 与 SQLite。
- **负面 / 代价**：本地需安装 `backend_prod` 更重依赖；服务器需配置 `.env`（含 `DEEPSEEK_API_KEY` 方可生成日报）。
- **后续**：安全组按需放行设备 TCP `9000`；日报功能需配置 DeepSeek Key。
