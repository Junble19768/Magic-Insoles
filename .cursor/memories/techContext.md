# Tech Context（技术栈与环境）

> 让 AI/新成员能快速把项目跑起来、并了解技术约束。
> 最近更新：2026-07-06

## 技术栈

| 模块 | 技术选型 | 备注 |
|------|---------|------|
| 前端框架 | React + TypeScript（strict） | Vite 构建 |
| 热力图渲染 | Three.js | PlaneGeometry + ShaderMaterial |
| BLE | Web Bluetooth API | **仅 Android Chrome** |
| 地图 | Leaflet.js + OpenStreetMap（默认）；高德可选（`VITE_AMAP_KEY`） | |
| 后端 | Python FastAPI | 公网云部署 |
| 数据库 | SQLite（演示阶段） | 单设备 |
| LLM | DeepSeek API | `https://api.deepseek.com` |
| 嵌入式 | STM32 + TinyML（X-CUBE-AI / TFLite Micro 待确认） | 硬件组训练部署 |
| 标定工具 | Python（win-datacap） | Windows USB-DAQ |
| 用户系统 | 无（固定 API Key） | `dev-magic-insoles-key` |

## 本地开发

```bash
# 终端 1 — 后端
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 终端 2 — 前端（注意 base 路径）
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173/insoles/
```

Vite `server.proxy` 将 `/api` 代理到 `http://127.0.0.1:8000`。

## 环境与配置

| 变量 | 说明 | 示例 |
|------|------|------|
| `API_KEY` / `VITE_API_KEY` | 设备/前端鉴权 | `dev-magic-insoles-key` |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 从 `.env` 读取，不提交 git |
| `DEEPSEEK_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `DB_PATH` | SQLite 路径 | `./data/magic_insoles.db` |
| `CORS_ORIGINS` | 允许的前端源 | `http://localhost:5173` |
| `VITE_API_BASE_URL` | 前端 API 基址 | `/api`（默认，站点根相对路径） |
| `VITE_AMAP_KEY` | 高德地图 Key（可选） | — |

### 前端部署配置（必须）

- `frontend/vite.config.ts`：`base: '/insoles/'`
- `frontend/src/main.tsx`：`BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, '')}`
- `frontend/index.html`：favicon 使用 `%BASE_URL%favicon.svg`

## BLE 协议

### GATT 服务定义

| 项目 | 值 |
|------|-----|
| Service UUID | `0000FFF0-0000-1000-8000-00805F9B34FB` |
| Notify Characteristic UUID | `0000FFF1-0000-1000-8000-00805F9B34FB` |
| Write Characteristic UUID（平衡评估） | `0000FFF2-0000-1000-8000-00805F9B34FB` |
| 属性 | Notify（压力帧）；Write（控制命令） |
| 推送周期 | 20ms（50Hz） |

### BLE 帧格式（二进制，小端序，41 字节）

| Offset | Size | Type | 字段名 | 说明 |
|--------|------|------|--------|------|
| 0 | 1 | uint8 | frame_type | 0x01=压力帧，0x02=评估帧 |
| 1 | 2 | uint16 | seq | 帧序号（0-65535 循环） |
| 3 | 32 | uint8 | pressure[32] | 0-255 归一化；index 0-15 左脚，16-31 右脚 |
| 35 | 1 | uint8 | gait_state | 0=站立 1=行走 2=跑步 |
| 36 | 1 | uint8 | ml_class | 0=正常 1=内八 2=外八 |
| 37 | 1 | uint8 | ml_conf | 置信度 0-100 |
| 38 | 2 | uint16 | step_count | 累计步数（低字节在前） |
| 40 | 1 | uint8 | battery | 电量 0-100% |

**平衡评估命令**：`0x02 0x01`（开始）/ `0x02 0x00`（停止）

### JavaScript 解析示例

```javascript
function parseInsoleFrame(dataView) {
  const frameType = dataView.getUint8(0);
  if (frameType !== 0x01) return null;
  return {
    seq: dataView.getUint16(1, true),
    pressures: new Array(32).fill(0).map((_, i) => dataView.getUint8(3 + i)),
    gaitState: dataView.getUint8(35),
    mlClass: dataView.getUint8(36),
    mlConf: dataView.getUint8(37) / 100,
    stepCount: dataView.getUint16(38, true),
    battery: dataView.getUint8(40),
    leftFoot: null,  // slice(0,16) after parse
    rightFoot: null, // slice(16,32) after parse
  };
}
```

## HTTP API

### Base URL

| 环境 | Base URL |
|------|----------|
| 生产（目标） | `https://<domain>/api` |
| 测试（当前） | `http://<ECS公网IP>/api` |

**鉴权**：Header `X-API-Key: <固定密钥>`

