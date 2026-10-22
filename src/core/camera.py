"""相机（R3）：死区 + 滞回 + 硬吸附 + 指数平滑。

单位约定：
- `current_*` / `target_*` 均为**世界像素**（相机中心）。
- 死区、滞回、吸附阈值以**格**为单位，换算用 `grid_size`。

规则（D-008 ~ D-011、D-045）：
1. 蛇头距某侧边缘 > 10 格 → 不动。
2. 进入 ≤ 10 格 → 推视角，使蛇头恰好距该侧 10 格（`偏移 = max(0, 10 - 距边缘格数)`）。
3. x / y 完全独立判定。
4. 滞回：推过一次后，要退到 ≥ 12 格才解除；解除区间内 target 冻结，不再跟着蛇头回拉。
5. 蛇头距边缘 < 3 格 → current 直接吸附 target（跳过平滑，保证不出屏）。
6. 平滑：`alpha = 1 - exp(-dt * K)`，`current += (target - current) * alpha`。

相机只产出 `Viewport.at_center(...)`，**不改 `Viewport` 内部的坐标换算**。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app import constants as C
from core.viewport import Viewport


@dataclass
class Camera:
    grid_size: int
    view_width: float
    view_height: float
    dead_zone: float = C.CAMERA_DEADZONE_CELLS
    hyst: float = C.CAMERA_HYST_CELLS
    snap: float = C.CAMERA_SNAP_CELLS
    smooth_k: float = C.CAMERA_SMOOTH_K

    target_x: float = 0.0
    target_y: float = 0.0
    current_x: float = 0.0
    current_y: float = 0.0
    armed_x: bool = False
    armed_y: bool = False

    # ---------- 初始化 ----------
    def reset(self, cell: tuple[int, int]) -> None:
        g = self.grid_size
        cx = cell[0] * g + g / 2.0
        cy = cell[1] * g + g / 2.0
        self.target_x = self.current_x = cx
        self.target_y = self.current_y = cy
        self.armed_x = self.armed_y = False

    def resize(self, grid_size: int, view_width: float, view_height: float) -> None:
        """窗口变化时只更新几何参数，保留当前取景位置。"""
        self.grid_size = grid_size
        self.view_width = view_width
        self.view_height = view_height

    # ---------- 输出 ----------
    def viewport(self) -> Viewport:
        return Viewport.at_center(
            self.current_x, self.current_y, self.grid_size, self.view_width, self.view_height
        )

    def center(self) -> tuple[float, float]:
        return (self.current_x, self.current_y)

    # ---------- 单轴 ----------
    def _axis(
        self,
        pos_px: float,
        current: float,
        half: float,
        armed: bool,
        target: float,
    ) -> tuple[float, bool, float]:
        g = self.grid_size
        d_low = (pos_px - (current - half)) / g
        d_high = ((current + half) - pos_px) / g
        d = min(d_low, d_high)

        if armed and d >= self.dead_zone + self.hyst:
            # 退出推视角：相机停在原地（target 归位到 current）
            return (current, False, d)

        if d <= self.dead_zone:
            # 推视角：让蛇头恰好距该侧 dead_zone 格
            if d_low <= d_high:
                new_target = pos_px + half - self.dead_zone * g
            else:
                new_target = pos_px + self.dead_zone * g - half
            return (new_target, True, d)

        if not armed:
            # 自由状态：target 必须跟住 current，否则会朝过期 target 漂移
            return (current, False, d)

        # armed 且 10 < d < 12：冻结 target，避免边界来回抽动
        return (target, armed, d)

    # ---------- 推进 ----------
    def update(self, dt: float, head_cell: tuple[int, int]) -> None:
        g = self.grid_size
        hx = head_cell[0] * g + g / 2.0
        hy = head_cell[1] * g + g / 2.0

        self.target_x, self.armed_x, d_x = self._axis(
            hx, self.current_x, self.view_width / 2.0, self.armed_x, self.target_x
        )
        self.target_y, self.armed_y, d_y = self._axis(
            hy, self.current_y, self.view_height / 2.0, self.armed_y, self.target_y
        )

        alpha = (1.0 - math.exp(-max(dt, 0.0) * self.smooth_k)) if dt > 0 else 0.0

        if d_x < self.snap:
            self.current_x = self.target_x
        else:
            self.current_x += (self.target_x - self.current_x) * alpha

        if d_y < self.snap:
            self.current_y = self.target_y
        else:
            self.current_y += (self.target_y - self.current_y) * alpha
