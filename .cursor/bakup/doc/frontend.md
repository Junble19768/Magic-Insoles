# magic-insoles 前端功能需求与实现方案

> 本文档整合已完成内容与新需求，作为前端开发的权威参考。
> 更新：2026-06-29

---

## 一、产品定位

Web 管理后台（PC 为主）+ 手机近程可视化工具。

- **PC 端**：远程监控（Dashboard、GPS、运动数据、步态分析、AI 报告），东亚健康软件后台视觉风格
- **手机端**：上述全部页面响应式适配 + BLE 近程功能（设备管理、实时压力可视化、平衡评估）

用户系统：最小方案，后端 user_id + 固定 token，无登录注册。

---

## 二、视觉设计方向

**东亚健康软件后台风格**：
- 白底 + 浅灰卡片，大量留白
- 主色调延续品牌绿 `#163B31`，辅色 `#2F8F78`
- 数据卡片式布局，指标数字突出
- 图表色系沉稳（蓝绿渐变，避免霓虹色）
- 字体：PC 端适当放大标题和数字，移动端紧凑
- 参考：小米健康、华为运动健康后台的数据看板风格

**对比之前**：当前 `/realtime` 页是手机紧凑风格，PC 页需要重新设计布局（见第三节）。

---

## 三、页面路由与导航

### 3.1 路由表

| 路由 | 页面 | PC | 手机 | BLE 依赖 |
|------|------|:--:|:----:|:--------:|
| `/` | 重定向 → `/dashboard` | ✅ | ✅ | — |
| `/dashboard` | 设备 DashBoard | ✅ | ✅ | 设备列表需 BLE |
| `/activity` | 运动情况 | ✅ | ✅ | — |
| `/gait` | 步态分析 | ✅ | ✅ | — |
| `/gps` | GPS 轨迹 | ✅ | ✅ | — |
| `/report` | 运动报告 | ✅ | ✅ | — |
| `/realtime` | 实时压力可视化 | — | ✅ | ✅ |
| `/balance` | 平衡能力评估 | — | ✅ | ✅ |

### 3.2 导航方案

**PC（≥768px）**：
```
┌──────┬──────────────────────────────┐
│      │                              │
│ Side │       Page Content            │
│ bar  │                              │
│      │                              │
└──────┴──────────────────────────────┘
```
- 左侧垂直导航，图标 + 文字
- 菜单项：DashBoard、运动情况、步态分析、GPS 轨迹、运动报告
- `/realtime`、`/balance` 不出现在 PC 导航中

**手机（<768px）**：
```
┌──────────────────────────────────────┐
│          Page Content                │
│                                      │
├──────────┬──────────┬───────────────┤
│ DashBoard│ 运动情况 │ 步态分析       │
├──────────┼──────────┼───────────────┤
│  GPS轨迹 │ 运动报告 │     更多      │
└──────────┴──────────┴───────────────┘
```
- 底部 Tab 导航，5 个主项 + "更多"（展开 `/realtime`、`/balance`）

### 3.3 响应式断点

| 断点 | 布局 |
|------|------|
| `< 768px` | 手机：底部 Tab，单栏卡片，紧凑排版 |
| `≥ 768px` | PC：侧边栏导航，多栏卡片网格，宽松留白 |
| `≥ 1200px` | 大屏：最大宽度 1400px 居中 |

---

## 四、页面详细设计

### 4.1 设备 DashBoard（`/dashboard`）

**定位**：首页概览 + 设备管理入口。

**布局（PC）**：
```
┌──────────────────────────────────────────────┐
│  [总步数 8,432] [运动时长 42min] [距离 3.2km] [步态状态 正常] │  ← 顶部指标卡
├──────────────────────────────────────────────┤
│                                              │
│  [最近7天步数趋势 迷你柱状图]                  │  ← 快速概览
│                                              │
├──────────────────────────────────────────────┤
│  设备管理                                     │
│  ┌─────────────────────────────────────┐     │
│  │ 鞋垫 #1  已连接  电量 82%  [断开]    │     │  ← 设备卡片列表
│  │ 上次连接 2026-06-29 15:30           │     │
│  └─────────────────────────────────────┘     │
│  [+ 添加设备]                                 │  ← 手机端触发 BLE 扫描
└──────────────────────────────────────────────┘
```

