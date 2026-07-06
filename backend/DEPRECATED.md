# DEPRECATED — 不再维护

`backend/` 为早期 FastAPI **测试桩**（mock 全部 API），已于 2026-07-06 弃用。

**请使用 `backend_prod/`** 作为唯一后端：

- 本地开发：`cd backend_prod && uvicorn main:app --reload --port 8000`
- 生产部署：`.\deploy\deploy.ps1`（同步 `backend_prod/` 至 ECS）

本目录仅作历史参考保留，不再接受功能改动与部署更新。
