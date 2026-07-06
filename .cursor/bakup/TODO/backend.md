# magic-insoles 完整后端实施计划

> 本文档记录前端验证完成后的完整后端实施方案。当前阶段仅提供 `backend/main.py` 测试桩供前端联调。

## 一、目标

实现 STM32 经 LTE 直传的数据接入、SQLite 存储、步态特征提取、DeepSeek 日报生成，以及供手机 Web 远程查看的 REST API。

数据协议以 [doc/data-protocol.md](../doc/data-protocol.md) 为准。

## 二、目录结构（目标态）

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

## 三、数据库设计

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

## 四、API 端点

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

## 五、服务模块职责

### 5.1 `services/feature.py`

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

### 5.2 `services/llm.py`

- 读取 `config.DEEPSEEK_KEY`
- 使用 Prompt 模板（见 [doc/software-architecture.md](../doc/software-architecture.md) 第137-152行）
- 调用 DeepSeek Chat API
- 将 `report_text` + `summary_json` 写入 `reports` 表

Prompt 要点：

- 角色：儿童运动健康顾问
- 输出：150 字以内家长日报
- 语气：友好、非医学诊断
- 包含：运动总结、改善建议、鼓励语

## 六、配置项（`config.py`）

| 变量 | 说明 | 示例 |
|------|------|------|
| `API_KEY` | 设备/前端鉴权密钥 | `dev-magic-insoles-key` |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 从环境变量读取 |
| `DEEPSEEK_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `DB_PATH` | SQLite 文件路径 | `./data/magic_insoles.db` |
| `CORS_ORIGINS` | 允许的前端源 | `http://localhost:5173` |

建议使用 `.env` 文件（不提交到 git）。

## 七、实施顺序

```
1. config.py + database.py + models/schemas.py
2. api/deps.py（API Key 校验）
3. api/ingest.py（存库 + 触发特征缓存）
4. services/feature.py（先用 mock/seed 数据单测）
5. services/llm.py（DeepSeek 调用）
6. api/report.py（查询 + 生成）
7. 替换 main.py 测试桩为完整路由注册
8. tests/ + 模拟 STM32 POST 脚本
```

## 八、测试策略

### 8.1 单元测试

- `test_feature.py`：用固定压力帧序列验证 COP、步频、对称性
- `test_ingest.py`：验证 ingest 鉴权、批量写入、响应格式

### 8.2 集成测试脚本

`scripts/simulate_ingest.py`：

- 按 `data-protocol.md` 格式构造 JSON
- 批量 POST 到 `/api/ingest`
- 调用 `/api/report/generate` 验证 LLM 链路

### 8.3 与前端联调

1. 启动后端：`uvicorn main:app --reload --port 8000`
2. 启动前端：`npm run dev`（Vite 代理 `/api` → `8000`）
3. 访问 `/report` 页面验证三态（加载/空/错误/成功）

## 九、当前测试桩说明

`backend/main.py`（已实现）：

- `GET /api/report/today` → 固定 mock 日报
- `GET /api/report/history?days=7` → 固定历史列表
- `POST /api/ingest` → 打印日志，返回 ok
- `GET /health` → 健康检查

启动命令：

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## 十、待确认项（不阻塞骨架，影响算法精度）

| 编号 | 内容 | 后端影响 |
|------|------|---------|
| TBD-1 | 传感器物理坐标映射 | feature.py 中 COP 计算 |
| TBD-2 | COP 坐标轴方向 | 报告中的左右脚描述 |
| TBD-3 | ADC → 压力标定曲线 | 物理量描述 |
| TBD-5 | 步态分析阈值 | 异常判定逻辑 |

当前使用与前端一致的 4x4 均匀网格占位方案。

## 十一、与嵌入式侧的接口约定

- STM32 经 LTE 直传 `POST /api/ingest`，手机不做中转
- BLE 帧格式见 `data-protocol.md`，仅用于近程可视化，不经过后端
- API Key 写入固件 config，与前端 `VITE_API_KEY` 保持一致
