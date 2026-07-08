# Active Context（当前焦点）

> 更新最频繁的文件。每次里程碑或换方向时刷新。
> 最近更新：2026-07-09

## 当前焦点

**生产后端 `backend_prod/` 为唯一权威实现**——ECS 已部署；`backend/` 测试桩已弃用。后续：设备 TCP 联调、DeepSeek 日报配置、HTTPS/BLE。

## 近期变更

- 2026-07-09 **fsr_calibrate 左脚热力图坐标**：修复「字对图错」——图像须 **先 transpose 再 flip(axis=0)**，标签 `(x_max-cx, cy)`；勿先 flip 再 transpose。见 ADR-0004、`fsr_calibrate/boundary.py` + `heatmap.py`
- 2026-07-09 **win-datacap 迁入 `tools/`**：`win-datacap/` → `tools/win-datacap/`（`git mv` 保留历史，54 个已跟踪文件 + `best_rx.ipynb`）；新增 `tools/win-datacap/docs/CALIBRATION_PIPELINE.md` 串联「采集→标定→拟合→result.yml→Rx选型」全流程。见 `.cursor/tasks/2026-07-09-reorganize-win-datacap.md`
- 2026-07-09 **insoles-boundary 同步修正版 pipeline**：从 `ignored/insoles-boundary` 移植 OBB CW90 代码；修正 masks 重跑后 `render_payload.json` 画布 **132×324**（原 132×327）；region 1/2 几何独立。见 `tools/insoles-boundary/docs/tasks/2026-07-09-mask-fix-rerun.md`
- 2026-07-09 **鞋垫边界拟合工具留存**：`ignored/insoles-boundary/`（独立 git、原不被父仓库追踪）的代码/可复现数据/处理文档整理到 `tools/insoles-boundary/` 并入 git；原始大文件保留在 `ignored/`。见 `.cursor/tasks/2026-07-09-preserve-insoles-boundary.md`
- 2026-07-06 **弃用 `backend/` 测试桩**，生产与本地均使用 `backend_prod/`（ADR-0003）
- 2026-07-06 ECS 首次部署：`deploy/deploy.ps1` + `server-init.sh`；Nginx 路径 `/` `/insoles/` `/api/` `/health`
- 2026-07-06 完成数字大脑初始化：旧 `doc/`、`TODO/` 归档至 `.cursor/bakup/`
- 2026-06~07 前端 7 页面 + BLE/viz 骨架完成

## 下一步

- [ ] 阿里云安全组放行 TCP 80（外网访问）；设备接入时放行 TCP 9000
- [ ] 服务器 `backend_prod/.env` 配置 `DEEPSEEK_API_KEY`（日报生成）
- [ ] 向硬件组确认 TBD-1（FSR 坐标）、TBD-5（BLE UUID）、TBD-BLE（平衡评估命令）
- [ ] 真机 BLE 需 HTTPS（当前 http IP 不可用）

## 进行中的任务 Plan

- [`.cursor/tasks/2026-07-06-backend-implementation.md`](../tasks/2026-07-06-backend-implementation.md)（实施主体已迁至 `backend_prod/`，桩阶段结束）

## 部署速查

```powershell
.\deploy\deploy.ps1              # 全量
.\deploy\deploy.ps1 -BackendOnly # 仅后端
.\deploy\deploy.ps1 -FrontendOnly
```

| 环境 | 后端目录 | ECS 路径 |
|------|----------|----------|
| 本地 | `backend_prod/` | — |
| 生产 | `backend_prod/` | `/var/www/magic-insoles/backend_prod/` |

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
| SG-80 | 安全组 TCP 80 | 公网 HTTP 访问 | 阿里云控制台 |
