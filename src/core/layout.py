"""70/30 分栏几何（纯函数，M4/R1）。"""

from __future__ import annotations

GAME_RATIO = 0.70


def split_rects(width: float, height: float, ratio: float = GAME_RATIO):
    """返回 (game_rect, panel_rect)，每项为 (x, y, w, h)。

    y 轴向上：两块都从 y=0 起，高度相同。左游戏区取整像素，保证两区宽度之和 == 窗口宽。
    """
    if width <= 0 or height <= 0:
        raise ValueError("width/height must be positive")
    if not 0.0 < ratio < 1.0:
        raise ValueError("ratio must be in (0, 1)")

    game_w = int(round(width * ratio))
    panel_w = int(width) - game_w
    return (0.0, 0.0, float(game_w), float(height)), (float(game_w), 0.0, float(panel_w), float(height))


def in_rect(rect: tuple[float, float, float, float], x: float, y: float) -> bool:
    """点是否在矩形内（左闭右开，避免两块区域在边界上重复命中）。"""
    rx, ry, rw, rh = rect
    return rx <= x < rx + rw and ry <= y < ry + rh

