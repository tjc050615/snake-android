"""蛇身插值（R4）：把整数格蛇身转成可渲染的浮点格坐标。

规则（与 ARCH §9 一致）：
- 蛇头 i=0：`body[1] → body[0]`
- 中间节 1≤i≤n-2：`body[i+1] → body[i]`
- 尾巴 i=n-1：
  - `ate_food=True` → 停在 `body[-1]`（本 Tick 尾巴不让位）
  - `ate_food=False` → `prev_tail → body[-1]`
- `t` 必须来自 `TickClock.progress`（[0,1)），死亡时由 Game 冻结为 1.0
- 长度 1 不插值

纯函数，不依赖 Kivy。
"""

from __future__ import annotations


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def segment_cells(snake, progress: float) -> list[tuple[float, float]]:
    """返回从蛇头到蛇尾的浮点格坐标列表（长度与蛇身一致）。"""
    body = list(snake.body)
    n = len(body)
    if n == 1:
        return [(float(body[0][0]), float(body[0][1]))]

    # t 由调用方保证（TickClock.progress ∈ [0,1)，死亡冻结 1.0）；这里不再二次夹取
    t = float(progress)

    out: list[tuple[float, float]] = []
    for i in range(n - 1):
        src = body[i + 1]
        dst = body[i]
        out.append((_lerp(src[0], dst[0], t), _lerp(src[1], dst[1], t)))

    tail = body[-1]
    if snake.ate_food:
        out.append((float(tail[0]), float(tail[1])))
    else:
        prev = snake.prev_tail
        out.append((_lerp(prev[0], tail[0], t), _lerp(prev[1], tail[1], t)))

    return out


def to_pixel(cell: tuple[float, float], grid_size: int, origin_x: float, origin_y: float):
    """浮点格坐标 → 屏幕像素（格中心）。"""
    return (
        cell[0] * grid_size + grid_size / 2.0 - origin_x,
        cell[1] * grid_size + grid_size / 2.0 - origin_y,
    )
