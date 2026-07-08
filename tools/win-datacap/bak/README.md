# bak — 历史代码归档

本目录保存 **win-datacap 项目的旧版 C/C++ 实现** 及相关脚本，供参考与对照。当前仓库的正式实现已迁移到根目录的 Python 代码（`server.py`、`usb_daq_v20/` 等），**日常开发请使用根目录版本**。

---

## 目录说明

```
bak/
├── server.cpp          # C++ FSR 数据采集 TCP 服务（Asio）
├── usb-daq-v20.cpp     # USB-DAQ V20 原生 C 库实现
├── usb-daq-v20.h       # 上述库头文件
├── CMakeLists.txt      # MinGW 构建配置
├── client.py           # PyQt5 足底热力图客户端（连接 server TCP）
├── my_aubo_control.py  # Aubo 机械臂 + ROS 相关控制脚本（独立实验）
├── .clang-format       # C++ 代码风格配置
├── libusb-1.0.dll      # 历史运行时 DLL 残留（完整 libusb 目录已删除）
└── bak/                # 更早期的 ROS / 双足采集示例
    ├── get_two_plantar.cpp
    ├── get_two_plantar_socket.cpp
    ├── get_tactile_sensor.cpp
    ├── usb_daq_test.c
    ├── plantar_sensor_client.py
    ├── twoPlotNew.py
    ├── two_plot_tactile.py
    ├── plot_tactile.py
    └── plot_curve.py
```

### 核心 C++ 组件

| 文件 | 作用 |
|------|------|
| `usb-daq-v20.cpp` / `.h` | 通过 libusb bulk 传输访问 USB-DAQ（VID=`0x7812`, PID=`0x55A9`），提供 AD/DA/PWM/数字 IO 等 API，以 **dev 序号** 索引设备 |
| `server.cpp` | 扫描 FSR 矩阵 32 路电压，经 **Asio TCP** 监听 `127.0.0.1:6543`，帧格式与现版 `server.py` 相同（320 字节 / 40 double） |
| `CMakeLists.txt` | 编译 `server.exe`，链接 libusb，拷贝运行时 DLL |

### Python 脚本

| 文件 | 作用 |
|------|------|
| `client.py` | 连接 `server.cpp` / `server.py` 的 TCP 流，左右脚各 16 点热力图可视化 |
| `my_aubo_control.py` | 机械臂遥操作、ROS2 节点等（与足底采集无直接依赖） |

### `bak/bak/` 子目录

更早期的 **ROS / 双卡双足** 采集与绘图示例，依赖 `OpenUsbV20_V2` 同时操作两张采集卡，部分通过 ROS topic 或 socket 发布数据。仅作历史参考。

---

## 第三方依赖（已自仓库移除）

原先本目录内 vendored 两份第三方库，用于 **C++ 本地编译**：

| 目录 | 来源 | 版本（归档时） | 用途 |
|------|------|----------------|------|
| ~~`asio/`~~ | [Asio C++ Library](https://think-async.com/Asio/) | 1.36.0（2025-08-16） | `server.cpp` 的 TCP 异步网络（header-only，`#include <asio.hpp>`） |
| ~~`libusb/`~~ | [libusb](https://libusb.info/) | 预编译 Windows 包 | `usb-daq-v20.cpp` 的 USB bulk 访问（`include/` + `lib/`） |

> **说明：** 上述 `asio/`、`libusb/` 文件夹已从本仓库删除，以减小体积。它们均为上游开源库的完整/预编译拷贝，**并非本项目自有代码**。

### 删除后的编译影响

**当前 `bak/` 目录已无法直接编译出 `server.exe`。**

`CMakeLists.txt` 仍引用以下路径，缺失后将报错：

```cmake
include_directories(libusb/include)
include_directories(asio/include)
link_directories(libusb/lib)
# POST_BUILD 复制 libusb-1.0.dll
```

若需重新编译 C++ 版，请自行恢复依赖：

1. **Asio** — 从 [think-async.com/Asio/](https://think-async.com/Asio/) 下载源码，解压到 `bak/asio/`，保证 `bak/asio/include/asio.hpp` 存在。

2. **libusb** — 从 [libusb.info](https://libusb.info/) 获取 Windows 预编译包或自行编译，恢复为：
   ```
   bak/libusb/include/libusb.h
   bak/libusb/lib/libusb-1.0.dll
   bak/libusb/lib/libusb-1.0.dll.a   # MinGW import lib
   bak/libusb/lib/libusb-1.0.a       # 静态库（可选）
   ```

3. 构建（MinGW 示例）：
   ```bash
   cd bak
   mkdir build && cd build
   cmake .. -G "MinGW Makefiles"
   cmake --build .
   ```

4. Windows 上仍需为 USB-DAQ 配置 **WinUSB** 驱动（Zadig），与 Python 版相同。

### 推荐替代

| 旧版（bak） | 现版（仓库根目录） |
|-------------|-------------------|
| `usb-daq-v20.cpp` | [`usb_daq_v20/`](../usb_daq_v20/) Python 库（CardID 索引、`DaqError`） |
| `server.cpp` | [`server.py`](../server.py) |
| `client.py` | 仍可用，连接 `server.py` |
| vendored libusb | `pip install pyusb libusb-package` |
| vendored Asio | Python 标准库 `socket`（`server.py`） |

---

## 与现版的关系

```
bak/server.cpp  ──移植──►  server.py
bak/usb-daq-v20.* ──重写──►  usb_daq_v20/
bak/client.py   ──仍兼容──►  server.py（TCP 协议未变）
```

现版 README：[../README.md](../README.md)  
USB 库文档：[../usb_daq_v20/README.md](../usb_daq_v20/README.md)
