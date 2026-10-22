"""蛇身插值（R4/R5A）：把整数格蛇身转成可渲染的浮点格坐标。

R5A：支持传入 out 缓冲复用，避免每帧新建结果 list。
"""

from __future__ import annotations


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def segment_cells(snake, progress: float, out: list | None = None) -> list[tuple[float, float]]:
    """返回从蛇头到蛇尾的浮点格坐标（长度 == 蛇身长度）。

    out 传入时复用该 list（clear + append），返回同一对象。
    """
    buf = out if out is not None else []
    buf.clear()

    body = list(snake.body)
    n = len(body)
    if n == 1:
        buf.append((float(body[0][0]), float(body[0][1])))
        return buf

    t = float(progress)
    for i in range(n - 1):
        src = body[i + 1]
        dst = body[i]
        buf.append((_lerp(src[0], dst[0], t), _lerp(src[1], dst[1], t)))

    tail = body[-1]
    if snake.ate_food:
        buf.append((float(tail[0]), float(tail[1])))
    else:
        prev = snake.prev_tail
        buf.append((_lerp(prev[0], tail[0], t), _lerp(prev[1], tail[1], t)))
    return buf


def to_pixel(cell: tuple[float, float], grid_size: int, origin_x: float, origin_y: float):
    """浮点格坐标 → 屏幕像素（格中心）。"""
    return (
        cell[0] * grid_size + grid_size / 2.0 - origin_x,
        cell[1] * grid_size + grid_size / 2.0 - origin_y,
    )
