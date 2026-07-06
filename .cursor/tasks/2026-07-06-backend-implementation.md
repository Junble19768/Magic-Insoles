# Task: magic-insoles 后端完整实施

- **日期**：2026-07-06
- **状态**：计划中
- **关联**：
  - ADR：[`decisions/0001-dual-link-no-relay.md`](../memories/decisions/0001-dual-link-no-relay.md)、[`decisions/0002-ai-layered-architecture.md`](../memories/decisions/0002-ai-layered-architecture.md)
  - Memory Bank：[`techContext.md`](../memories/techContext.md)（BLE/HTTP 协议）、[`systemPatterns.md`](../memories/systemPatterns.md)
  - 原始文档备份：`.cursor/bakup/TODO/backend.md`、`.cursor/bakup/doc/data-protocol.md`

## Problem / 目标

前端验证完成后，将 `backend/main.py` 从测试桩升级为完整 FastAPI 实现：

- STM32 经 LTE 直传的数据接入
- SQLite 存储
- 步态特征提取
- DeepSeek 日报生成
- 供手机 Web 远程查看的 REST API

数据协议以 Memory Bank `techContext.md`（原 `data-protocol.md`）为准。

## 核心思路

按依赖顺序自底向上实施：配置与数据层 → 鉴权 → 数据接入 → 特征服务 → LLM 服务 → 报告 API → 替换 main 桩 → 测试。

当前测试桩已 mock 全部端点（activity/gait/gps/report/ingest），完整实现时需保留这些端点的响应格式以兼容前端。

## 受影响的文件 / 模块

- `backend/main.py` — 从测试桩改为路由注册入口
- `backend/config.py` — 新建：环境变量
- `backend/database.py` — 新建：SQLite 连接与建表
- `backend/requirements.txt` — 可能需补充 sqlalchemy 等
- `backend/api/deps.py` — 新建：API Key 鉴权
- `backend/api/ingest.py` — 新建：POST /api/ingest
- `backend/api/report.py` — 新建：报告查询与生成
- `backend/services/feature.py` — 新建：步频、COP、对称性
- `backend/services/llm.py` — 新建：DeepSeek 封装
- `backend/models/schemas.py` — 新建：Pydantic + ORM
- `backend/tests/` — 新建：单元测试
- `backend/scripts/simulate_ingest.py` — 新建：集成测试脚本

## 目录结构（目标态）

```
backend/
├── main.py                 # FastAPI 入口、CORS、路由注册
├── config.py               # 环境变量：API_KEY、DEEPSEEK_KEY、DB_PATH
├── database.py             # SQLite 连接、建表、Session 管理
├── requirements.txt
├── api/
│   ├── __init__.py
│   ├── deps.py             # API Key 鉴权依赖
│   ├── ingest.py           # POST /api/ingest
│   └── report.py           # GET /api/report/today、/history，POST /api/report/generate
├── services/
│   ├── __init__.py
│   ├── feature.py          # 步频、COP、对称性特征提取
│   └── llm.py              # DeepSeek API 封装 + Prompt 渲染
├── models/
│   ├── __init__.py
│   └── schemas.py          # Pydantic 请求/响应模型 + SQLAlchemy ORM
└── tests/
    ├── test_ingest.py
    └── test_feature.py
```

## 数据库设计

```sql
-- 原始压力帧（每 N 步一批）
CREATE TABLE gait_frames (
    id          INTEGER PRIMARY KEY,
    timestamp   REAL NOT NULL,
    pressures   TEXT NOT NULL,      -- JSON array, 32 integers
    step_count  INTEGER,
    gait_class  INTEGER,            -- 0=正常, 1=内八, 2=外八
    ml_conf     REAL
);

-- AI 报告（每日一条）
CREATE TABLE reports (
    id           INTEGER PRIMARY KEY,
    date         TEXT NOT NULL UNIQUE,
    report_text  TEXT NOT NULL,
    summary_json TEXT                -- 结构化摘要 JSON
);
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ingest` | STM32 LTE 批量上传原始帧，API Key 鉴权 |
| GET | `/api/report/today` | 获取今日 AI 日报 |
| GET | `/api/report/history?days=7` | 获取历史日报列表 |
| POST | `/api/report/generate` | 手动触发当日报告生成（调试用） |
| POST | `/api/heartbeat` | 设备心跳（可选，时间充裕再做） |

### 鉴权

- Header: `X-API-Key: <固定密钥>`
- 单设备演示，无需用户登录系统

### ingest 请求体

```json
{
  "frames": [
    {
      "timestamp": 1751000000.123,
      "pressures": [0, 0, "..."],
      "gait_state": 1,
      "ml_class": 0,
      "ml_conf": 0.92,
      "step_count": 134
    }
  ]
}
```

## 服务模块职责

### `services/feature.py`

对当日 `gait_frames` 计算：

