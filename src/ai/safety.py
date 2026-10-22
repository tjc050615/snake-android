"""两级安全校验（M3/R2）。

一级：模拟吃完后（头=食物格、长度+1、尾巴不动），新蛇头能否到达当前蛇尾。
二级：从新蛇头做**洪水填充**统计可通行面积，要求 > 蛇长 + 10。
      —— 二级是**启发式加强**，不是数学证明：面积够不等于一定有活路，
         但面积不够基本必死。代码注释、UI 文案（strings.safety_l2_note）、
         ARCH 三处都标注这一口径（D-051）。

穿墙模式：两级 BFS 都忽略地形阻挡，但**保留蛇身**为不可通行。
"""

from __future__ import annotations

from collections import deque


def body_after_eat(snake, food: tuple[int, int]) -> list[tuple[int, int]]:
    """模拟吃到食物后的蛇身：头变成食物格，尾巴不动（长度 +1）。"""
    return [food] + list(snake.body)


def _neighbors(cell):
    x, y = cell
    return ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))


def level1_reachable(
    world,
    snake,
    food: tuple[int, int],
    wrap_mode: bool = False,
    max_nodes: int = 2000,
) -> bool:
    """一级：新蛇头到蛇尾是否可达。"""
    body = set(body_after_eat(snake, food))
    body.discard(food)  # 头所在格当然可站
    tail = snake.tail
    if food == tail:
        return True

    seen = {food}
    q = deque([food])
    steps = 0
    while q:
        cell = q.popleft()
        steps += 1
        if steps > max_nodes:
            return False
        for nxt in _neighbors(cell):
            if nxt in seen:
                continue
            if nxt == tail:
                return True  # 蛇尾是目标，它在 body 里但会随移动腾出
            if nxt in body:
                continue
            if not wrap_mode and world.is_blocked(nxt):
                continue
            seen.add(nxt)
            q.append(nxt)
    return False


def level2_area(
    world,
    snake,
    food: tuple[int, int],
    wrap_mode: bool = False,
    limit: int = 400,
) -> int:
    """二级：从新蛇头出发的连通面积（达到 limit 提前返回，省预算）。"""
    body = set(body_after_eat(snake, food))
    body.discard(food)

    seen = {food}
    q = deque([food])
    while q:
        cell = q.popleft()
        if len(seen) > limit:
            return len(seen)
        for nxt in _neighbors(cell):
            if nxt in seen or nxt in body:
                continue
            if not wrap_mode and world.is_blocked(nxt):
                continue
            seen.add(nxt)
            q.append(nxt)
    return len(seen)


def level2_ok(
    world,
    snake,
    food: tuple[int, int],
    wrap_mode: bool = False,
) -> bool:
    """二级（启发式加强）：连通面积 > 蛇长 + 10。"""
    need = len(snake) + 10
    return level2_area(world, snake, food, wrap_mode, limit=need + 1) > need


def is_safe_food(world, snake, food, wrap_mode: bool = False) -> bool:
    return level1_reachable(world, snake, food, wrap_mode) and level2_ok(
        world, snake, food, wrap_mode
    )
