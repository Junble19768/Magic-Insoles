# Task: magic-insoles 后端完整实施

- **日期**：2026-07-06
- **状态**：计划中
- **关联**：
  - ADR：[`decisions/0001-dual-link-no-relay.md`](../memories/decisions/0001-dual-link-no-relay.md)、[`decisions/0002-ai-layered-architecture.md`](../memories/decisions/0002-ai-layered-architecture.md)
  - Memory Bank：[`techContext.md`](../memories/techContext.md)（BLE/设备 TCP/HTTP API 协议）、[`systemPatterns.md`](../memories/systemPatterns.md)
  - 原始文档备份：`.cursor/bakup/TODO/backend.md`、`.cursor/bakup/doc/data-protocol.md`

## Problem / 目标

前端验证完成后，将 `backend/main.py` 从测试桩升级为完整后端实现：

- STM32 经 LTE/串口透传模块建立 TCP 连接，后端解析设备二进制应用层协议
- SQLite 存储
- 步态特征提取
- DeepSeek 日报生成
- 供手机 Web 远程查看的 REST API

设备上需要用 C 实现一个 serial bridge，负责按本文协议打包并通过物联网模块透传；后端集成 TCP 端口监听、帧同步、CRC 校验、payload 解析和入库。当前 task 只确定后端设计，不进行实现。

## 核心思路

按依赖顺序自底向上实施：配置与数据层 → 设备协议解析 → TCP 接入 → 内部 ingest service → 特征服务 → LLM 服务 → REST 查询 API → 替换 main 桩 → 测试。

当前测试桩已 mock 全部端点（activity/gait/gps/report/ingest），完整实现时需保留这些端点的响应格式以兼容前端。

设备接入主路径为 TCP 二进制流；`POST /api/ingest` 可保留为开发/仿真入口，但不再作为真实设备首选链路。

## 受影响的文件 / 模块

- `backend/main.py` — 从测试桩改为路由注册入口
- `backend/config.py` — 新建：环境变量
- `backend/database.py` — 新建：SQLite 连接与建表
- `backend/requirements.txt` — 可能需补充 sqlalchemy 等
- `backend/api/deps.py` — 新建：API Key 鉴权
- `backend/api/ingest.py` — 新建：POST /api/ingest（调试/仿真入口）
- `backend/api/report.py` — 新建：报告查询与生成
- `backend/protocol/device_frame.py` — 新建：设备二进制帧定义、CRC、状态机解析
- `backend/protocol/payloads.py` — 新建：Force/GPS/Event/DeviceStatus payload 解析
- `backend/services/tcp_ingest.py` — 新建：TCP server，接收设备流并调用 ingest service
- `backend/services/ingest.py` — 新建：统一入库服务，供 TCP 与 HTTP ingest 共用
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
│   ├── ingest.py           # POST /api/ingest，调试/仿真入口
│   └── report.py           # GET /api/report/today、/history，POST /api/report/generate
├── protocol/
│   ├── __init__.py
│   ├── device_frame.py     # 帧头、CRC16、stream parser
│   └── payloads.py         # datatype -> payload parser
├── services/
│   ├── __init__.py
│   ├── ingest.py           # TCP/HTTP 共用的数据入库服务
│   ├── tcp_ingest.py       # 设备 TCP 监听与连接管理
│   ├── feature.py          # 步频、COP、对称性特征提取
│   └── llm.py              # DeepSeek API 封装 + Prompt 渲染
├── models/
│   ├── __init__.py
│   └── schemas.py          # Pydantic 请求/响应模型 + SQLAlchemy ORM
└── tests/
    ├── test_ingest.py
    ├── test_protocol.py
    ├── test_tcp_ingest.py
    └── test_feature.py