**数据来源**：
- 顶部指标：`GET /api/activity/today`
- 迷你图表：`GET /api/activity/history?days=7`
- 设备列表：前端 `localStorage` + BLE 连接状态（`bleService`）

**复用/新增组件**：设备卡片组件（`DeviceCard`）、迷你柱状图（`MiniBarChart`）、指标卡片（`MetricCard`）

---

### 4.2 运动情况（`/activity`）

**布局（PC）**：
```
┌──────────────────────────────────────────────┐
│  [今日步数]         [有效运动时间]    [运动距离]  │  ← 三大指标，大号数字
│   8,432 步           42 分钟          3.2 km   │
├──────────────────────────────────────────────┤
│  最近7天步数                                   │
│  ██                                              │  ← 柱状图
│  ██ ██                                           │
│  ██ ██ ██ ██ ██ ██ ██                           │
│  22  23  24  25  26  27  28                     │
└──────────────────────────────────────────────┘
```

**数据来源**：
- `GET /api/activity/today` → `{ steps, activeMinutes, distanceKm }`
- `GET /api/activity/history?days=7` → `{ days: [{ date, steps }] }`

**新增 API**：

```
GET /api/activity/today
Response: {
  "date": "2026-06-29",
  "steps": 8432,
  "activeMinutes": 42,
  "distanceKm": 3.2
}

GET /api/activity/history?days=7
Response: {
  "days": [
    { "date": "2026-06-22", "steps": 7800 },
    ...
  ]
}
```

**新增组件**：柱状图（使用 Canvas 或轻量 Chart 库如 uPlot/recharts）

---

### 4.3 步态分析（`/gait`）

**定位**：历史步态数据回放分析（数据来自后端）。

**布局（PC）**：
```
┌──────────────────────────────────────────────┐
│  步态分析                        [2026-06-29 ▼]│  ← 日期选择
├──────────────────┬───────────────────────────┤
│                  │                           │
│  [左脚热力图]     │  [右脚热力图]              │  ← 左右并排
│  + COP 散点叠加   │  + COP 散点叠加            │
│                  │                           │
├──────────────────┴───────────────────────────┤
│  分析结果                                     │
│  左脚：正常 (置信度 92%)    右脚：轻微内八 (78%)│
│  综合评估：步态基本正常，建议关注右脚内旋倾向     │
└──────────────────────────────────────────────┘
```

**数据来源**：`GET /api/gait/summary?date=2026-06-29`

**新增 API**：

```
GET /api/gait/summary?date=YYYY-MM-DD
Response: {
  "date": "2026-06-29",
  "leftFoot": {
    "pressures": [0, 12, ..., 255],     // 16 个值，当日平均压力分布
    "copPoints": [                       // COP 轨迹点（下采样至 ~100 点）
      { "x": 0.2, "y": -0.8, "pressure": 1800 },
      ...
    ],
    "classification": "normal",
    "confidence": 0.92
  },
  "rightFoot": {
    "pressures": [...],
    "copPoints": [...],
    "classification": "in_toe",
    "confidence": 0.78
  },
  "overallAssessment": "步态基本正常，建议关注右脚内旋倾向"
}
```

**复用组件**：复用 `HeatmapCanvas` 的热力图材质逻辑，新增 `FootAnalysisCanvas`（静态热力图 + COP 散点叠加）。

---

### 4.4 GPS 轨迹（`/gps`）

**定位**：展示户外活动的 GPS 轨迹，双地图方案（Leaflet 默认，高德可选）。

**数据来源**：STM32 通过 LTE 上传 GPS 坐标到后端 → `GET /api/gps/routes?date=2026-06-29`

**新增 API**：

```
GET /api/gps/routes?date=YYYY-MM-DD
Response: {
  "date": "2026-06-29",
  "points": [
    { "timestamp": 1751000000, "lat": 39.9042, "lng": 116.4074 },
    ...
  ],
  "totalDistanceKm": 3.2,
  "durationMinutes": 42
}
```

