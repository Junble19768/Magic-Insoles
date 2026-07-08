# usb_daq_v20

Python 版 USB-DAQ V20 采集库，移植自 `usb-daq-v20.cpp` / `usb-daq-v20.h`。

与原版 C 库的主要区别：

- 所有操作以 **CardID**（设备唯一 ID）索引，不再使用 `dev` 序号
- 失败时抛出结构化异常 **`DaqError`**，包含阶段、libusb 错误码与排查提示
- 支持枚举多张采集卡、probe 读取 CardID

**硬件标识：** VID=`0x7812`，PID=`0x55A9`

---

## 安装

在项目根目录（`win-datacap`）下：

```bash
pip install -r requirements.txt
```

依赖：

| 包 | 用途 |
|---|---|
| `pyusb` | USB 设备访问 |
| `libusb-package` | 自带 libusb-1.0 动态库（Windows/macOS 推荐；Linux 也可配合系统 libusb） |

### 各平台连接说明

库在打开设备时会自动尝试 `detach_kernel_driver`（Linux）并 `claim_interface(0)`。各平台额外配置如下。

#### Windows

首次使用需用 [Zadig](https://zadig.akeo.ie/) 将采集卡驱动替换为 **WinUSB**。每张卡单独配置。

1. 插入采集卡，打开 Zadig → Options → 勾选 **List All Devices**
2. 在下拉列表中选择 `USB-DAQ` 或 VID=`7812` / PID=`55A9` 对应项
3. 右侧驱动选 **WinUSB**，点击 **Replace Driver**
4. 验证：`python -m usb_daq_v20` 能列出 CardID

若出现 `CLAIM_FAILED` / `ACCESS (-3)`，优先检查驱动是否已替换、是否有其他程序占用设备。

#### Linux

**1. 确认系统识别设备**

```bash
lsusb | grep 7812
# 期望看到类似: Bus 001 Device 00x: ID 7812:55a9 ...
```

若无输出，检查 USB 线、Hub 供电，或尝试 `dmesg | tail` 查看内核日志。

**2. 安装 libusb（若 pip 后端加载失败）**

```bash
# Debian / Ubuntu
sudo apt install libusb-1.0-0 libusb-1.0-0-dev

# Fedora / RHEL
sudo dnf install libusb libusb-devel

# Arch
sudo pacman -S libusb
```

**3. 配置 udev 规则（免 root 访问）**

创建 `/etc/udev/rules.d/99-usb-daq.rules`：

```
SUBSYSTEM=="usb", ATTR{idVendor}=="7812", ATTR{idProduct}=="55a9", MODE="0666", GROUP="plugdev"
```

然后重载规则并重新插拔设备：

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
# 或重新插拔 USB
```

将当前用户加入 `plugdev` 组（若发行版使用该组）：

```bash
sudo usermod -aG plugdev $USER
# 注销后重新登录生效
```

**4. 内核驱动占用**

本库在 open 时会尝试 detach 接口 0 的内核驱动。若仍报 `BUSY (-6)`，可手动解绑后再试：

```bash
# 查看是否被内核驱动绑定（驱动名因内核而异，常见 usbfs/hid 等）
lsusb -t
# 若存在 usbhid 等驱动占用，可临时解绑（需 root，路径以 /sys 实际为准）：
# echo '7812 55a9' | sudo tee /sys/bus/usb/drivers/usb/unbind
```

**5. 验证**

```bash
python -m usb_daq_v20
```

#### macOS

**1. 安装依赖**

```bash
pip install -r requirements.txt
# 若 libusb 后端加载失败，可通过 Homebrew 安装系统 libusb：
brew install libusb
```

**2. 确认设备可见**

```bash
system_profiler SPUSBDataType | grep -A5 -i "7812\|55a9"
# 或
ioreg -p IOUSB -l | grep -E "7812|55a9"
```

**3. 权限说明**

macOS 一般**不需要**像 Windows 那样用 Zadig 换驱动。普通用户通常可直接通过 libusb 访问；库会自动 `claim_interface(0)`。

- 首次连接若弹出「是否允许访问 USB 设备」类提示，请选择允许
- 若报 `ACCESS (-3)` 或 `CLAIM_FAILED`：
  - 确认无其他进程占用（如另一个 `server.py` 实例）
  - 尝试换 USB 口（避免仅充电线/劣质 Hub）
  - 在「系统设置 → 隐私与安全性」中检查是否有 USB/辅助功能相关限制（因 macOS 版本而异）

**4. Apple Silicon (M 系列)**

`pyusb` + `libusb-package` 支持 arm64。若 `import usb_daq_v20` 报 libusb 加载失败，优先：

```bash
brew install libusb
pip install --force-reinstall libusb-package
```

**5. 验证**

```bash
python -m usb_daq_v20
```

#### 跨平台常见问题

| 现象 | Windows | Linux | macOS |
|------|---------|-------|-------|
| 找不到设备 | Zadig 未配置 | udev 未配置 / 未识别 | 线缆/Hub 问题 |
| `ACCESS (-3)` | 驱动不对 | 无 udev 权限 | 权限/占用 |
| `BUSY (-6)` | 其他程序占用 | 内核驱动未 detach | 其他程序占用 |
| 多卡只识别一张 | 每张分别 Zadig | 检查 udev 规则 | 检查 Hub 供电 |

### Conda 环境（可选）

```bash
conda create -n datacap python=3.10 -y
conda activate datacap
conda install -c conda-forge pyusb libusb -y
pip install libusb-package
```

---

## 快速开始

### 命令行：列出已连接设备

```bash
# 推荐
python -m usb_daq_v20

# 或运行示例脚本
python usb_daq_v20/example/list_card_ids.py
```

### 最小代码示例

```python
import usb_daq_v20
from usb_daq_v20 import DaqError

try:
    devices = usb_daq_v20.open_all()
    card_id = devices[0].card_id

    usb_daq_v20.do_set(card_id, chan=0, state=0)
    voltage = usb_daq_v20.ad_single(card_id, chan=0)
    print(f"CardID=0x{card_id:08X}, AD[0]={voltage:.4f} V")

finally:
    usb_daq_v20.close_all()
```

---

## 典型工作流程

```
probe / list_connected_devices   # 无需长期占用，查看 CardID
        ↓
open_all()                       # 打开并 claim 所有卡，建立 CardID 注册表
        ↓
ad_single(card_id, ...) 等       # 按 CardID 操作
        ↓
close_all()                      # 释放所有设备
```

多卡场景：先用 `list_connected_devices()` 确认各卡 CardID，再在 `open_all()` 后通过 `card_id` 指定目标卡。

指定 CardID 的环境变量（`server.py` 中使用）：

```bash
set DAQ_CARD_ID=0x00BC614E
python server.py
```

---

## 数据类型

### `DeviceInfo`

| 字段 | 类型 | 说明 |
|------|------|------|
| `card_id` | `int` | 设备 Card ID（32 位，可用 `0x........` 显示） |
| `bus` | `int` | USB 总线号 |
| `address` | `int` | USB 设备地址 |

---

## API 参考

### 设备发现（无需 `open_all`）

| 函数 | 返回 | 说明 |
|------|------|------|
| `list_connected_devices()` | `list[DeviceInfo]` | 短暂打开每张卡读取 CardID 后释放 |
| `format_devices_table(devices)` | `str` | 格式化为表格字符串 |
| `print_connected_devices()` | `list[DeviceInfo]` | 打印表格并返回列表 |
| `list_devices(*, probe=False)` | `list[DeviceInfo]` | `probe=True` 同 `list_connected_devices`；否则读已打开 registry |
| `list_card_ids(*, probe=False)` | `list[int]` | 仅返回 CardID 列表 |

### 生命周期

| 函数 | 返回 | 说明 |
|------|------|------|
| `open_all()` | `list[DeviceInfo]` | 打开所有采集卡（对齐 C 库 `OpenUsbV20_V2`） |
| `close_all()` | `None` | 关闭并释放所有设备 |
| `get_device_count()` | `int` | 当前已打开的设备数量 |
| `get_card_id(card_id)` | `int` | 验证 CardID 是否存在，返回 CardID |
| `reset_device(card_id)` | `None` | USB reset 指定卡，之后需重新 `open_all()` |

### AD 采集

| 函数 | 返回 | 说明 |
|------|------|------|
| `ad_single(card_id, chan)` | `float` | 单通道单次 AD，电压 V（0~3.3V 量程） |
| `ad_continu(card_id, chan, num_sample, frequency)` | `list[float]` | 单通道连续采样 |
| `mad_continu(card_id, chan_first, chan_last, num_sample, frequency)` | `list[float]` | 多通道连续采样 |

- `chan`：AD 通道 0~15
- `num_sample`：采样点数（自动对齐到 32 的倍数）
- `frequency`：采样频率 Hz

### DA 输出

| 函数 | 说明 |
|------|------|
| `da_single_out(card_id, chan, value)` | 单值输出；`chan` 为 1 或 2；`value` 12 位 DAC 码 |
| `da_data_send(card_id, chan, num, databuf)` | 发送扫描波形数据（最多 512 点） |
| `da_scan_out(card_id, chan, freq, scan_num)` | 启动 DA 扫描输出 |

### PWM

| 函数 | 返回 | 说明 |
|------|------|------|
| `pwm_out_set(card_id, chan, freq, duty_cycle)` | `None` | PWM 输出；`chan` 1/2；占空比 0~100（%） |
| `pwm_in_set(card_id, mod)` | `None` | PWM 输入模式设置 |
| `pwm_in_read(card_id)` | `(freq, duty)` | 读取 PWM 输入频率与占空比 |

### 计数器

| 函数 | 返回 | 说明 |
|------|------|------|
| `count_set(card_id, mod)` | `None` | 计数器模式设置 |
| `count_read(card_id)` | `int` | 读取计数值 |

### 数字 IO

| 函数 | 返回 | 说明 |
|------|------|------|
| `do_set(card_id, chan, state)` | `None` | 开关量输出；`state` 0/1 |
| `di_read(card_id)` | `int` | 开关量输入，返回低 8 位 |

---

## 错误处理

所有 API 失败时抛出 **`DaqError`**（不再返回 C 风格的 `0/-1`）。

```python
from usb_daq_v20 import DaqError, ErrorCode

try:
    usb_daq_v20.open_all()
except DaqError as e:
    print(e.code)        # ErrorCode 枚举
    print(e.stage)       # 失败阶段：open / claim / bulk_read ...
    print(e.usb_errno)   # libusb 错误码，如 -6 (BUSY)
    print(e.bus, e.address)
```

### 常见 `ErrorCode`

| 代码 | 含义 | 常见原因 |
|------|------|----------|
| `NO_DAQ_DEVICE` | 未找到设备 | 未连接、VID/PID 不符 |
| `CLAIM_FAILED` | claim 接口失败 | 驱动未配置、设备被占用 |
| `DUPLICATE_CARD_ID` | CardID 重复 | 两张卡 ID 相同（理论上不应发生） |
| `NOT_OPENED` | 未 open 就调用 | 先 `open_all()` |
| `DEVICE_NOT_FOUND` | CardID 不在 registry | ID 写错或未 open |
| `IO_SHORT_READ/WRITE` | 传输字节数不符 | 通信异常 |
| `USB_IO` | USB 底层错误 | 线缆/Hub/掉线 |

---

## 示例脚本

位于 `usb_daq_v20/example/`，请在项目根目录运行：

| 脚本 | 说明 |
|------|------|
| [example/list_card_ids.py](example/list_card_ids.py) | 列出所有已连接卡的 CardID |
| [example/ad_single_read.py](example/ad_single_read.py) | 打开首张卡，循环读取 AD 通道 |
| [example/open_by_card_id.py](example/open_by_card_id.py) | probe 后按 CardID 打开并操作 |
| [example/fsr_matrix_scan.py](example/fsr_matrix_scan.py) | FSR 足底 32 点矩阵扫描（同 server.py 逻辑） |

```bash
cd win-datacap
python usb_daq_v20/example/ad_single_read.py
```

---

## 与 C 库 API 对照

| C 函数 | Python 函数 | 索引参数 |
|--------|-------------|----------|
| `OpenUsbV20_V2` | `open_all()` | — |
| `CloseUsbV20` | `close_all()` | — |
| `GetDeviceCountV20` | `get_device_count()` | — |
| `GetCardIdV20` | `get_card_id(card_id)` | CardID |
| `Reset_Usb_DeviceV20` | `reset_device(card_id)` | CardID |
| `ADSingleV20` | `ad_single(card_id, chan)` | CardID |
| `ADContinuV20` | `ad_continu(...)` | CardID |
| `MADContinuV20` | `mad_continu(...)` | CardID |
| `DASingleOutV20` | `da_single_out(...)` | CardID |
| `DADataSendV20` | `da_data_send(...)` | CardID |
| `DAScanOutV20` | `da_scan_out(...)` | CardID |
| `PWMOutSetV20` | `pwm_out_set(...)` | CardID |
| `PWMInSetV20` / `PWMInReadV20` | `pwm_in_set` / `pwm_in_read` | CardID |
| `CountSetV20` / `CountReadV20` | `count_set` / `count_read` | CardID |
| `DoSetV20` | `do_set(...)` | CardID |
| `DiReadV20` | `di_read(card_id)` | CardID |

---

## 模块结构

```
usb_daq_v20/
├── __init__.py      # 公共 API
├── __main__.py      # python -m usb_daq_v20
├── constants.py     # VID/PID、端点、超时
├── device.py        # DeviceManager、CardID 注册表
├── protocol.py      # USB bulk 协议实现
├── errors.py        # DaqError、ErrorCode
├── list_cards.py    # 设备枚举与表格输出
├── _card_id.py      # CardID 读取解析
├── example/         # 示例脚本
└── README.md        # 本文件
```

---

## 相关项目脚本

| 脚本 | 说明 |
|------|------|
| [server.py](../server.py) | FSR 数据采集 TCP 服务，使用本库 |
| [fsr_calibrate.py](../fsr_calibrate.py) | FSR 标定客户端 |
