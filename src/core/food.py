"""食物纯随机 + 保底（模块一.4）。

- 地图/障碍仍由 seed 决定（D-057 保持）
- 食物位置由 (seed) 派生的 RNG 洗牌：同 seed 可复现（回放需要），不同 seed 不同
- 每 tick 检查：无食物立刻补一个
"""

from __future__ import annotations

import random


def entropy_rng() -> random.Random:
    """系统熵：每次开局食物位置都不同。"""
    return random.Random()


def food_rng(seed: int) -> random.Random:
    return random.Random((int(seed) * 2654435761) & 0xFFFFFFFF)


def free_cells(world, snake, limit: int = 4096):
    """在已加载 chunk 内枚举可放食物的空格（避开蛇身/障碍/已有食物）。"""
    body = set(snake.body)
    out = []
    for (cx, cy) in world.loaded_chunks():
        for gx in range(cx * 32, cx * 32 + 32):
            for gy in range(cy * 32, cy * 32 + 32):
                cell = (gx, gy)
                if cell in body or cell in world._foods:  # noqa: SLF001
                    continue
                if world.is_blocked(cell):
                    continue
                out.append(cell)
                if len(out) >= limit:
                    return out
    return out


def reroll_foods(world, snake, rng: random.Random) -> None:
    """把当前已生成食物洗到随机空格（保留数量）。"""
    current = list(world.foods())
    if not current:
        return
    cells = free_cells(world, snake)
    if len(cells) < len(current):
        return
    rng.shuffle(cells)
    for cell in current:
        world.discard_food(cell)
    for cell in cells[: len(current)]:
        world.add_food(cell)


def ensure_local_food(world, snake, rng: random.Random, radius: int = 25):
    """保证蛇头附近有食物：AI 搜索半径内看不到食物时补一个（Bug 3）。

    只放在已加载、可通行、非蛇身的格子上；返回新食物坐标或 None。
    """
    hx, hy = snake.head
    for cell in world.foods():
        if abs(cell[0] - hx) <= radius and abs(cell[1] - hy) <= radius:
            return None
    cells = [
        c for c in free_cells(world, snake, limit=8192)
        if abs(c[0] - hx) <= radius and abs(c[1] - hy) <= radius
    ]
    if not cells:
        return None
    cell = rng.choice(cells)
    world.add_food(cell)
    return cell


def ensure_food(world, snake, rng: random.Random) -> tuple[int, int] | None:
    """场上无食物时立刻补一个；返回新食物坐标。"""
    if world.food_count() > 0:
        return None
    cells = free_cells(world, snake)
    if not cells:
        return None
    cell = rng.choice(cells)
    world.add_food(cell)
    return cell
