"""AI 控制器（M3/R2）：状态机 + 局部 A* + 两级安全校验 + 跟尾兜底 + 防循环。

R2 起 AI 不再"允许随便死"：吃食物前必须过两级校验（一级可达性 / 二级面积启发式），
否则退化为跟随蛇尾；蛇头在最近 20 步内重复出现 3 次则强制跟尾并做固定优先级微调。
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

from ai import safety
from ai.search import NodePool, astar, manhattan

STATE_IDLE = "IDLE"
STATE_SEEKING_FOOD = "SEEKING_FOOD"
STATE_FOLLOW_TAIL = "FOLLOW_TAIL"
STATE_FALLBACK = "FALLBACK"
STATE_DEAD = "DEAD"

# 确定性降级顺序：上 → 右 → 下 → 左（D-018）
FALLBACK_DIRS = ((0, 1), (1, 0), (0, -1), (-1, 0))
MAX_FOOD_CANDIDATES = 12   # R5C：扩大候选，避免只盯最近 4 个
LOOP_WINDOW = 20
LOOP_THRESHOLD = 3


@dataclass
class Vision:
    """向后兼容的占位；视野已改为 World.loaded_rect()。"""

    view_w: int | None = None
    view_h: int | None = None


class AIController:
    def __init__(self, view_w: int | None = None, view_h: int | None = None,
                 max_nodes: int = 4000) -> None:
        self.vision = Vision(view_w=view_w, view_h=view_h)
        self.pool = NodePool()
        self.max_nodes = max_nodes
        self.state = STATE_IDLE
        self.path: list[tuple[int, int]] = []
        self.recent_heads: deque[tuple[int, int]] = deque(maxlen=LOOP_WINDOW)
        self.radius_cap = 80  # 高速档由会话改成 40（D-040）
        self._nudge_offset = 0
        self.stats = {
            "state": self.state,
            "nodes": 0,
            "path_len": 0,
            "plans": 0,
            "blocked_l1": 0,
            "blocked_l2": 0,
            "follow_tail": 0,
            "loop_guard": 0,
            "cost_ms": 0.0,
        }

    # ---------- 视野 ----------
    def search_radius(self, snake_len: int) -> int:
        return min(snake_len + 20, self.radius_cap)

    def rect_for(self, head, snake_len, world=None):
        r = self.search_radius(snake_len)
        rect = (head[0] - r, head[1] - r, head[0] + r, head[1] + r)
        if world is None:
            return rect
        loaded = world.loaded_rect()
        if loaded is None:
            return rect
        return (
            max(rect[0], loaded[0]),
            max(rect[1], loaded[1]),
            min(rect[2], loaded[2]),
            min(rect[3], loaded[3]),
        )

    # ---------- 规划 ----------
    def plan(self, world, snake, wrap_mode: bool = False, deadline=None):
        head = snake.head
        self.recent_heads.append(head)
        rect = self.rect_for(head, len(snake), world)
        x0, y0, x1, y1 = rect

        def in_rect(c):
            return x0 <= c[0] <= x1 and y0 <= c[1] <= y1

        def passable(c):
            if not in_rect(c) or c in snake.occupied:
                return False
            return wrap_mode or not world.is_blocked(c)

        self.stats["plans"] += 1

        # 防循环：最近 20 步里蛇头重复 ≥3 次 → 强制跟尾 + 微调
        if self.recent_heads.count(head) >= LOOP_THRESHOLD:
            self.stats["loop_guard"] += 1
            self._nudge_offset = (self._nudge_offset + 1) % 4
            # 关键：触发后清空窗口，否则会每 tick 都命中、永远回不到找食物
            self.recent_heads.clear()
            return self._follow_tail(snake, rect, passable, deadline=deadline)

        foods = sorted(
            (c for c in world.foods_in_rect(*rect) if in_rect(c)),
            key=lambda c: (manhattan(head, c), c[0], c[1]),
        )

        for food in foods[:MAX_FOOD_CANDIDATES]:
            if deadline is not None and time.perf_counter() > deadline:
                break  # 预算耗尽：不再尝试更多候选，直接走兜底
            if not safety.level1_reachable(world, snake, food, wrap_mode, deadline=deadline):
                self.stats["blocked_l1"] += 1
                continue
            if not safety.level2_ok(world, snake, food, wrap_mode, deadline=deadline):
                self.stats["blocked_l2"] += 1
                continue

            path = astar(head, food, passable, rect, pool=self.pool,
                         max_nodes=self.max_nodes, deadline=deadline)
            if path:
                self.path = path
                self.state = STATE_SEEKING_FOOD
                self.stats.update(state=self.state, path_len=len(path), nodes=self.pool.created)
                return path
            # A* 空路径不代表其它食物不可达：继续尝试下一个候选
            continue

        return self._follow_tail(snake, rect, passable, deadline=deadline)

    def _follow_tail(self, snake, rect, passable, deadline=None):
        self.stats["follow_tail"] += 1
        tail = snake.tail
        self.state = STATE_FOLLOW_TAIL
        if tail == snake.head:
            self.path = []
            self.stats.update(state=self.state, path_len=0)
            return []

        # 尾巴格本身在 occupied 里，但它是跟随目标，必须可通行
        def passable_tail(c):
            return True if c == tail else passable(c)

        path = astar(snake.head, tail, passable_tail, rect, pool=self.pool,
                     max_nodes=self.max_nodes, deadline=deadline)
        self.path = path
        self.stats.update(state=self.state, path_len=len(path))
        return path

    # ---------- 单步 ----------
    def next_direction(self, snake):
        if not self.path:
            return None
        nxt = self.path[0]
        return (nxt[0] - snake.head[0], nxt[1] - snake.head[1])

    def safe_step(self, world, snake, direction, wrap_mode: bool = False) -> bool:
        head = snake.head
        nxt = (head[0] + direction[0], head[1] + direction[1])
        if nxt in snake.occupied and nxt != snake.tail:
            return False
        if not (wrap_mode or not world.is_blocked(nxt)):
            return False
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

    def fallback_direction(self, world, snake, wrap_mode: bool = False, offset: int = 0):
        """严格按 上→右→下→左（可整体旋转 offset）取第一个通过 O(1) 校验的方向。"""
        dirs = FALLBACK_DIRS[offset:] + FALLBACK_DIRS[:offset]
        for direction in dirs:
            if self.safe_step(world, snake, direction, wrap_mode):
                return direction
        return None

    def decide(self, world, snake, wrap_mode: bool = False, timeout_s: float = 0.008):
        t0 = time.perf_counter()
        deadline = t0 + max(0.0005, timeout_s)
        path = self.plan(world, snake, wrap_mode, deadline=deadline)
        direction = self.next_direction(snake) if path else None
        self.stats["cost_ms"] = (time.perf_counter() - t0) * 1000.0

        if direction is not None and self.safe_step(world, snake, direction, wrap_mode):
            return direction

        offset = self._nudge_offset if self.state == STATE_FOLLOW_TAIL else 0
        fallback = self.fallback_direction(world, snake, wrap_mode, offset=offset)
        if fallback is not None:
            if direction is not None:
                self.state = STATE_FALLBACK
                self.stats["state"] = self.state
            return fallback
        self.state = STATE_DEAD
        self.stats["state"] = self.state
        return None