### 端点一览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ingest` | STM32 LTE 批量上传原始帧 |
| GET | `/api/report/today` | 今日 AI 日报 |
| GET | `/api/report/history?days=7` | 历史日报列表 |
| GET | `/api/report?period=today\|week\|month` | 多周期 AI 报告 |
| POST | `/api/report/generate` | 手动触发报告生成（调试） |
| GET | `/api/activity/today` | 今日运动摘要 |
| GET | `/api/activity/history?days=7` | 步数历史 |
| GET | `/api/gait/summary?date=` | 步态分析数据 |
| GET | `/api/gps/routes?date=` | GPS 轨迹 |
| POST | `/api/heartbeat` | 设备心跳（可选） |
| GET | `/health` | 健康检查 |

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

### DeepSeek Prompt 模板要点

- 角色：儿童运动健康顾问
- 输入：运动时长、步数、步频、步态评估、异常比例、对称性描述
- 输出：150 字以内家长日报；友好、非医学诊断；含运动总结、改善建议、鼓励语

## 数据量估算

| 场景 | 数据量 |
|------|--------|
| BLE 帧大小 | 41 字节/帧 |
| BLE 推送频率 | 50Hz → ~2KB/s（仅手机本地） |
| LTE 上传频率 | 每 N 步一批，~820 字节/批 |
| 每日存储（活动 1 小时） | ~7.4 MB 原始帧 |

## 部署架构（阿里云 ECS 方案 A）

| 项 | 说明 |
|----|------|
| 云主机 | 阿里云 ECS，2 核 2G（测试阶段） |
| 共机 | 外部中小企业官网（`/`）+ magic-insoles（`/insoles/` + `/api/`） |
| 域名 | 当前无域名，`http://<ECS公网IP>/` 访问 |

### Nginx 路径路由

| 路径 | 服务 | 目录/进程 |
|------|------|-----------|
| `/` | 外部官网静态站 | `/var/www/corp/dist` |
| `/insoles/` | magic-insoles 前端 SPA | `/var/www/insoles/dist` |
| `/api/` | FastAPI | uvicorn `127.0.0.1:8000`，Nginx 反代 |

### 部署步骤摘要

```bash
# 前端 build
cd frontend && npm run build
# 上传 dist/ → ECS:/var/www/insoles/dist

# 后端
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# 参考 deploy/magic-insoles-api.service 配置 systemd
# 参考 deploy/nginx.conf 配置 Nginx
nginx -t && systemctl reload nginx
systemctl enable --now magic-insoles-api
```

安全组放行入站 TCP 80。

### 验证清单

- `http://<IP>/` → 官网
- `http://<IP>/insoles/` → 鞋垫应用
- `http://<IP>/api/health` → `{"status":"ok"}`
- 刷新 `/insoles/dashboard` 不出现 404

## 技术约束

- BLE 仅 Android Chrome；http IP 访问时真机 BLE 不可用，需 HTTPS
- SQLite 演示阶段，无需迁移数据库
- STM32 经 LTE 直传 `POST /api/ingest`，手机不做中转
- API Key 写入固件 config，与前端 `VITE_API_KEY` 一致
- 正式对外推广需域名 + ICP 备案

## win-datacap（标定工具，已有）

| 文件 | 功能 | 状态 |
|------|------|------|
| `server.py` | USB-DAQ 32 路 FSR → TCP :6543 | 完整可用 |
| `force_server.py` | Modbus 压力传感器 → WebSocket :8765 | 完整可用 |
| `fsr_calibrate.py` | ADC vs 参考压力双轴对比 GUI | 待补充拟合导出 |
| `modbus_rtu.py` | Modbus RTU 帧构建/CRC | 完整可用 |
| `usb_daq_v20/` | USB-DAQ Python 库 | 完整可用 |

`server.py` 扫描：6 行（DO 选通）× 8 列（ADC 采样）= 48 次读取，映射到 32 路有效通道。

## 待确认项（TBD）

| 编号 | 内容 | 影响 |
|------|------|------|
| TBD-1 | FSR 传感器物理坐标映射（index → 前掌/后跟/内外侧） | 热力图、COP 计算 |
| TBD-2 | COP 坐标轴方向及左右脚镜像规则 | 前端轨迹显示 |
| TBD-3 | ADC 电压 → 压力值标定曲线 | 物理量展示 |
| TBD-4 | TinyML 模型（待采集数据后训练） | 固件推理 |
| TBD-5 | BLE GATT UUID 最终值 | 前端 BLE 连接 |
| TBD-BLE | 平衡评估 Write UUID + 命令格式 | balance 页 |
| TBD-GPS | GPS 坐标存储位置 | 后端模型 |
| TBD-MAP | 高德地图 API Key | MapContainer |
| TBD-BAL | 平衡评分算法（椭圆面积 vs 标准差） | cop.ts 评分函数 |

## 外部依赖 / 集成

- DeepSeek Chat API（日报生成）
- 阿里云 ECS + Nginx（部署）
- Leaflet.js / OpenStreetMap（地图，免费）
- 高德地图 JS API 2.0（可选，`VITE_AMAP_KEY`）

## 原始文档备份

详细规格已归档至 `.cursor/bakup/doc/`（project-context、design-overview、software-architecture、data-protocol、deployment、frontend）。