**地图方案**：
- **默认**：Leaflet.js + OpenStreetMap（免费、无需 Key）
- **可选**：高德地图 JS API 2.0（通过环境变量 `VITE_AMAP_KEY` 切换）
- 统一封装 `MapContainer` 组件，内部根据配置选择地图引擎

**组件**：`MapContainer`（内部 Leaflet/AMap 适配器）、轨迹折线、起终点标记、距离/时间信息卡片。

---

### 4.5 运动报告（`/report`）

**定位**：LLM 生成的多周期健康日报（复用现有骨架，扩展周期）。

**新增需求**：支持三个周期切换 — 今日报告 / 近一周 / 近一个月。

**新增 API**：

```
GET /api/report?period=today|week|month
Response: {
  "period": "today",
  "dateRange": { "start": "2026-06-29", "end": "2026-06-29" },
  "reportText": "过去一周，宝贝累计步行 21,430 步...",
  "stepCount": 21430,
  "gaitSummary": "步态整体正常，偶有轻度内八（占比 8%）",
  "generatedAt": 1751080000
}
```

**组件变更**：`ReportPage` 新增 `PeriodSelector`（三个 Tab 切换），复用现有 `ReportCard`。

---

### 4.6 实时压力可视化（`/realtime`）【手机专属】

**已有基础**：当前 `/realtime` 页面已实现 mock 数据流 + 热力图 + COP 轨迹 + 步态状态栏。

**需新增**：
1. **设备扫描与配对**：
   - "扫描设备" 按钮 → 调用 `navigator.bluetooth.requestDevice()`（系统原生蓝牙选择器）
   - 选中设备后连接 → 读取设备名称等信息 → 保存设备 ID 到 `localStorage`
   - 下次打开页面自动尝试重连已保存设备
   - **无需特殊 UI 列表**（Web Bluetooth 限制，系统选择器代替）

2. **已保存设备管理**：
   - 显示已配对设备信息（名称、上次连接时间、电池）
   - 一键连接 / 断开 / 忘记设备

**组件变更**：
- `BleConnectButton` 重构为 `BleDevicePanel`（含扫描、已保存设备列表、连接状态）
- `bleService.ts` 新增：
  - `scanAndConnect(): Promise<SavedDeviceInfo>`
  - `reconnectSavedDevice(): Promise<boolean>`
  - `getSavedDevice(): SavedDeviceInfo | null`
  - `forgetDevice(): void`
  - `writeCommand(data: ArrayBuffer): Promise<void>`（用于平衡评估等控制指令）

---

### 4.7 平衡能力评估（`/balance`）【手机专属】

**定位**：纯前端 + BLE 实时功能，不依赖后端。

**交互流程**：
```
┌─────────────────────────────────────┐
│  [开始评估]                          │  ← 初始状态
│  请保持站立姿势，点击开始后              │
│  保持 30 秒稳定站立                    │
├─────────────────────────────────────┤
│  ⏱ 剩余 22 秒                        │  ← 评估中状态
│                                      │
│  [左右脚实时热力图]                    │
│                                      │
│  [重心位置指示器]                      │  ← 实时 COP 显示
│  ● (重心偏左，请调整)                  │  ← 实时提示
├─────────────────────────────────────┤
│  评估完成！                           │  ← 结果状态
│  评分：85 分 等级：良好               │
│  [30 秒重心轨迹图]                    │
│  [左右脚平均压力分布热力图]            │
│  [重新评估]                           │
└─────────────────────────────────────┘
```

**技术实现**：
1. **BLE 命令**：手机通过 BLE Write Characteristic 发送 `0x02`（开始评估模式）→ STM32 切换至平衡模式（固定采集参数、可能调高频率）
2. **30 秒计时**：前端倒计时，每帧更新 COP 和压力显示
3. **实时提示**：根据 COP 位置判断重心偏移方向，显示文字提示（"重心偏左"、"重心偏右"、"重心偏前"、"重心偏后"、"保持稳定"）
4. **评分计算**（前端本地）：
   - 计算 30 秒内 COP 轨迹的覆盖面积（椭圆面积）
   - 计算 COP 离散度（标准差）
   - 映射到 0-100 分
   - 分级：优秀(≥85)、良好(70-84)、一般(55-69)、需改善(<55)
5. **结果展示**：轨迹图 + 平均压力热力图 + 评分 + 等级 + 建议文字