```

## 设备通讯协议（后端-设备）

### 链路定位

- 这是后端与设备之间的应用层二进制协议，不是 BLE 手机近程可视化协议。
- 设备侧使用 C 实现 serial bridge；后端侧集成 TCP server 与内容解析。
- 物联网模块只做 UART/TCP 透传，协议本身不依赖具体传输层。
- TCP 是字节流，后端必须用状态机做帧同步，不能假设一次 `recv()` 得到一帧。
- 当前先确定协议与后端设计，不进行代码实现。

### 通用帧格式

所有多字节整数、浮点 payload 字段默认小端序；CRC16 两字节沿用 `serial_bridge_sample`：**高字节在前，低字节在后**。

```c
// Wire frame, not a packed C struct.
// Header fields before payload are little-endian except CRC output order.
SOF_1        uint8_t   // 0xA5
SOF_2        uint8_t   // 0x5A
seq          uint16_t  // auto increase, wrap at 65535
data_type    uint16_t  // high byte: category, low byte: schema version
data_length  uint16_t  // payload length in bytes
payload      uint8_t[data_length]
crc16        uint16_t  // CRC16-Modbus over SOF..payload, high byte first on wire
```

CRC 算法沿用样例中的 `CRC16_Check`：

```c
uint16_t CRC16_Check(const uint8_t *data, uint16_t length) {
    uint16_t crc16 = 0xFFFF;
    for (uint16_t i = 0; i < length; ++i) {
        crc16 ^= data[i];
        for (uint8_t j = 0; j < 8; ++j) {
            uint8_t state = crc16 & 0x01;
            crc16 >>= 1;
            if (state) {
                crc16 ^= 0xA001;
            }
        }
    }
    return crc16;
}
```

发送 CRC 时：

```c
packet.push_back((uint8_t)(crc16 >> 8));    // high byte first
packet.push_back((uint8_t)(crc16 & 0xFF));  // low byte second
```

### Data Type 分配

| `data_type` | 名称 | 方向 | 发送策略 | 说明 |
|-------------|------|------|----------|------|
| `0x0101` | Force | 设备 → 后端 | 30Hz 采样，建议每 1s 聚合 30 个样本发送 | 32 点压力，每点 `uint16_t` |
| `0x0201` | IMU | 保留 | 采集 200Hz，但当前不发送 | 后端保留 parser/数据库扩展位 |
| `0x0301` | GPS | 设备 → 后端 | 不固定频率，收到定位即发送 | 单点定位数据 |
| `0x0401` | DeviceStatus | 设备 → 后端 | 状态变化或定时发送 | 电量、左右鞋垫连接位 |
| `0x0501` | Event | 设备 → 后端 | 每 10s 或满 50 个事件发送；无事件时发送 1 个心跳事件 | 步态/系统/心跳事件 |

### Payload 定义

不要在设备侧直接 `memcpy(struct)` 作为协议 payload。下面的 C struct 是无歧义字段顺序定义，实际发送时仍应逐字段序列化，避免 padding/alignment 差异。

#### Force `0x0101`

压力采样固定 30Hz。每个压力点压缩为 `uint16_t`，每个样本 32 点。

```c
#define FORCE_CHANNEL_COUNT 32
#define FORCE_BATCH_SAMPLES 30

typedef struct {
    uint64_t start_stamp; // first sample timestamp, unit TBD: ms or us
    uint16_t samplecount; // normally 30
    uint16_t data[FORCE_BATCH_SAMPLES][FORCE_CHANNEL_COUNT];
} ForcePayloadV1;
```

payload 长度：

```text
8 + 2 + samplecount * 32 * 2
```

当 `samplecount = 30` 时，payload 为 `1930` bytes，整帧约 `1940` bytes，适合 TCP 透传与后端即时入库。

#### IMU `0x0201`

IMU 固定 200Hz 采集，但当前不发送，接口保留。后端可先不建实时入库链路，只保留 datatype 与 payload schema 注释。

```c
typedef struct {
    float acc[3];
    float gyr[3];
    float quat[4]; // w, x, y, z
} ImuSampleV1;

typedef struct {
    uint64_t start_stamp;
    uint16_t samplecount;
    ImuSampleV1 data[]; // reserved, not sent in current version
} ImuPayloadV1;
```

#### GPS `0x0301`

GPS 不做积累，收到数据就发送。

```c
typedef struct {
    uint64_t timestamp;
    double latitude;
    double longitude;
    float altitude;
    float speed;
    float heading;
    float accuracy;
    uint8_t fix_type;
    uint8_t satellite_count;
} GpsPayloadV1;
```

#### DeviceStatus `0x0401`

```c
typedef struct {
    uint8_t battery;      // 0..100 percent
    uint8_t reserved;     // must be 0
    uint16_t device_link; // bit0: right insole ok, bit1: left insole ok, others reserved
} DeviceStatusPayloadV1;
```

#### Event `0x0501`

事件数据每 10s 或满 50 个事件发送一次；如果 10s 内没有事件，发送 `samplecount = 1` 的心跳包。

```c
#define EVENT_BATCH_MAX 50

