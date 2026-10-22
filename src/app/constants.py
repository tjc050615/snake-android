"""项目常量（唯一来源：docs/DECISIONS.md）。

本模块不得 import kivy —— core / ai 层必须能在无 GUI 环境下被 pytest 导入。
"""

# --- 世界 ---
CHUNK_SIZE = 32                  # D-004
CHUNK_PRELOAD_RINGS = 2          # D-005（M2 生效）
CHUNK_UNLOAD_RINGS = 3           # D-005（M2 生效）
SPAWN_CELL = (0, 0)              # D-006
SPAWN_DIR = (1, 0)               # D-006
SPAWN_LEN = 3                    # D-006

# --- 相机（M1/R3 使用）---
CAMERA_DEADZONE_CELLS = 10       # D-008
CAMERA_HYST_CELLS = 2            # D-009
CAMERA_SNAP_CELLS = 3            # D-010
CAMERA_SMOOTH_K = 8.0            # D-045（A 区已锁定；改值需重跑 R3 平滑测试）

# --- 输入 ---
JOYSTICK_DEADZONE = 0.15         # D-012

# --- 像素缩放 ---
GRID_SIZE_MIN = 16               # D-013
GRID_SIZE_BASE = 32              # D-013
VIEWPORT_MIN_CELLS = 21          # D-014

# --- 时间 ---
TICK_HZ = 10                     # D-015
TICK_INTERVAL = 1.0 / TICK_HZ    # D-015
SPEED_MIN = 0.5                  # D-016
SPEED_MAX = 10.0                 # D-016

# --- AI（M3 使用）---
AI_TIMEOUT_S = 0.008             # D-017
AI_RADIUS_BASE = 20              # D-021
AI_RADIUS_MAX = 80               # D-021
AI_RADIUS_HIGHSPEED_MAX = 40     # D-048

# --- 生成（M2 起：障碍 / 墙壁）---
FOOD_PER_CHUNK_MIN = 3           # D-030
FOOD_PER_CHUNK_MAX = 5           # D-030
OBSTACLE_DENSITY = 0.05          # D-026（约 5%）
SPAWN_PROTECT_CHUNKS = 1         # D-007：出生点周围 1 圈 → 3×3 = 9 个 chunk 保护

# --- 历史 / 回放（M4）---
HISTORY_SIZE = 20                # D-031
REPLAY_MAX_BYTES = 100 * 1024    # D-032

# --- 渲染 ---
RENDER_FPS_TARGET = 60           # D-037（架构基线；M5 真机再谈 90~120）