**新增 BLE 协议**（需与硬件组确认）：

| 项目 | 值 |
|------|-----|
| Write Characteristic UUID | `0000FFF2-0000-1000-8000-00805F9B34FB` |
| 开始评估命令 | `0x02 0x01`（2 字节：cmd + param） |
| 停止评估命令 | `0x02 0x00` |
| 评估帧标记 | Notify 帧中 `frame_type` = `0x02`（区别于普通压力帧 `0x01`） |

**新增类型**：

```typescript
interface BalanceState {
  status: 'idle' | 'running' | 'done'
  elapsedMs: number
  frames: PressureFrame[]
  copHistory: { left: CopPoint[]; right: CopPoint[] }
  postureTip: string | null
}

interface BalanceResult {
  score: number
  grade: 'excellent' | 'good' | 'fair' | 'needs_improvement'
  leftCopTrajectory: CopPoint[]
  rightCopTrajectory: CopPoint[]
  leftAvgPressures: number[]
  rightAvgPressures: number[]
  swayArea: number
  copStdDev: number
}
```

---

## 五、前后端功能划分

### 前端负责

| 功能 | 说明 |
|------|------|
| 页面 UI 与交互 | 所有页面的布局、卡片、图表渲染 |
| 响应式适配 | PC 侧边栏 / 手机底部 Tab 切换 |
| BLE 设备扫描/连接 | Web Bluetooth API，设备信息存 localStorage |
| BLE 帧解析 | 解析 41 字节压力帧（已有 `frameParser.ts`） |
| Mock 数据流 | 开发阶段模拟 BLE 帧（已有 `mockData.ts`） |
| 热力图渲染 | Three.js 顶点颜色映射（已有） |
| COP 计算与可视化 | 加权平均 + 轨迹渐隐（已有） |
| 平衡评估评分 | 30s COP 数据分析 + 评分（前端本地计算） |
| 地图渲染 | Leaflet.js / 高德地图轨迹展示 |
| 柱状图 | 7 天步数趋势 |
| API 请求封装 | `fetch` + API Key Header（已有） |
| 设备配对信息 | 存 localStorage |

### 后端负责（新增 API）

| API | 方法 | 说明 |
|-----|------|------|
| `/api/activity/today` | GET | 今日运动摘要（步数/时长/距离） |
| `/api/activity/history` | GET | 指定天数步数历史 |
| `/api/gait/summary` | GET | 指定日期步态分析数据 |
| `/api/gps/routes` | GET | 指定日期 GPS 轨迹 |
| `/api/report?period=` | GET | 多周期 AI 报告 |
| `/api/ingest` | POST | 已有，无需改动 |
| `/api/report/generate` | POST | 已有，需扩展 period 参数 |

### 后端负责（服务层）

| 服务 | 说明 |
|------|------|
| `feature.py` | 从 `gait_frames` 计算：步频、COP 平均值、对称性、步数汇总 |
| `aggregate.py` | 按日/周/月聚合运动数据 |
| `llm.py` | DeepSeek 调用，支持多周期 Prompt |
| GPS 存储 | `gait_frames` 表增加 `lat`/`lng` 字段或在 `reports.summary_json` 中存储轨迹摘要 |

---

## 六、类型定义汇总

在现有 `types/index.ts` 基础上新增以下类型：

```typescript
// === 运动情况 ===
interface ActivitySummary {
  date: string
  steps: number
  activeMinutes: number
  distanceKm: number
}

interface ActivityHistory {
  days: Array<{ date: string; steps: number }>
}

// === 步态分析 ===
interface GaitSummary {
  date: string
  leftFoot: FootAnalysis
  rightFoot: FootAnalysis
  overallAssessment: string
}

interface FootAnalysis {
  pressures: readonly number[]         // 16 个平均压力值
  copPoints: readonly CopPoint[]       // COP 轨迹
  classification: GaitClass
  confidence: number
}

// === GPS ===
interface GpsRoute {
  date: string
  points: Array<{ timestamp: number; lat: number; lng: number }>
  totalDistanceKm: number
  durationMinutes: number
}

// === 报告（扩展） ===
type ReportPeriod = 'today' | 'week' | 'month'

interface ReportResponse {
  period: ReportPeriod
  dateRange: { start: string; end: string }
  reportText: string
  stepCount: number
  gaitSummary: string
  generatedAt: number
}

// === 设备管理 ===
interface SavedDeviceInfo {
  deviceId: string
  deviceName: string
  pairedAt: number
  lastConnectedAt: number
}

// === 平衡评估 ===
interface BalanceResult {
  score: number
  grade: 'excellent' | 'good' | 'fair' | 'needs_improvement'
  leftCopTrajectory: CopPoint[]
  rightCopTrajectory: CopPoint[]
  leftAvgPressures: readonly number[]
  rightAvgPressures: readonly number[]
  swayArea: number
  copStdDev: number
  timestamp: number
}
```

