# 软件结构与实体功能清单

> 对应 design-overview.md 第四节，供 AI-IDE 开发参考
> 当前是设计阶段，未标注技术栈的部分待开发时再确定

---

## 一、代码仓库结构

```
magic-insoles/
│
├── win-datacap/              【已有】开发/标定工具（Windows PC，Python）
│   ├── server.py                 USB-DAQ FSR TCP 服务（32路 → TCP :6543）
│   ├── force_server.py           Modbus 压力传感器 WebSocket 服务（WS :8765）
│   ├── fsr_calibrate.py          ADC-压力标定对比 GUI（待补充：拟合系数导出）
│   ├── modbus_rtu.py             Modbus RTU 帧构建/CRC
│   ├── serial_test.py            力传感器独立监控
│   └── usb_daq_v20/              USB-DAQ Python 库
│
├── firmware/                 【硬件组负责】STM32 底层固件（驱动、TinyML部署等）
│   └── 本人负责嵌入式侧的**数据处理+通信逻辑**，不涉及底层驱动/PCB/TinyML训练部署
│
├── backend/                  【待开发】云端后端服务（Python FastAPI）
│   ├── main.py
│   ├── api/
│   │   ├── ingest.py             原始数据接入接口
│   │   ├── report.py             LLM 报告生成接口
│   │   └── history.py            历史数据查询接口
│   ├── services/
│   │   ├── feature.py            特征提取（步频、COP、对称性）
│   │   └── llm.py                DeepSeek API 封装 + Prompt 工程
│   ├── models/                   数据库 ORM 模型
│   └── config.py                 环境变量（API Key、数据库连接等）
│
├── frontend/                 【待开发】手机 Web 前端（React / Vue + Three.js）
│   ├── src/
│   │   ├── ble/                  Web Bluetooth API 封装
│   │   ├── viz/                  Three.js 可视化组件
│   │   ├── pages/                页面路由
│   │   └── upload.js             后台批量上传队列
│   └── public/
│
└── doc/                      【当前目录】项目文档
    ├── design-overview.md        项目背景、设计思路、功能要点
    ├── software-architecture.md  本文件
    └── data-protocol.md          数据协议定义（BLE帧、HTTP接口）
```

---

## 二、数据流总图

```
┌─────────────────────────────────────────────────────────────────────┐
│  STM32（鞋垫）                                                       │
│  32路FSR → ADC采集 → 滤波 → 步态FSM → TinyML → 32路压力值           │
│                                                ↓                     │
│                                         LED/马达反馈                  │
│                                                                       │
│  两条独立输出链路：                                                    │
│    ① BLE Notify（50Hz）→ 手机 Chrome（近程实时可视化）                │
│    ② LTE HTTP POST（批量）→ 公网云后端（存储 + AI 分析）              │
└───────────────────────────────────────────────────────────┬──────────┘
                                                            │ LTE
            BLE                                             ▼
            ─────────────────────┐          ┌──────────────────────────┐
                                 ▼          │  云端后端（FastAPI）       │
              ┌──────────────────────────┐  │  接收原始压力帧           │
              │  手机 Chrome（Android）   │  │  存数据库                 │
              │                          │  │  特征提取计算             │
              │  模式A：近程蓝牙         │  │  DeepSeek 日报生成        │
              │   BLE 接收 → 解析帧      │  │  REST API                │
              │   Three.js 热力图渲染    │  └──────────────┬───────────┘
              │   COP 轨迹展示           │                 │ HTTPS GET
              │   步态状态显示           │                 │（远程查看）
              │                          │◄────────────────┘
              │  模式B：远程查看         │
              │   HTTPS 拉取历史数据     │
              │   展示 AI 日报           │
              └──────────────────────────┘

  注：两条链路独立，手机不做任何数据中转
```

---

## 三、实体功能清单

### 3.1 STM32 固件（抽象描述）

> **分工**：硬件组负责 PCB/驱动/TinyML 部署；本人负责嵌入式**数据处理与通信逻辑**（数据采集处理流程、BLE 帧封装、LTE 上传逻辑、步态FSM 事件检测），以下表格描述的是本人需要实现的嵌入式数据处理接口。

| 模块 | 对外接口（软件视角） | 说明 |
|------|-------------------|------|
| **FSR 采集** | 输出：32路压力值数组（float，单位 kPa，待标定后确定），100Hz | 左脚 index 0–15，右脚 index 16–31 |
| **IMU 采集** | 输出：三轴加速度、三轴角速度，200Hz | 用于步态事件检测辅助 |
| **步态 FSM** | 输出：步态事件（heel_strike / toe_off）、当前状态（stand/walk/run）| 基于总压力+加速度阈值 |
| **TinyML 推理** | 输入：特征向量；输出：分类（0=正常,1=内八,2=外八）+ 置信度 | 模型待训练后部署 |
| **BLE 发送** | 推送帧，格式见 data-protocol.md，Notify，20ms 周期 | 32路压力值 + 步态状态 + ML结果 |
| **LTE 上传** | STM32 直接 POST 原始压力帧至公网后端，每 N 步批量，与 BLE 推送互不阻塞；手机不做中转 | URL/API Key 写入固件 config |
| **LED/马达反馈** | 输入：步态分类结果 → 控制 LED 颜色 + 马达震动 | 阈值：连续5帧异常才触发，避免误报 |
| **OLED 显示** | 显示：设备状态、步数、BLE/LTE 连接状态 | 低优先级，有时间再做 |

