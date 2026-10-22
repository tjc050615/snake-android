"""世界坐标 ↔ 屏幕像素的纯数学变换（不依赖 Kivy）。

坐标约定：
- 世界坐标以**格**为逻辑单位，y 轴向上（与 Kivy 屏幕坐标同向，避免翻轴）。
- 视口用"世界像素"描述左上/左下原点：origin = 屏幕 (0,0) 对应的世界像素坐标。
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Viewport:
    origin_x: float
    origin_y: float
    grid_size: int
    width: float
    height: float

    # ---------- 构造 ----------
    @classmethod
    def at_center(
        cls, center_x: float, center_y: float, grid_size: int, width: float, height: float
    ) -> "Viewport":
        """以世界像素中心定位（R3 相机用这个入口，内部换算不变）。"""
        return cls(
            origin_x=center_x - width / 2.0,
            origin_y=center_y - height / 2.0,
            grid_size=grid_size,
            width=width,
            height=height,
        )

    @classmethod
    def centered_on_cell(
        cls, cell: tuple[int, int], grid_size: int, width: float, height: float
    ) -> "Viewport":
        """让该格中心落在屏幕中心（等价于 at_center(cell 中心)）。"""
        cx = cell[0] * grid_size + grid_size / 2.0
        cy = cell[1] * grid_size + grid_size / 2.0
        return cls.at_center(cx, cy, grid_size, width, height)

    # ---------- 变换 ----------
    def to_screen(self, px: float, py: float) -> tuple[float, float]:
        """世界像素 → 屏幕像素。"""
        return (px - self.origin_x, py - self.origin_y)

    def cell_rect(self, cell: tuple[int, int]) -> tuple[float, float, float, float]:
        """格 → 屏幕矩形 (x, y, w, h)，左下角为基准。"""
        g = self.grid_size
        sx, sy = self.to_screen(cell[0] * g, cell[1] * g)
        return (sx, sy, float(g), float(g))

    def cell_at_screen(self, sx: float, sy: float) -> tuple[int, int]:
        """屏幕像素 → 格坐标（R2 的输入/拾取会用）。"""
        wx = sx + self.origin_x
        wy = sy + self.origin_y
        return (math.floor(wx / self.grid_size), math.floor(wy / self.grid_size))

    # ---------- 可见范围 ----------
    def visible_bounds(self) -> tuple[int, int, int, int]:
        """返回 (x0, y0, x1, y1)，x1 / y1 为**开区间**上界。"""
        g = self.grid_size
        x0 = math.floor(self.origin_x / g)
        y0 = math.floor(self.origin_y / g)
        x1 = math.floor((self.origin_x + self.width) / g) + 1
        y1 = math.floor((self.origin_y + self.height) / g) + 1
        return (x0, y0, x1, y1)

    def iter_visible_cells(self):
        x0, y0, x1, y1 = self.visible_bounds()
        for y in range(y0, y1):
            for x in range(x0, x1):
                yield (x, y)

    def covers(self, cell: tuple[int, int]) -> bool:
        x0, y0, x1, y1 = self.visible_bounds()
        return x0 <= cell[0] < x1 and y0 <= cell[1] < y1