---

## 七、文件结构（目标态）

```
frontend/src/
├── main.tsx
├── App.tsx                          # 路由 + 响应式布局切换
├── index.css                        # 全局样式 + 响应式
│
├── types/
│   └── index.ts                     # 所有类型定义（扩展现有）
│
├── api/
│   └── client.ts                    # fetch 封装（新增 activity/gait/gps 接口）
│
├── hooks/
│   ├── useBleService.ts             # BLE 连接状态 + 设备管理 Hook
│   ├── useMediaQuery.ts             # 响应式断点检测
│   └── useBalanceAssessment.ts      # 平衡评估状态机 Hook
│
├── ble/
│   ├── bleService.ts                # 重构：新增扫描/保存设备/命令写入
│   ├── frameParser.ts               # 已有，无需改动
│   ├── mockData.ts                  # 已有，扩展平衡模式 mock
│   └── deviceStore.ts               # 设备信息的 localStorage 读写
│
├── viz/
│   ├── HeatmapCanvas.tsx            # 已有（热力图），API 兼容复用
│   ├── CopTrajectory.tsx            # 已有（COP 轨迹），API 兼容复用
│   ├── FootAnalysisCanvas.tsx       # 新增：静态热力图 + COP 散点叠加
│   ├── interpolation.ts             # 已有，无需改动
│   ├── cop.ts                       # 已有（COP 计算），扩展平衡评分函数
│   └── sensorLayout.ts             # 已有，无需改动
│
├── components/
│   ├── layout/
│   │   ├── PcSidebar.tsx            # PC 侧边导航
│   │   └── MobileTabBar.tsx         # 手机底部 Tab
│   ├── dashboard/
│   │   ├── MetricCard.tsx           # 指标卡片
│   │   ├── MiniBarChart.tsx         # 迷你柱状图
│   │   └── DeviceCard.tsx           # 设备卡片
│   ├── activity/
│   │   └── StepsBarChart.tsx        # 7 天柱状图
│   ├── gait/
│   │   └── GaitClassificationCard.tsx # 步态分类结果卡片
│   ├── gps/
│   │   └── MapContainer.tsx         # 地图容器（Leaflet/AMap 适配）
│   ├── report/
│   │   ├── ReportCard.tsx           # 已有
│   │   └── PeriodSelector.tsx       # 周期切换（今日/周/月）
│   ├── ble/
│   │   └── BleDevicePanel.tsx       # 设备扫描 + 已配对列表 + 连接管理
│   ├── balance/
│   │   ├── BalanceTimer.tsx         # 倒计时显示
│   │   ├── BalanceCopIndicator.tsx  # 重心位置指示器
│   │   ├── PostureTip.tsx           # 姿势提示文字
│   │   └── BalanceResultCard.tsx    # 评估结果展示
│   ├── common/
│   │   └── DatePicker.tsx           # 通用日期选择器
│   ├── BleConnectButton.tsx         # 保留兼容，逐步迁移至 BleDevicePanel
│   ├── GaitStatusBar.tsx            # 已有，保留
│   └── HistoryPicker.tsx            # 已有，可能被 DatePicker 替代
│
└── pages/
    ├── DashboardPage.tsx            # 新增
    ├── ActivityPage.tsx             # 新增
    ├── GaitPage.tsx                 # 新增
    ├── GpsPage.tsx                  # 新增
    ├── ReportPage.tsx               # 已有，扩展周期切换
    ├── RealtimePage.tsx             # 已有，整合 BleDevicePanel
    └── BalancePage.tsx              # 新增
```

