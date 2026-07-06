# Active Context（当前焦点）

> 更新最频繁的文件。每次里程碑或换方向时刷新。
> 最近更新：2026-07-06

## 当前焦点

**后端从测试桩升级为完整实现**——按 `.cursor/tasks/2026-07-06-backend-implementation.md` 实施 config → database → ingest → feature → llm → report 全链路。

## 近期变更

- 2026-07-06 完成数字大脑初始化：旧 `doc/`、`TODO/`、`ignored/TALK_WITH_AI.md` 归档至 `.cursor/bakup/`，知识沉淀至 `.cursor/memories/`
- 2026-06~07 前端多页面骨架完成：7 个页面（Dashboard/Activity/Gait/Gps/Report/Realtime/Balance）+ BLE 模块 + viz 模块 + hooks + 响应式布局（PcSidebar/MobileTabBar）
- 后端 `main.py` 仍为测试桩，mock 全部 API 端点（activity/gait/gps/report/ingest）

## 下一步

- [ ] 按 Task Plan 实施后端完整实现（8 步顺序见 task 文档）
- [ ] 向硬件组确认 TBD-1（FSR 物理坐标映射）和 TBD-5（BLE UUID 最终值）
- [ ] 向硬件组确认 TBD-BLE（平衡评估 Write Characteristic + 命令格式）
- [ ] 真机 BLE 测试需 HTTPS 环境（当前 http IP 下不可用）

## 进行中的任务 Plan

- [`.cursor/tasks/2026-07-06-backend-implementation.md`](../tasks/2026-07-06-backend-implementation.md)

## 待决问题 / 阻塞

| 编号 | 内容 | 影响 | 等待 |
|------|------|------|------|
| TBD-1 | FSR 传感器物理坐标映射 | 热力图、COP 计算 | 硬件组/标定 |
| TBD-2 | COP 坐标轴方向及左右脚镜像 | 前端轨迹显示 | 算法确认 |
| TBD-3 | ADC → 压力标定曲线 | 物理量展示 | fsr_calibrate 拟合导出 |
| TBD-4 | TinyML 模型 | 固件推理 | 硬件组采集训练 |
| TBD-5 | BLE GATT UUID 最终值 | 前端 BLE 连接 | 固件确认 |
| TBD-BLE | 平衡评估 BLE 命令格式 | `/balance` 页真机联调 | 硬件组 |
| HTTPS | 真机 Web Bluetooth | `/realtime` 近程演示 | 域名/证书配置 |
