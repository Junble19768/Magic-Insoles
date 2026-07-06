# 阿里云 ECS 部署说明（方案 A）

> 测试阶段：单台 ECS、无域名、公网 IP 访问；与外部中小企业官网共机部署。

---

## 一、背景与目标

| 项 | 说明 |
|----|------|
| 云主机 | 阿里云 ECS，2 核 2G（测试阶段） |
| 共机项目 | ① 外部中小企业官网（静态为主，图片在 OSS）② magic-insoles（React SPA + FastAPI） |
| 域名 | 当前无域名，通过 `http://<ECS公网IP>/` 访问 |
| 官网图片 | 已托管阿里云 OSS，页面引用 OSS URL，不占 ECS 出站带宽 |

**方案 A**：同一公网 IP，按 URL 路径拆分服务（不依赖子域名）。

---

## 二、路径规划

| 路径 | 服务 | 部署目录 / 进程 |
|------|------|-----------------|
| `/` | 中小企业官网静态站 | `/var/www/corp/dist`（外部仓库 build 产物） |
| `/insoles/` | magic-insoles 前端 SPA | `/var/www/insoles/dist` |
| `/api/` | FastAPI 后端 | `uvicorn` 监听 `127.0.0.1:8000`，Nginx 反代 |

API 挂在站点根路径 `/api/`，**不**放在 `/insoles/api/` 下，与前端子路径解耦。

```
                    ┌──────────────────────────────┐
  浏览器 ──────────►│  Nginx :80                    │
                    │  /          → 官网 dist       │
                    │  /insoles/  → 鞋垫前端 dist   │
                    │  /api/      → uvicorn :8000   │
                    └──────────────────────────────┘
                              │
                    图片直接访问 OSS（不经 ECS）
```

---

## 三、资源与容量

**内存（粗略）**

| 组件 | 占用 |
|------|------|
| Linux 系统 | ~400–600 MB |
| Nginx | ~30–50 MB |
| FastAPI + SQLite | ~100–200 MB |
| 静态文件服务 | 几乎不额外占内存 |

2 核 2G 对测试阶段足够。官网访问量大时，瓶颈更可能在 **ECS 出站带宽**（入门规格常为 1–5 Mbps），而非 CPU/内存。官网图片走 OSS 可显著减轻带宽压力。

---

## 四、仓库内代码约束

### 前端（必须）

- [frontend/vite.config.ts](../frontend/vite.config.ts)：`base: '/insoles/'`
- [frontend/src/main.tsx](../frontend/src/main.tsx)：`BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, '')}`
- [frontend/index.html](../frontend/index.html)：favicon 使用 `%BASE_URL%favicon.svg`

### API 客户端（保持默认）

- [frontend/src/api/client.ts](../frontend/src/api/client.ts)：`VITE_API_BASE_URL` 默认为 `/api`（站点根相对路径）
- 生产环境参考 [frontend/.env.production.example](../frontend/.env.production.example)

### 后端（无需改动）

- [backend/main.py](../backend/main.py) 路由已带 `/api` 前缀
- CORS 当前允许 `*`，同 IP 部署无跨域问题

### 外部官网（不在本仓库）

- build 产物部署到 `/var/www/corp/dist`
- 资源使用相对路径或 OSS 完整 URL
- **不得**占用 `/insoles/`、`/api/` 路径

---

## 五、ECS 部署步骤

### 1. 构建与上传

```bash
# 鞋垫前端（本仓库）
cd frontend && npm run build
# 上传 dist/ → ECS:/var/www/insoles/dist

# 官网（外部仓库）
# build 后上传 dist/ → ECS:/var/www/corp/dist

# 后端
# 上传 backend/ → ECS:/var/www/magic-insoles/backend
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Nginx

复制 [deploy/nginx.conf](../deploy/nginx.conf) 到 ECS（如 `/etc/nginx/conf.d/magic-insoles.conf`），然后：

```bash
nginx -t && systemctl reload nginx
```

### 3. 后端守护进程

参考 [deploy/magic-insoles-api.service](../deploy/magic-insoles-api.service) 配置 systemd：

```bash
systemctl enable --now magic-insoles-api
```

按实际路径修改 `WorkingDirectory`、`ExecStart` 中的 venv 路径。

### 4. 安全组

阿里云安全组放行入站 **TCP 80**。

---

## 六、验证清单

- [ ] `http://<IP>/` → 官网首页
- [ ] `http://<IP>/insoles/` → 鞋垫应用，自动跳转 dashboard
- [ ] 刷新 `http://<IP>/insoles/dashboard` 不出现 404
- [ ] `http://<IP>/api/health` 返回 `{"status":"ok"}`
- [ ] 浏览器 Network：JS/CSS 路径为 `/insoles/assets/...`
- [ ] 报告/数据页 API 请求指向 `/api/...`

---

## 七、已知限制

| 限制 | 说明 |
|------|------|
| Web Bluetooth | 要求 HTTPS 或 localhost；`http://<IP>/insoles/realtime` 在真机上 BLE **不可用** |
| STM32 LTE | 测试阶段使用 `http://<IP>/api/ingest`（见 [data-protocol.md](data-protocol.md)） |
| 备案 | 正式对外推广需域名 + ICP 备案；测试阶段 IP 访问即可 |
| 后续 HTTPS | 有域名后配置 `server_name`、证书（如 Let's Encrypt），路径结构无需大改 |

---

## 八、本地开发

设置 `base: '/insoles/'` 后，开发入口为：

```
http://localhost:5173/insoles/
```

Vite `server.proxy` 仍将 `/api` 代理到 `http://127.0.0.1:8000`，行为与生产一致。

```bash
# 终端 1
cd backend && uvicorn main:app --reload --port 8000

# 终端 2
cd frontend && npm run dev
```

---

## 九、相关文件

| 文件 | 用途 |
|------|------|
| [deploy/nginx.conf](../deploy/nginx.conf) | Nginx 路径路由模板 |
| [deploy/magic-insoles-api.service](../deploy/magic-insoles-api.service) | systemd 单元模板 |
| [data-protocol.md](data-protocol.md) | HTTP Base URL、STM32 上传格式 |
| [software-architecture.md](software-architecture.md) | 系统架构与数据流 |