---

## 八、实施路线图

### 阶段 1：基础设施（必须先做）

| 序号 | 任务 | 说明 |
|------|------|------|
| 1.1 | 响应式布局框架 | PC 侧边栏 + 手机 Tab，`useMediaQuery` Hook |
| 1.2 | 类型定义扩展 | `types/index.ts` 新增所有新接口 |
| 1.3 | API 层扩展 | `client.ts` 新增 activity/gait/gps/report(period) 接口 |
| 1.4 | 后端新 API 实现 | `activity/today`、`activity/history`、`gait/summary`、`gps/routes`（先用 mock 数据） |
| 1.5 | CSS 设计系统 | 东亚健康后台风格变量（颜色、间距、卡片阴影、字体层级） |

### 阶段 2：PC 远程监控页面（逐页实现）

| 序号 | 任务 | 依赖 |
|------|------|------|
| 2.1 | Dashboard 页 | 1.1, 1.2, 1.3 |
| 2.2 | Activity 页 + 柱状图 | 1.4 |
| 2.3 | Gait 分析页 + `FootAnalysisCanvas` | 1.4 |
| 2.4 | GPS 页 + Leaflet 地图 | 1.4 |
| 2.5 | Report 页扩展（today/week/month） | 1.4 |

### 阶段 3：手机近程功能

| 序号 | 任务 | 依赖 |
|------|------|------|
| 3.1 | BLE Service 重构（扫描/配対/写入命令） | — |
| 3.2 | `BleDevicePanel` 组件 | 3.1 |
| 3.3 | RealtimePage 整合 BleDevicePanel | 3.2 |
| 3.4 | 平衡评估页 + `useBalanceAssessment` | 3.1 |

### 阶段 4：打磨

| 序号 | 任务 |
|------|------|
| 4.1 | 高德地图适配（`VITE_AMAP_KEY` 环境变量） |
| 4.2 | PC/手机响应式细节调优 |
| 4.3 | 空状态、加载态、错误态全覆盖 |

---

## 九、当前已完成模块（可复用）

| 模块 | 位置 | 状态 |
|------|------|------|
| BLE 帧解析 | `frameParser.ts` | ✅ 可复用 |
| Mock 数据流 | `mockData.ts` | ✅ 可复用，需扩展平衡模式 |
| 热力图渲染 | `HeatmapCanvas.tsx` | ✅ 可复用 |
| COP 轨迹 | `CopTrajectory.tsx` | ✅ 可复用 |
| COP 计算 | `cop.ts` | ✅ 可复用，需新增平衡评分函数 |
| 插值与颜色映射 | `interpolation.ts` | ✅ 可复用 |
| 传感器布局 | `sensorLayout.ts` | ✅ 可复用 |
| 步态状态栏 | `GaitStatusBar.tsx` | ✅ 可复用 |
| 日报卡片 | `ReportCard.tsx` | ✅ 可复用 |
| BLE 连接基础 | `bleService.ts` | 🔧 需重构（加扫描/配对/写命令） |
| 报告页 | `ReportPage.tsx` | 🔧 需扩展周期切换 |
| 实时页 | `RealtimePage.tsx` | 🔧 需整合 BleDevicePanel |
| API 客户端 | `client.ts` | 🔧 需新增接口 |
| 类型定义 | `types/index.ts` | 🔧 需大幅扩展 |

---

## 十、待确认项

| 编号 | 内容 | 影响模块 |
|------|------|---------|
| TBD-BLE | BLE Write Characteristic UUID + 平衡评估命令格式 | `bleService.ts`、`BleDevicePanel`、`BalancePage` |
| TBD-GPS | GPS 坐标在 `gait_frames` 中的存储位置（独立字段 or JSON 内嵌） | 后端模型、前端 GPS 页 |
| TBD-MAP | 高德地图 JS API Key（需用户提供后填入 `.env`） | `MapContainer` 组件 |
| TBD-BAL | 平衡评估评分的具体算法（是 COP 椭圆面积还是标准差为主） | `cop.ts` 评分函数 |

> TBD-BLE 和 TBD-BAL 需与硬件组沟通后确定。
