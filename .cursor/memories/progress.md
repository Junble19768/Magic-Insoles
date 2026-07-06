# Progress（进展与里程碑）

> 项目的「状态快照」：已完成、待办、已知问题。
> 最近更新：2026-07-06

## 已完成

### win-datacap 标定工具（Windows PC）

| 文件 | 功能 | 状态 |
|------|------|------|
| `server.py` | USB-DAQ 32 路 FSR → TCP :6543 | ✅ 完整可用 |
| `force_server.py` | Modbus 压力传感器 → WebSocket :8765 | ✅ 完整可用 |
| `fsr_calibrate.py` | ADC vs 参考压力双轴对比 GUI | ✅ 可用，待拟合导出 |
| `modbus_rtu.py` | Modbus RTU 帧构建/CRC | ✅ 完整可用 |
| `usb_daq_v20/` | USB-DAQ Python 库 | ✅ 完整可用 |

### 前端（React + Three.js）

| 模块 | 位置 | 状态 |
|------|------|------|
| 响应式布局 | `PcSidebar` / `MobileTabBar` / `useMediaQuery` | ✅ |
| 7 个页面 | Dashboard/Activity/Gait/Gps/Report/Realtime/Balance | ✅ 骨架完成 |
| BLE 帧解析 | `frameParser.ts` | ✅ |
| Mock 数据流 | `mockData.ts` | ✅ |
| 热力图渲染 | `HeatmapCanvas.tsx` | ✅ |
| COP 轨迹 | `CopTrajectory.tsx` / `cop.ts` | ✅ |
| 设备管理 | `bleService.ts` / `deviceStore.ts` / `BleDevicePanel` | ✅ 骨架 |
| 平衡评估 | `useBalanceAssessment` / Balance 组件 | ✅ 骨架 |
| API 客户端 | `client.ts`（全部端点封装） | ✅ |
| 类型定义 | `types/index.ts` | ✅ 已扩展 |

### 后端（FastAPI 测试桩）

| 端点 | 状态 |
|------|------|
| `GET /api/report/today` | ✅ mock |
| `GET /api/report/history` | ✅ mock |
| `GET /api/report?period=` | ✅ mock |
| `GET /api/activity/today` | ✅ mock |
| `GET /api/activity/history` | ✅ mock |
| `GET /api/gait/summary` | ✅ mock |
| `GET /api/gps/routes` | ✅ mock |
| `POST /api/ingest` | ✅ 打印日志 |
| `GET /health` | ✅ |

### 部署模板

- `deploy/nginx.conf` — Nginx 路径路由
- `deploy/magic-insoles-api.service` — systemd 单元

### 数字大脑

- `.cursor/memories/` 六层记忆文件已初始化
- `.cursor/tasks/`、`issues/`、`skills/`、`rules/` workflow 就绪

## 进行中

- **后端完整实施**（当前桩 → config/db/ingest/feature/llm/report），见 Task Plan

## 待办

### 后端（优先级最高）

- [ ] `config.py` + `database.py` + `models/schemas.py`
- [ ] `api/deps.py`（API Key 校验）
- [ ] `api/ingest.py`（存库）
- [ ] `services/feature.py`（步频、COP、对称性）
- [ ] `services/llm.py`（DeepSeek 调用）
- [ ] `api/report.py`（查询 + 生成）
- [ ] 替换 `main.py` 测试桩为完整路由
- [ ] `tests/` + `scripts/simulate_ingest.py`

### 前端打磨

- [ ] 真机 BLE 联调（需 HTTPS）
- [ ] 高德地图适配（`VITE_AMAP_KEY`）
- [ ] 空状态/加载态/错误态全覆盖

### 标定与嵌入式

- [ ] `fsr_calibrate.py` 多项式拟合 + 导出 `calibration.json`
- [ ] TinyML 模型采集训练部署（硬件组主导）
- [ ] STM32 BLE 发送压力帧（固件）
- [ ] STM32 LTE 直传后端（固件）

### 扩展（时间充裕）

- [ ] GPS 运动轨迹真数据
- [ ] 历史步态评分趋势图
- [ ] OLED 显示设备状态

## 已知问题 / 技术债

| 问题 | 影响 | 临时规避 |
|------|------|----------|
| TBD-1~5 坐标/标定/UUID 未确认 | 算法精度、真机联调 | 4×4 均匀网格占位 |
| http IP 下 BLE 不可用 | 真机 `/realtime` 测试 | localhost 开发或配置 HTTPS |
| `sensorLayout.ts` 坐标占位 | 热力图/COP 方向可能不准 | 待 TBD-1 后替换 |
| 后端无真实存储 | 报告/步态/GPS 均为 mock | 按 Task Plan 实施 |
| 平衡评估评分算法未定（TBD-BAL） | 评分逻辑可能调整 | 前端本地 COP 椭圆面积方案 |

## 里程碑记录

| 日期 | 里程碑 | 摘要 |
|------|--------|------|
| 2026-06 | 硬件打板完成 | STM32 PCB + FSR 鞋垫 32 路 |
| 2026-06 | 前端骨架完成 | 7 页面 + BLE/viz 模块 + 响应式布局 |
| 2026-06 | 后端测试桩 | mock 全部 API 供前端联调 |
| 2026-07-06 | 数字大脑初始化 | doc/TODO/TALK 归档，memories/tasks 就绪 |