### 3.2 后端（Python FastAPI）

| 模块 | 功能职责 | 接口 | 说明 |
|------|----------|------|------|
| **数据接入** | 接收 STM32 经 LTE 直传的原始压力帧，存入数据库 | `POST /api/ingest` | 单设备，API Key 鉴权（固定值即可） |
| **特征提取** | 对存储的帧序列计算：步频、COP 轨迹、左右对称性指数 | 内部服务，由 ingest 触发 | TBD：具体算法待确认 |
| **LLM 报告** | 定时汇总当日特征，构建 Prompt，调用 DeepSeek API，存储报告 | `GET /api/report/today` | 每日定时或手动触发 |
| **历史查询** | 查询历史报告列表、步态评分趋势 | `GET /api/history` | 按日期查询 |
| **设备心跳** | 接收设备状态上报（可选） | `POST /api/heartbeat` | 有时间再做 |

**数据库表（极简版，SQLite 即可用于演示）：**

```sql
-- 原始压力帧（每 N 步一批）
gait_frames (
    id          INTEGER PRIMARY KEY,
    timestamp   REAL,           -- Unix 时间戳
    pressures   TEXT,           -- JSON array，32 路压力值
    step_count  INTEGER,        -- 该批次步数
    gait_class  INTEGER,        -- TinyML 分类 0/1/2
    ml_conf     REAL            -- 置信度 0.0-1.0
)

-- AI 报告（每日一条）
reports (
    id          INTEGER PRIMARY KEY,
    date        TEXT,           -- YYYY-MM-DD
    report_text TEXT,           -- DeepSeek 生成的报告全文
    summary_json TEXT           -- 结构化摘要（步数、评分等）
)
```

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

### 3.3 前端（React / Vue + Three.js，手机 Chrome）

前端是纯消费端，不做任何数据转发。两种模式相互独立。

**模式 A — 近程蓝牙（实时可视化）**

| 模块 | 功能职责 | 技术要点 |
|------|----------|---------|
| **BLE 连接** | 扫描并连接鞋垫 BLE，订阅 Notify Characteristic，断线自动重连 | `navigator.bluetooth` Web Bluetooth API；GATT UUID 见 data-protocol.md |
| **足底热力图** | 接收 32 路压力值 → 双线性插值 → Three.js 渲染左右脚热力图 | Three.js PlaneGeometry + ShaderMaterial 顶点颜色映射 |
| **COP 轨迹** | 实时计算压力中心，在足底轮廓图上绘制过去 2 秒轨迹 | Three.js LineSegments，滑动窗口缓冲 |
| **步态状态栏** | 显示当前步态分类（正常/内八/外八）及 TinyML 置信度 | React/Vue 组件，根据 BLE 帧数据更新 |
| **异常提醒** | 连续 N 帧异常时页面弹出 Toast 提示 | 组件状态 + CSS 动画 |

**模式 B — 远程查看**

| 模块 | 功能职责 | 技术要点 |
|------|----------|---------|
| **AI 报告页** | 从后端 API 拉取当日/历史 AI 健康日报展示 | `fetch` + 文本展示 |
| **历史数据页** | 查看历史步态评分趋势（可选，有时间再做） | Chart.js 简单折线图 |

**页面结构：**

```
/realtime   近程蓝牙页（模式 A）
  ├─ BLE 连接/断开按钮
  ├─ 足底热力图（Three.js，左右脚）
  ├─ COP 轨迹图
  └─ 步态状态栏 + 异常 Toast

/report     远程查看页（模式 B）
  ├─ 今日 AI 日报文字
  └─ 历史日期切换（简单下拉）
```

### 3.4 win-datacap（标定工具，已有 + 待补充）

| 组件 | 状态 | 待补充内容 |
|------|------|-----------|
| `server.py` | 完整可用 | 无需改动 |
| `force_server.py` | 完整可用 | 无需改动 |
| `fsr_calibrate.py` | 可视化对比（无导出） | **待补充**：多项式拟合 + 导出 `calibration.json` |
| `modbus_rtu.py` | 完整可用 | 无需改动 |

---

## 四、开发优先级

```
阶段 1 — 实时可视化闭环（最先做）
  ├── 前端：BLE 连接 + 热力图渲染
  └── 固件：BLE 发送压力帧

阶段 2 — 云端 AI 闭环
  ├── 后端：数据接入 + SQLite 存储
  ├── 后端：DeepSeek 报告生成
  └── 前端：报告页展示

阶段 3 — 完整度补充（有时间再做）
  ├── 前端：历史趋势图
  ├── 固件：GPS 解析 + LTE 上传优化
  └── win-datacap：标定曲线导出
```

部署与上云说明见 [deployment.md](deployment.md)。
