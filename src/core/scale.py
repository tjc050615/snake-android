"""像素缩放（D-013 / D-014）。

公式：grid_size = max(16, round(32 * density))
整数缩放，保证像素对齐不模糊。
视口宽高不足 21 格时允许逐档下调，最低 16；降到 16 仍不足则**抛 ValueError**，
由调用方给出提示（M4 的 UI 文案），绝不静默返回一个不满足约束的值。
"""

from __future__ import annotations

from app import constants as C


def min_viewport_px() -> int:
    """满足 21 格所需的最小物理边长：21 * 16 = 336 px。"""
    return C.VIEWPORT_MIN_CELLS * C.GRID_SIZE_MIN


def grid_size_for_density(density: float) -> int:
    """核心公式：max(16, round(32 * density))。"""
    if density <= 0:
        raise ValueError("density must be positive")
    return max(C.GRID_SIZE_MIN, int(round(C.GRID_SIZE_BASE * float(density))))


def cells_for(size_px: float, grid_size: int) -> int:
    """某一边长能容纳的整格数（地板除，不四舍五入）。"""
    if grid_size <= 0:
        raise ValueError("grid_size must be positive")
    return int(size_px // grid_size)


def viewport_cells(width: float, height: float, grid_size: int) -> tuple[int, int]:
    return (cells_for(width, grid_size), cells_for(height, grid_size))


def viewport_ok(width: float, height: float, grid_size: int) -> bool:
    """视口宽、高是否都 ≥ 21 格（D-014）。"""
    cols, rows = viewport_cells(width, height, grid_size)
    return cols >= C.VIEWPORT_MIN_CELLS and rows >= C.VIEWPORT_MIN_CELLS


def fit_grid_size(density: float, width: float, height: float) -> int:
    """先按密度公式取值；若视口不足 21 格则逐档下调，下限 16。

    Raises:
        ValueError: 即使 grid_size 降到 16，视口仍不足 21 格（窗口过小）。
    """
    grid = grid_size_for_density(density)
    while grid > C.GRID_SIZE_MIN and not viewport_ok(width, height, grid):
        grid -= 1

    if not viewport_ok(width, height, grid):
        need = min_viewport_px()
        raise ValueError(
            f"viewport too small: {width:.0f}x{height:.0f}px; "
            f"need >= {C.VIEWPORT_MIN_CELLS} cells/side even at grid_size={C.GRID_SIZE_MIN} "
            f"(>= {need}x{need}px)"
        )
    return grid