typedef struct {
    uint32_t eventId;
    uint64_t stamp;
    uint64_t reserved; // must be 0
} EventSampleV1;

typedef struct {
    uint16_t samplecount; // 1..50
    EventSampleV1 data[EVENT_BATCH_MAX];
} EventPayloadV1;
```

payload 长度：

```text
2 + samplecount * 20
```

心跳事件约定：

```c
#define EVENT_ID_HEARTBEAT 0x00000000u
```

### 后端解析原则

- stream parser 负责：寻找 `0xA5 0x5A`、读取固定头、按 `data_length` 收 payload、读取 CRC、校验、输出完整 frame。
- payload parser 负责：按 `data_type` 解析 payload 字段，转换为后端内部模型。
- 未知 `data_type`：记录日志并丢弃，不中断 TCP 连接。
- `data_length` 必须设置上限，建议 MVP 先设为 `8192` bytes；超过上限直接丢帧并重新同步。
- CRC 错误只丢当前帧，继续扫描下一个 SOF。
- `seq` 用于丢包/乱序观测，不作为数据库主键。
- timestamp 单位仍待定，建议设备侧统一为 Unix epoch milliseconds；若无 RTC，则使用设备启动后的 monotonic milliseconds，并由后端记录 receive time。

## 数据库设计

```sql
-- 压力批次：30Hz，通常每批 30 个样本
CREATE TABLE force_batches (
    id             INTEGER PRIMARY KEY,
    seq            INTEGER NOT NULL,
    start_stamp    INTEGER NOT NULL,
    receive_time   REAL NOT NULL,
    samplecount    INTEGER NOT NULL,
    samples_json   TEXT NOT NULL      -- JSON: samplecount x 32 uint16
);

-- GPS 点：不固定频率
CREATE TABLE gps_points (
    id              INTEGER PRIMARY KEY,
    seq             INTEGER NOT NULL,
    timestamp       INTEGER NOT NULL,
    receive_time    REAL NOT NULL,
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    altitude        REAL,
    speed           REAL,
    heading         REAL,
    accuracy        REAL,
    fix_type        INTEGER,
    satellite_count INTEGER
);

-- 设备状态
CREATE TABLE device_status (
    id            INTEGER PRIMARY KEY,
    seq           INTEGER NOT NULL,
    receive_time  REAL NOT NULL,
    battery       INTEGER NOT NULL,
    device_link   INTEGER NOT NULL
);

