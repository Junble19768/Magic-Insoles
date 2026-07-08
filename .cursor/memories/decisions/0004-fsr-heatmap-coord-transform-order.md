# ADR-0004: fsr_calibrate 双脚热力图坐标变换顺序

- **状态**：已采纳
- **日期**：2026-07-09

## 背景

`tools/win-datacap/fsr_calibrate/heatmap.py` 左脚可视化多次出现「文字标注位置正确、热力图 blob 错位」。
根因不是镜像公式本身，而是 **NumPy 图像变换与 PyQtGraph 标签坐标使用了不同顺序**。

`insoles-boundary` 的 `render_sensor_field` 输出 `field[row, col]`（左上角原点，形状 `(H, W)`）。
质心 `region_label_centroids` 返回 `(cx, cy)`，与 payload 画布列/行一致。

右脚显示已验证正确；左脚应在同一显示基准上沿 X 镜像。

## 决策

双脚热力图统一约定：

| 脚 | 图像变换（`build_boundary_foot_heatmap`） | 标签 plot 坐标 |
|----|-------------------------------------------|----------------|
| 右脚 | `transpose`（`field.T`） | `(cx, cy)` |
| 左脚 | `transpose` → `flip(axis=0)` | `(x_max - cx, cy)` |

**强制顺序**：必须先 `transpose`，再 `flip_horizontal`（`np.flip(field, axis=0)`）。
转置后 plot 的 x 对应数组第 0 轴（行索引），左脚镜像必须作用在这一轴上。

实现位置：
- `fsr_calibrate/boundary.py` — `build_boundary_foot_heatmap`
- `fsr_calibrate/heatmap.py` — `FootPressurePanel._update_labels`

## 备选方案

- **先 flip 再 transpose**：标签若按「先转置再镜像」手算仍可能对，但图像 blob 与文字错位 — 本次 bug 根因，禁止。
- **左脚单独换一套 cy/cx 交换公式**：与右脚基准不一致，难维护 — 未选。
- **在 GUI 层用 `ImageItem` 变换代替数组变换**：隐式顺序更难排查 — 未选。

## 影响

- **正面**：左右脚图像与标签对齐；与 `insoles-boundary/src/insoles/coord_transform.py` 中「transpose + horizontal_flip」语义一致。
- **负面 / 代价**：修改 `flip`/`transpose` 参数时必须同时检查 `heatmap.py` 标签公式，不能只看一侧。
- **后续**：前端 Three.js 热力图、COP 左右脚镜像应复用同一约定（见 TBD-2）。

## 回归检查（改坐标相关代码时必做）

对单传感器脉冲 `values[i]=1`，`blur_sigma=0`：

```python
right = build_boundary_foot_heatmap(vals, transpose=True)
left  = build_boundary_foot_heatmap(vals, transpose=True, flip_horizontal=True)
# 右脚: right[int(cx), int(cy)] > 0.5
# 左脚: left[int(x_max-cx), int(cy)] > 0.5
```

若标签对、图像错，优先怀疑 **变换顺序**，而非镜像方向。
