# Progress（进展与里程碑）

> 项目的「状态快照」：已完成、待办、已知问题。
> 最近更新：2026-07-06

## 已完成

### win-datacap 标定工具（`tools/win-datacap/`，Windows PC）

USB 采集卡（32 路 FSR）+ Modbus 参考压力传感器的采集、标定、拟合工具集。2026-07-09 从仓库根目录整理迁入 `tools/`，与 `insoles-boundary` 并列；完整流程见 [`tools/win-datacap/docs/CALIBRATION_PIPELINE.md`](../../tools/win-datacap/docs/CALIBRATION_PIPELINE.md)。

| 文件 | 功能 | 状态 |
|------|------|------|
| `server.py` | USB-DAQ 32 路 FSR → TCP :6543 | ✅ 完整可用 |
| `force_server.py` | Modbus 压力传感器 → WebSocket :8765 | ✅ 完整可用 |
| `fsr_calibrate.py`（`fsr_calibrate/`） | ADC vs 参考压力实时 UI + 时间对齐 CSV 录制 | ✅ 完整可用 |
| `plot_fsr_grid_fit.py` | 批量拟合 `record/*.csv` → `result.yml`（指数/幂/倒数三模型 + R²） | ✅ 完整可用 |
| `best_rx.ipynb` | 基于幂函数拟合仿真 12-bit ADC 量化误差，选型参考电阻 Rx | ✅ 可用（手工改参数重跑） |
| `modbus_rtu.py` | Modbus RTU 帧构建/CRC | ✅ 完整可用 |
| `usb_daq_v20/` | USB-DAQ Python 库 | ✅ 完整可用 |

### 鞋垫边界拟合工具（`tools/insoles-boundary/`）

鞋垫照片手动抠图 → 二值掩码 → 周期 B-spline 参数化 → 导出可携带 `render_payload.json`（17 区域）。原为 `ignored/` 下独立 git 仓库，2026-07-09 整理留存到父仓库并追踪。

| 内容 | 状态 |
|------|------|
| 核心算法库 `src/insoles/`（uniform/adaptive B-spline、边界指标、OBB/坐标变换、payload 导出） | ✅ |
| 流水线脚本 `scripts/`（缩放/拟合/导出/重绘/重映射） | ✅ |
| 可复现数据集（`masks*/`、`contours*/`、`reports/`，含 `render_payload.json`） | ✅ 已追踪 |
| 处理过程文档 `docs/PIPELINE.md` + 记忆/任务/讨论快照 | ✅ |
| 原始大文件（`insoles.psd`/照片/验证图） | 保留在 `ignored/insoles-boundary/ignored/`（不入 git） |

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

### 后端（`backend_prod/` — 唯一权威）

| 模块 | 状态 |
|------|------|
| `config.py` + `.env` + `llm_config.yml` | ✅ |
| `database.py` + SQLite | ✅ |
| `protocol/device_frame.py` + `payloads.py` | ✅ |
| `services/ingest.py` + `tcp_ingest.py` | ✅ |
| `services/feature.py` + `services/llm.py` | ✅ |
| `api/*`（activity/gait/gps/report/ingest） | ✅ |
| `tests/` + `scripts/simulate_ingest.py` | ✅ |

### 部署（ECS 47.76.112.33）

| 项 | 状态 |
|----|------|
| `deploy/deploy.ps1` 一键同步 | ✅ 同步 `backend_prod/` |
| `deploy/server-init.sh` 初始化 | ✅ 已执行 |
| Nginx `/` `/insoles/` `/api/` `/health` | ✅ |
| systemd `magic-insoles-api` | ✅ |
| 外网 TCP 80 | ⏳ 待安全组放行 |

### 已弃用（不再维护）

- `backend/` — FastAPI 测试桩，见 `backend/DEPRECATED.md` 与 ADR-0003

### 数字大脑

- `.cursor/memories/` 六层记忆 + ADR-0003
- `.cursor/tasks/`、`issues/`、`skills/`、`rules/` workflow 就绪

## 进行中

- ECS 生产环境稳定化（安全组、`.env`、设备 TCP 9000）
- 硬件/标定 TBD 项确认

## 待办

### 生产运维

- [ ] 阿里云安全组入站 TCP 80
- [ ] 服务器配置 `DEEPSEEK_API_KEY`
- [ ] 设备接入时安全组 TCP 9000

### 前端打磨

- [ ] 真机 BLE 联调（需 HTTPS）
- [ ] 高德地图适配（`VITE_AMAP_KEY`）
- [ ] 空状态/加载态/错误态全覆盖

### 标定与嵌入式

- [x] ~~`fsr_calibrate.py` 拟合 + 导出标定参数~~ 已由 `plot_fsr_grid_fit.py` 实现（三模型拟合 → `result.yml`，见 `tools/win-datacap/docs/CALIBRATION_PIPELINE.md`）
- [ ] `best_rx.ipynb`：Rx 从手工改参数升级为网格搜索，自动输出「最优 Rx vs 最大相对误差」表格
- [ ] TinyML 模型采集训练部署（硬件组主导）
- [ ] STM32 BLE 发送压力帧（固件）
- [ ] STM32 C serial bridge → 后端 TCP :9000

### 扩展（时间充裕）

- [ ] GPS 运动轨迹真数据
- [ ] 历史步态评分趋势图
- [ ] OLED 显示设备状态

## 已知问题 / 技术债

| 问题 | 影响 | 临时规避 |
|------|------|----------|
| TBD-1~5 坐标/标定/UUID 未确认 | 算法精度、真机联调 | 4×4 均匀网格占位 |
| http IP 下 BLE 不可用 | 真机 `/realtime` 测试 | localhost 或 HTTPS |
| 安全组未放行 80 | 外网无法访问 | 服务器本机 curl 已验证 |
| 无 DeepSeek Key | 日报生成失败 | 配置 `.env` |
| 平衡评估评分算法未定（TBD-BAL） | 评分逻辑可能调整 | 前端本地 COP 椭圆面积方案 |

## 里程碑记录

| 日期 | 里程碑 | 摘要 |
|------|--------|------|
| 2026-06 | 硬件打板完成 | STM32 PCB + FSR 鞋垫 32 路 |
| 2026-06 | 前端骨架完成 | 7 页面 + BLE/viz 模块 + 响应式布局 |
| 2026-06 | 后端测试桩 | mock API（**已弃用**） |
| 2026-07-06 | 数字大脑初始化 | doc/TODO 归档，memories/tasks 就绪 |
| 2026-07-06 | 设备接入协议定稿 | TCP 二进制帧；Force 30Hz/uint16 |
| 2026-07-06 | backend_prod 为唯一后端 | 弃用 `backend/`；ADR-0003 |
| 2026-07-06 | ECS 首次部署 | deploy.ps1 + nginx + systemd |
| 2026-07-09 | 鞋垫边界拟合工具留存 | `tools/insoles-boundary/` 代码+数据+文档入 git；见 task 2026-07-09-preserve-insoles-boundary |
| 2026-07-09 | win-datacap 迁入 tools/ | `win-datacap/` → `tools/win-datacap/`（git mv 保留历史）；新增 `docs/CALIBRATION_PIPELINE.md` 说明标定/拟合/Rx选型；见 task 2026-07-09-reorganize-win-datacap |