-- 事件批次：每 10s / 满 50 个发送；无事件时包含心跳事件
CREATE TABLE device_events (
    id            INTEGER PRIMARY KEY,
    seq           INTEGER NOT NULL,
    receive_time  REAL NOT NULL,
    event_id      INTEGER NOT NULL,
    stamp         INTEGER NOT NULL,
    reserved      INTEGER
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
| TCP | `0.0.0.0:<DEVICE_TCP_PORT>` | 设备二进制帧接入，主链路 |
| POST | `/api/ingest` | 调试/仿真入口，API Key 鉴权 |
| GET | `/api/report/today` | 获取今日 AI 日报 |
| GET | `/api/report/history?days=7` | 获取历史日报列表 |
| POST | `/api/report/generate` | 手动触发当日报告生成（调试用） |

### 鉴权

- Header: `X-API-Key: <固定密钥>`
- 单设备演示，无需用户登录系统
- TCP 设备链路 MVP 阶段可先依赖私有端口 + 固定设备来源；若需要链路鉴权，后续增加 `0x0001` hello/auth 帧或在 payload 中加入 device token。

### HTTP ingest 请求体（调试/仿真）

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

HTTP ingest 只作为本地调试入口，不代表设备真实传输格式。真实设备使用 TCP 二进制帧，后端解析后调用同一个 `services/ingest.py`。

## 服务模块职责

### `services/feature.py`

对当日 `force_batches`、`device_events` 计算：

- **步频**：优先根据 Event 中的步态事件估算步/分钟；没有事件时可用压力变化粗略估算
- **COP 轨迹**：加权平均压力中心（坐标映射待 TBD-1/TBD-2 确认后替换占位）
- **对称性指数**：左右脚压力分布差异
- **异常比例**：优先使用 Event 分类事件；MVP 可先置为未知/0

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
| `DEVICE_TCP_HOST` | 设备 TCP 监听地址 | `0.0.0.0` |
| `DEVICE_TCP_PORT` | 设备 TCP 监听端口 | `9000` |
| `DEVICE_MAX_FRAME_BYTES` | 单帧最大字节数 | `8192` |

建议使用 `.env` 文件（不提交到 git）。

## 分步计划

- [ ] Step 1: `config.py` + `database.py` + `models/schemas.py`
- [ ] Step 2: `protocol/device_frame.py`（CRC16 + TCP stream frame parser）
- [ ] Step 3: `protocol/payloads.py`（Force/GPS/Event/DeviceStatus payload parser）
- [ ] Step 4: `services/ingest.py`（统一入库服务）
- [ ] Step 5: `services/tcp_ingest.py`（设备 TCP server，接收帧并调用 ingest service）
- [ ] Step 6: `api/deps.py` + `api/ingest.py`（API Key 校验 + HTTP 调试入口）
- [ ] Step 7: `services/feature.py`（先用 mock/seed 数据单测）
- [ ] Step 8: `services/llm.py`（DeepSeek 调用）
- [ ] Step 9: `api/report.py`（查询 + 生成）
- [ ] Step 10: 替换 `main.py` 测试桩为完整路由注册与 TCP server lifecycle
- [ ] Step 11: `tests/` + `scripts/simulate_ingest.py`

## 测试策略

### 单元测试

- `test_feature.py`：用固定压力帧序列验证 COP、步频、对称性
- `test_protocol.py`：验证 SOF 同步、CRC16 高字节在前、粘包/拆包、CRC 错误恢复
- `test_ingest.py`：验证 TCP/HTTP 共用 ingest service 的批量写入
- `test_tcp_ingest.py`：验证 TCP 收帧后正确入库

### 集成测试脚本

`scripts/simulate_ingest.py`：

- 构造 Force/GPS/Event/DeviceStatus 二进制帧
- 通过 TCP 连接发送粘包、拆包、CRC 错误帧和正常帧
- 可选：批量 POST JSON 到 `/api/ingest` 验证调试入口
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

- STM32 经 LTE/串口透传模块连接后端 TCP 端口，发送本文定义的二进制帧
- 设备侧 C serial bridge 负责：按字段序列化 payload、组帧、计算 CRC16、CRC 高字节在前发送
- 后端负责：TCP stream parser、CRC 校验、datatype 分发、入库、特征与报告生成
- `POST /api/ingest` 仅作为开发/仿真入口，不作为真实设备主链路
- BLE 帧格式见 `techContext.md`，仅用于近程可视化，不经过后端
- API Key 写入固件 config，与前端 `VITE_API_KEY` 保持一致

## 当前协议决策记录

- 2026-07-06：后端-设备通讯协议改为 TCP 二进制应用层协议，设备侧实现 C serial bridge，后端集成 TCP 端口及内容解析。
- 2026-07-06：CRC16 算法沿用 `serial_bridge_sample`，CRC 字节序明确为高字节在前。
- 2026-07-06：压力采样从 100Hz 调整为 30Hz，每点从 `float` 压缩为 `uint16_t`，每个 Force payload 通常聚合 30 个样本。
- 2026-07-06：IMU 仍以 200Hz 采集，但当前不发送，仅保留 datatype/schema。
- 2026-07-06：新增 Event `0x0501`，每 10s 或满 50 个发送；10s 无事件时发送 1 个心跳事件。

## Debug Notes

> 开发中遇到的重大 Bug、卡点、设计变更即时追加到这里（带时间戳）。

## Lessons Learned

> 任务收尾时填写，供后续任务参考；重要结论应同步回 `.cursor/memories/`。
