"""AI 控制器（M3/R1）：状态机 + 局部 A* + 食物搜索。

R1 只做"能吃食物、路径合理"，**没有两级安全校验**（R2 加），所以这一轮 AI 允许死。
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from ai.search import NodePool, astar, manhattan

STATE_IDLE = "IDLE"
STATE_SEEKING_FOOD = "SEEKING_FOOD"
STATE_FOLLOW_TAIL = "FOLLOW_TAIL"
STATE_FALLBACK = "FALLBACK"
STATE_DEAD = "DEAD"

# 确定性降级顺序：上 → 右 → 下 → 左（D-018）
FALLBACK_DIRS = ((0, 1), (1, 0), (0, -1), (-1, 0))


@dataclass
class Vision:
    """以蛇头为中心的方形/矩形视野（受视口尺寸约束）。"""

    view_w: int = 41
    view_h: int = 23

    def rect(self, head: tuple[int, int], radius: int) -> tuple[int, int, int, int]:
        half_x = min(radius, max(1, self.view_w // 2))
        half_y = min(radius, max(1, self.view_h // 2))
        return (
            head[0] - half_x,
            head[1] - half_y,
            head[0] + half_x,
            head[1] + half_y,
        )


class AIController:
    """状态机 + 单步规划。所有世界访问都走 World 的只读接口。"""

    def __init__(self, view_w: int = 41, view_h: int = 23, max_nodes: int = 4000) -> None:
        self.vision = Vision(view_w=view_w, view_h=view_h)
        self.pool = NodePool()
        self.max_nodes = max_nodes
        self.state = STATE_IDLE
        self.path: list[tuple[int, int]] = []
        self.stats = {
            "state": self.state,
            "nodes": 0,
            "path_len": 0,
            "plans": 0,
        }

    # ---------- 视野 ----------
    def search_radius(self, snake_len: int) -> int:
        return min(snake_len + 20, 80)

    def rect_for(self, head: tuple[int, int], snake_len: int) -> tuple[int, int, int, int]:
        return self.vision.rect(head, self.search_radius(snake_len))

    # ---------- 规划 ----------
    def plan(self, world, snake, wrap_mode: bool = False) -> list[tuple[int, int]]:
        head = snake.head
        rect = self.rect_for(head, len(snake))
        x0, y0, x1, y1 = rect

        def in_rect(c: tuple[int, int]) -> bool:
            return x0 <= c[0] <= x1 and y0 <= c[1] <= y1

        def passable(c: tuple[int, int]) -> bool:
            if not in_rect(c):
                return False
            if c in snake.occupied:
                return False
            return wrap_mode or not world.is_blocked(c)

        self.stats["plans"] += 1

        foods = {c for c in world.foods_in_rect(*rect) if in_rect(c)}
        if not foods:
            self.state = STATE_IDLE
            self.path = []
            self.stats.update(state=self.state, path_len=0)
            return []

        # 最近食物；平局用 (距离, x, y) 保证确定性
        target = min(foods, key=lambda c: (manhattan(head, c), c[0], c[1]))
        path = astar(head, target, passable, rect, pool=self.pool, max_nodes=self.max_nodes)

        self.path = path
        self.state = STATE_SEEKING_FOOD if path else STATE_IDLE
        self.stats.update(state=self.state, path_len=len(path), nodes=self.pool.created)
        return path

    # ---------- 单步 ----------
    def next_direction(self, snake) -> tuple[int, int] | None:
        if not self.path:
            return None
        nxt = self.path[0]
        return (nxt[0] - snake.head[0], nxt[1] - snake.head[1])

    # ---------- O(1) 单步安全校验（R1 只用于降级兜底，R2 全面接入） ----------
    def safe_step(
        self,
        world,
        snake,
        direction: tuple[int, int],
        wrap_mode: bool = False,
    ) -> bool:
        head = snake.head
        nxt = (head[0] + direction[0], head[1] + direction[1])
        if nxt in snake.occupied and nxt != snake.tail:
            return False
        if not (wrap_mode or not world.is_blocked(nxt)):
            return False
        # 四邻除来路外至少 1 个可通行，避免走进死胡同
        back = (-direction[0], -direction[1])
        free = 0
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (dx, dy) == back:
                continue
            c = (nxt[0] + dx, nxt[1] + dy)
            if c in snake.occupied and c != snake.tail:
                continue
            if not wrap_mode and world.is_blocked(c):
                continue
            free += 1
        return free >= 1

    def fallback_direction(self, world, snake, wrap_mode: bool = False):
        """按 上→右→下→左 取第一个通过单步校验的方向。"""
        for direction in FALLBACK_DIRS:
            if self.safe_step(world, snake, direction, wrap_mode):
                return direction
        return None

    def decide(
        self, world, snake, wrap_mode: bool = False, timeout_s: float = 0.008
    ) -> tuple[int, int] | None:
        """一次决策：规划 → 取方向 → 不通过单步校验就降级。"""
        t0 = time.perf_counter()
        path = self.plan(world, snake, wrap_mode)
        direction = self.next_direction(snake) if path else None
        self.stats["cost_ms"] = (time.perf_counter() - t0) * 1000.0

        if direction is not None and self.safe_step(world, snake, direction, wrap_mode):
            return direction

        fallback = self.fallback_direction(world, snake, wrap_mode)
        if fallback is not None:
            self.state = STATE_FALLBACK if direction is not None else self.state
            self.stats["state"] = self.state
            return fallback
        self.state = STATE_DEAD
        self.stats["state"] = self.state
        return None
