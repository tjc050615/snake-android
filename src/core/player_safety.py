"""玩家侧防死胡同（洪水填充）：拦截会导致空间不足的转向。"""

from __future__ import annotations

from collections import deque

DIRS = ((0, 1), (1, 0), (0, -1), (-1, 0))


def flood_area(world, snake, start, wrap_mode: bool = False, limit: int = 400) -> int:
    body = set(snake.body)
    body.discard(snake.tail)
    seen = {start}
    q = deque([start])
    while q and len(seen) < limit:
        x, y = q.popleft()
        for dx, dy in DIRS:
            n = (x + dx, y + dy)
            if n in seen or n in body:
                continue
            if not wrap_mode and world.is_blocked(n):
                continue
            seen.add(n)
            q.append(n)
    return len(seen)


def blocks_move(world, snake, direction, wrap_mode: bool = False) -> bool:
    """True = 这一步会让蛇钻进死圈，应拦截。"""
    hx, hy = snake.head
    nxt = (hx + direction[0], hy + direction[1])
    if nxt in snake.body and nxt != snake.tail:
        return True
    if not wrap_mode and world.is_blocked(nxt):
        return True
    area = flood_area(world, snake, nxt, wrap_mode)
    return area < len(snake) + 1
