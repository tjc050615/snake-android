# M1 验收结果（冻结）

版本：**v1.0-m1** ｜ 日期：2026-10-22 ｜ 对应 tag：`m1-done`

命令：`python -m pytest -q` → **106 passed**
GUI：Kivy 2.3.0 / Python 3.11.3 / OpenGL 4.6（NVIDIA RTX 3060 Laptop）

| # | 验收条件 | 结论 | 证据 |
|---|---|---|---|
| M1-1 | 世界整数格坐标，负坐标与跨 0 正常 | ✅ | `tests/test_world_coords.py`（8 条，含 `(-33,0)→(-2,0)`） |
| M1-2 | 单 chunk 32×32 空网格 + 食物 3~5，纯函数 | ✅ | `tests/test_chunk_pregen.py`（20 条） |
| M1-3 | 每 Tick 前进 1 格，默认 10 Tick/秒 | ✅ | `tests/test_tick.py`、`tests/test_game.py`；`docs/evidence/smoke-120tick.txt`（12s→117 tick） |
| M1-4 | 仅自撞死亡；吃食物长度 +1、`ate_food=True` | ✅ | `tests/test_snake.py`、`tests/test_game.py` |
| M1-5 | 死区：>10 不动；9 格推 1、8 格推 2 | ✅ | `tests/test_camera.py::test_push_offset_formula` 等 |
| M1-6 | 滞回：进入 10、退出 12，不抖动 | ✅ | `test_hysteresis_armed_then_holds_until_twelve`、`test_exit_*12`（12.0/11.999/12.001）；GUI：`docs/evidence/smoke-hyst.txt` |
| M1-7 | <3 格硬吸附，蛇头不出屏 | ✅ | `test_snap_inside_three_cells`、`test_snap_beats_slow_smoothing`；10x 跑 1137 tick `inside=True` |
| M1-8 | x/y 独立 | ✅ | `test_axes_are_independent` |
| M1-9 | `grid_size = max(16, round(32*density))` | ✅ | `tests/test_grid_scale.py`；多分辨率日志 48 / 34 / 22 / 16 |
| M1-10 | 整数缩放、Nearest，无半像素模糊 | ✅ | `docs/evidence/res-1920x1080.png` 等 4 张 |
| M1-11 | 插值：头 `body[1]→body[0]`、尾两分支、`ate_food` | ✅ | `tests/test_interp.py`（13 条）；`docs/evidence/interp_compare.png` |
| M1-12 | 方向键/WASD 转向，禁止 180° | ✅ | `test_reverse_direction_rejected`、`test_reverse_of_pending_rejected`、`test_quick_two_key_combo_allowed` |
| M1-13 | 重开：世界/蛇/相机全重置 | ✅ | `test_reset_restores_initial_state`、`test_restart_uses_same_seed_world` |
| M1-14 | 仅横屏布局，无竖屏分支 | ✅（桌面侧） | 4 个分辨率均横屏；安卓旋转锁定留 M5 真机复验 |

## 多分辨率实测

| 分辨率 | density | grid_size | 视口格数 | too_small | 日志 |
|---|---|---|---|---|---|
| 1920×1080 | 1.5 | 48 | 41×23 | False | `res-1920x1080.txt` |
| 1280×720 | 1.5 | 34 | 39×23 | False | `res-1280x720.txt` |
| 800×480 | 1.5 | 22 | 37×23 | False | `res-800x480.txt` |
| 320×240 | 1.5 | 16 | 21×16 | **True** | `res-320x240.txt`（`Logger.warning` 输出，回退 grid_size=16） |

> 800×480 **不触发** too_small：公式值 48 会只剩 16×10 格，`fit_grid_size` 逐档降到 22 后满足 21 格。
> 320×240 触发：降到 16 仍只有 20×15 格 → 抛 `ValueError` → 画布回退 16 并 `Logger.warning`，日志可见。

## 遗留 KI（带入 M2/M4/M5）

| ID | 级别 | 内容 | 归属 |
|---|---|---|---|
| KI-003 | P3 | 帧率未测（无 FPS 采集） | M5 |
| KI-004 | P2 | TickClock 追车上限；PAUSED 需 `clock.reset()` | M4 |
| KI-005 | P3 | resize 后相机世界位置漂移 | M4 |
| KI-006 | P2 | 每帧全量 `rebuild()`，需局部更新 | M5 |