- **步频**：根据 step_count 或 heel_strike 事件估算步/分钟
- **COP 轨迹**：加权平均压力中心（坐标映射待 TBD-1/TBD-2 确认后替换占位）
- **对称性指数**：左右脚压力分布差异
- **异常比例**：ml_class != 0 的帧占比

输出结构化摘要供 LLM 使用：

```python
{
  "walk_min": 45,
  "step_count": 3200,
  "step_freq": 108,
  "gait_summary": "轻度内八",
  "abnormal_pct": 12.5,
  "symmetry_desc": "左右脚压力分布基本对称"
}
```

### `services/llm.py`

- 读取 `config.DEEPSEEK_API_KEY`
- 使用 Prompt 模板（见下方）
- 调用 DeepSeek Chat API
- 将 `report_text` + `summary_json` 写入 `reports` 表

**DeepSeek Prompt 模板：**

```
你是一名儿童运动健康顾问。以下是今日步态数据摘要：
- 运动时长：{walk_min} 分钟，总步数：{step_count}
- 平均步频：{step_freq} 步/分钟
- 步态评估：{gait_summary}（正常/轻度内八/轻度外八，出现比例 {abnormal_pct}%）
- 左右脚对称性：{symmetry_desc}

请用简洁、友好的语言生成一份家长日报（150字以内），包含：
1. 今日运动总结
2. 一个具体改善建议（如有异常）
3. 一句鼓励孩子的话

注意：不使用医学诊断语气，语言适合普通家长阅读。
```

Prompt 要点：角色为儿童运动健康顾问；输出 150 字以内；友好、非医学诊断；含运动总结、改善建议、鼓励语。

## 配置项（`config.py`）

| 变量 | 说明 | 示例 |
|------|------|------|
| `API_KEY` | 设备/前端鉴权密钥 | `dev-magic-insoles-key` |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 从环境变量读取 |
| `DEEPSEEK_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `DB_PATH` | SQLite 文件路径 | `./data/magic_insoles.db` |
| `CORS_ORIGINS` | 允许的前端源 | `http://localhost:5173` |

建议使用 `.env` 文件（不提交到 git）。

## 分步计划

- [ ] Step 1: `config.py` + `database.py` + `models/schemas.py`
- [ ] Step 2: `api/deps.py`（API Key 校验）
- [ ] Step 3: `api/ingest.py`（存库 + 触发特征缓存）
- [ ] Step 4: `services/feature.py`（先用 mock/seed 数据单测）
- [ ] Step 5: `services/llm.py`（DeepSeek 调用）
- [ ] Step 6: `api/report.py`（查询 + 生成）
- [ ] Step 7: 替换 `main.py` 测试桩为完整路由注册
- [ ] Step 8: `tests/` + `scripts/simulate_ingest.py`

## 测试策略

### 单元测试

- `test_feature.py`：用固定压力帧序列验证 COP、步频、对称性
- `test_ingest.py`：验证 ingest 鉴权、批量写入、响应格式

### 集成测试脚本

`scripts/simulate_ingest.py`：

- 按 `techContext.md` BLE/HTTP 格式构造 JSON
- 批量 POST 到 `/api/ingest`
- 调用 `/api/report/generate` 验证 LLM 链路

### 与前端联调

1. 启动后端：`uvicorn main:app --reload --port 8000`
2. 启动前端：`npm run dev`（Vite 代理 `/api` → `8000`）
3. 访问 `http://localhost:5173/insoles/report` 验证三态（加载/空/错误/成功）

## 当前测试桩说明（替换前参考）

`backend/main.py`（已实现）：

- `GET /api/report/today` → 固定 mock 日报
- `GET /api/report/history?days=7` → 固定历史列表
- `GET /api/report?period=today|week|month` → 多周期 mock
- `GET /api/activity/today` / `/history` → mock 运动数据
- `GET /api/gait/summary` → mock 步态分析
- `GET /api/gps/routes` → mock GPS 轨迹
- `POST /api/ingest` → 打印日志，返回 ok
- `GET /health` → 健康检查

启动命令：

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## 待确认项（不阻塞骨架，影响算法精度）

| 编号 | 内容 | 后端影响 |
|------|------|---------|
| TBD-1 | 传感器物理坐标映射 | feature.py 中 COP 计算 |
| TBD-2 | COP 坐标轴方向 | 报告中的左右脚描述 |
| TBD-3 | ADC → 压力标定曲线 | 物理量描述 |
| TBD-5 | 步态分析阈值 | 异常判定逻辑 |

当前使用与前端一致的 4×4 均匀网格占位方案。

## 与嵌入式侧的接口约定

- STM32 经 LTE 直传 `POST /api/ingest`，手机不做中转
- BLE 帧格式见 `techContext.md`，仅用于近程可视化，不经过后端
- API Key 写入固件 config，与前端 `VITE_API_KEY` 保持一致

## Debug Notes

> 开发中遇到的重大 Bug、卡点、设计变更即时追加到这里（带时间戳）。

## Lessons Learned

> 任务收尾时填写，供后续任务参考；重要结论应同步回 `.cursor/memories/`。
