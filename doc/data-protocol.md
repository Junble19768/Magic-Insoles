# 数据协议定义

> 定义 STM32 ↔ 手机 Web ↔ 后端 之间的数据格式
> 协议字段以实际开发为准，此处为设计基准版本

---

## 一、BLE 协议

### 1.1 GATT 服务定义

| 项目 | 值 |
|------|-----|
| Service UUID | `0000FFF0-0000-1000-8000-00805F9B34FB` |
| Characteristic UUID | `0000FFF1-0000-1000-8000-00805F9B34FB` |
| Characteristic 属性 | Notify |
| 推送周期 | 20ms（50Hz） |

> UUID 可在固件开发时自定义，前端同步更新即可。

### 1.2 BLE 帧格式（二进制，小端序）

```
Offset  Size   Type    字段名          说明
──────  ─────  ──────  ──────────────  ──────────────────────────────
0       1      uint8   frame_type      帧类型，0x01=压力帧
1       2      uint16  seq             帧序号（0-65535 循环）
3       32     uint8   pressure[32]    32路压力值（0-255，归一化）
                                       index 0-15: 左脚
                                       index 16-31: 右脚
                                       物理坐标映射见 TBD-1
35      1      uint8   gait_state      步态状态 0=站立 1=行走 2=跑步
36      1      uint8   ml_class        TinyML分类 0=正常 1=内八 2=外八
37      1      uint8   ml_conf         置信度 0-100
38      2      uint16  step_count      累计步数（低字节在前）
40      1      uint8   battery         电量 0-100%

总计：41 字节
```

**压力值归一化说明：**
- 0 = 无压力
- 255 = 最大量程压力
- 实际物理量（kPa）换算待标定曲线确定（TBD-3）

**坐标映射说明（TBD-1）：**
- 当前左右脚为镜像对称排列
- 具体 index → 物理位置（前掌/后跟/内外侧）的映射表待后续确认

---

## 二、HTTP 接口

### 上行：STM32 → 后端（经 LTE，设备直传）

### 下行：手机 Web → 后端（远程查看模式，HTTPS GET）

**Base URL：** `https://<your-server>/api`  
**鉴权：** Header `X-API-Key: <固定密钥>`（单设备，无需登录）

### 2.1 STM32 上传原始数据帧（LTE 直传，非手机中转）

```
POST /api/ingest
Content-Type: application/json

Request Body:
{
  "frames": [
    {
      "timestamp": 1751000000.123,      // Unix 时间戳（秒）
      "pressures": [0, 0, ..., 255],    // 32个整数，0-255
      "gait_state": 1,                  // 0=站立 1=行走 2=跑步
      "ml_class": 0,                    // 0=正常 1=内八 2=外八
      "ml_conf": 0.92,                  // 置信度
      "step_count": 134                 // 当前累计步数
    },
    ...
  ]
}

Response 200:
{
  "received": 10,   // 成功接收帧数
  "status": "ok"
}
```

### 2.2 获取今日 AI 报告

```
GET /api/report/today

Response 200:
{
  "date": "2026-06-29",
  "report_text": "今天宝贝运动了 45 分钟...",
  "step_count": 3200,
  "gait_summary": "步态整体正常",
  "generated_at": 1751080000
}

Response 404（当日尚无报告）:
{
  "status": "not_ready",
  "message": "今日报告尚未生成"
}
```

### 2.3 获取历史报告列表

```
GET /api/report/history?days=7

Response 200:
{
  "reports": [
    {
      "date": "2026-06-29",
      "step_count": 3200,
      "gait_summary": "步态整体正常",
      "report_text": "..."
    },
    ...
  ]
}
```

### 2.4 手动触发报告生成（调试用）

```
POST /api/report/generate

Response 200:
{
  "status": "ok",
  "report_text": "..."
}
```

---

## 三、数据量估算

| 场景 | 数据量 |
|------|--------|
| BLE 帧大小 | 41 字节 / 帧 |
| BLE 推送频率（手机近程可视化） | 50Hz → ~2KB/s（仅手机本地消费，不上传） |
| LTE 上传频率（STM32 直传后端） | 每 N 步一批（约 10-20 帧），~820 字节/批 |
| 每日存储量（活动 1 小时） | ~7.4 MB 原始帧（可接受） |

---

## 四、前端 BLE 解析示例（JavaScript）

```javascript
// 解析 BLE 二进制帧
function parseInsoleFrame(dataView) {
  const frameType = dataView.getUint8(0);
  if (frameType !== 0x01) return null;

  const frame = {
    seq:        dataView.getUint16(1, true),       // 小端
    pressures:  new Array(32).fill(0).map((_, i) =>
                  dataView.getUint8(3 + i)),
    gaitState:  dataView.getUint8(35),
    mlClass:    dataView.getUint8(36),
    mlConf:     dataView.getUint8(37) / 100,       // 0.0-1.0
    stepCount:  dataView.getUint16(38, true),
    battery:    dataView.getUint8(40),
  };

  // 分离左右脚
  frame.leftFoot  = frame.pressures.slice(0, 16);
  frame.rightFoot = frame.pressures.slice(16, 32);

  return frame;
}
```

---

## 五、待确认项

| 编号 | 内容 | 影响 |
|------|------|------|
| TBD-1 | 传感器物理坐标映射（index → 前掌/后跟/内外侧） | 热力图插值方向、COP 计算坐标 |
| TBD-2 | COP 坐标轴方向（X=内→外，Y=跟→趾），左右脚镜像规则 | 前端 COP 轨迹显示方向 |
| TBD-3 | 压力归一化范围（最大量程对应 kPa 值） | 报告中的物理量描述 |
| TBD-4 | BLE UUID 最终值（固件开发确认后同步前端） | 前端 BLE 连接代码 |
