"""AI 会话（M3/R3）：决策同步 + 高速档 + 统计采集。

语义（ARCH §15）：
- 决策结果**下一逻辑 tick 生效**：本 tick 算出的方向放进 `pending`，下个 tick 才消费。
- tick 到来时没有 `pending`（尚未算完 / 首次）→ **沿用上一有效方向**，并做 O(1) 单步校验；
  校验失败按 上→右→下→左 降级。
- 速度 ≥5x：每 2 个逻辑 tick 决策 1 次、预算 4ms、半径上限 40（D-040）。
"""

from __future__ import annotations

import logging

from ai.controller import STATE_DEAD, AIController

LOG = logging.getLogger("snake.ai")

HIGH_SPEED = 5.0


class AISession:
    def __init__(self, tick_hz: int = 10, stats_log_hz: float = 2.0,
                 deterministic: bool = True) -> None:
        self.deterministic = bool(deterministic)
        self.controller = AIController()
        if self.deterministic:
            self.controller.max_nodes = 1500
        self.tick_hz = tick_hz
        self.stats_log_every = max(1, int(round(tick_hz / stats_log_hz)))
        self.reset()

    # ---------- 生命周期 ----------
    def reset(self) -> None:
        self.controller = AIController()
        self.ticks = 0
        self.period = 1
        self.timeout_s = 0.008
        self.pending: tuple[int, int] | None = None          # 兼容字段
        self._next_pending: tuple[int, int] | None = None    # 兼容字段
        self.pending_path: list[tuple[int, int]] = []        # 上一 tick 算好、本 tick 使用的路径
        self._next_path: list[tuple[int, int]] = []          # 本 tick 算好、下一 tick 使用的路径
        self.last_direction: tuple[int, int] | None = None
        self.path: list[tuple[int, int]] = []
        self.path_tick = -1
        self._follow_cheap = False
        self.stats = {
            "strategy": "IDLE",
            "nodes": 0,
            "cost_avg_ms": 0.0,
            "cost_peak_ms": 0.0,
            "alive_ticks": 0,
            "eaten": 0,
            "blocked_l1": 0,
            "blocked_l2": 0,
            "follow_tail": 0,
            "loop_guard": 0,
            "timeouts": 0,
            "no_decision_reuse": 0,
            "reuse": 0,  # 兼容别名，与 no_decision_reuse 同值
            "emergency": 0,
            "stale_direction": 0,
        }

    # ---------- 每个逻辑 tick 调用 ----------
    def note_forced_reuse(self) -> None:
        """强制 chunk 帧跳过 AI 决策时调用：记一次"沿用上一方向"。"""
        self.stats["no_decision_reuse"] += 1
        self.stats["reuse"] = self.stats["no_decision_reuse"]
        return None

    def tick(self, world, snake, wrap_mode: bool = False, speed: float = 1.0,
             budget_s: float | None = None) -> tuple[int, int] | None:
        self.ticks += 1
        if getattr(self, "_last_len", None) is None:
            self._last_len = len(snake)
        elif len(snake) > self._last_len:
            self.stats["eaten"] += len(snake) - self._last_len
        self._last_len = len(snake)
        self._plan: list[tuple[int, int]] = getattr(self, "_plan", [])
        self._stall = getattr(self, "_stall", 0)
        self._last_target = getattr(self, "_last_target", None)
        self._last_dist = getattr(self, "_last_dist", None)
        high = speed >= HIGH_SPEED
        self.period = 2 if high else 1
        # 留 1ms 余量给 Python 调度抖动，保证总耗时 p99 < 8ms
        self.timeout_s = budget_s if budget_s is not None else (0.0035 if high else 0.0070)
        self.controller.radius_cap = 40 if high else 80

        # FOLLOW_TAIL 省钱模式：仅当「附近确实没食物」且连续使用不超过 12 tick
        near_food = any(abs(c[0] - snake.head[0]) <= 30 and abs(c[1] - snake.head[1]) <= 30
                        for c in world.foods())
        # 取消廉价直走：有食物就必须规划；全场无食物由 ensure 立即补
        cheap_ok = False
        if (cheap_ok and self.controller.state == "FOLLOW_TAIL"
                and self.last_direction is not None
                and self.controller.safe_step(world, snake, self.last_direction, wrap_mode)):
            self._cheap_ticks = getattr(self, "_cheap_ticks", 0) + 1
            # 廉价帧也要累计跟尾时长，否则 controller 的强制觅食永远触发不了
            self.controller._follow_streak += 1
            self._follow_cheap = True
            self.stats["follow_cheap"] = self.stats.get("follow_cheap", 0) + 1
            self.stats["alive_ticks"] = self.ticks
            return self.last_direction
        self._cheap_ticks = 0
        self._follow_cheap = False

        reuse_dir = None

        # 高速档：每 2 tick 决策一次；其余每 tick
        if self.ticks % self.period == 0:
            self._compute(world, snake, wrap_mode)

        # KI-016（方案 B，已与文档对齐）：本 tick 计算的方向直接交给本次 step；
        # 真正的"下一步生效"由 Snake.pending 保证（set_direction 只写 pending，
        # step() 才消费）。没有 pending（未计算/超时）时才 reuse。
        direction = self._direction_from(self._next_path, snake)
        self.pending_path = list(self._next_path)
        self._next_path = []

        if direction is not None and not self.controller.safe_step(
            world, snake, direction, wrap_mode
        ):
            direction = self._reuse(world, snake, wrap_mode)
            self.stats["stale_direction"] += 1

        if direction is None:
            direction = self._reuse(world, snake, wrap_mode)
            self.stats["no_decision_reuse"] += 1
            self.stats["reuse"] = self.stats["no_decision_reuse"]

        # 幽灵路径检测：目标不变且距离连续 8 tick 未缩短 → 标记死食物、强制重算
        target = self.controller.path[-1] if self.controller.path else None
        if target is not None:
            dist = abs(target[0] - snake.head[0]) + abs(target[1] - snake.head[1])
            if target == self._last_target and self._last_dist is not None and dist >= self._last_dist:
                self._stall += 1
            else:
                self._stall = 0
            self._last_target, self._last_dist = target, dist
            if self._stall >= 8:
                self.controller._bad_food[target] = self.controller.stats["plans"] + 200
                self.controller._follow_streak = 999
                self.controller.path = []
                self.stats["ghost_food"] = self.stats.get("ghost_food", 0) + 1
                self._stall = 0
        else:
            self._stall = 0

        if direction is not None:
            self.last_direction = direction

        self.stats["alive_ticks"] = self.ticks
        if self.ticks % self.stats_log_every == 0:
            self._log_stats()
        return direction

    # ---------- 内部 ----------
    def _direction_from(self, path, snake):
        """从缓存路径取下一步方向（跳过蛇头已经到达的点）。"""
        while path and path[0] == snake.head:
            path.pop(0)
        if not path:
            return None
        c = path[0]
        return (c[0] - snake.head[0], c[1] - snake.head[1])

    def _compute(self, world, snake, wrap_mode: bool) -> None:
        t0 = __import__("time").perf_counter()
        # 动态搜索深度：短蛇贪心、长蛇深搜
        if len(snake) < 30:
            self.controller.max_nodes = getattr(self, "max_nodes_small", 400)
        else:
            self.controller.max_nodes = getattr(self, "max_nodes_large", 800)
        deadline = None if self.deterministic else t0 + self.timeout_s
        self.controller.plan(world, snake, wrap_mode, deadline=deadline)
        cost_ms = (__import__("time").perf_counter() - t0) * 1000.0

        direction = self.controller.next_direction(snake)
        if direction is not None and self.controller.safe_step(world, snake, direction, wrap_mode):
            self._next_pending = direction
        self._plan = list(self.controller.path)
        self._next_path = list(self.controller.path)
        self.path = list(self.controller.path)
        self.path_tick = self.ticks
        self._accumulate(cost_ms)

    def _reuse(self, world, snake, wrap_mode: bool):
        if self.last_direction is not None and self.controller.safe_step(
            world, snake, self.last_direction, wrap_mode
        ):
            return self.last_direction
        offset = self.controller._nudge_offset if self.controller.state == "FOLLOW_TAIL" else 0
        fallback = self.controller.fallback_direction(world, snake, wrap_mode, offset=offset)
        return fallback

    def _accumulate(self, cost_ms: float) -> None:
        s = self.stats
        s["nodes"] = self.controller.pool.created
        s["strategy"] = self.controller.state
        s["follow_tail"] = self.controller.stats["follow_tail"]
        s["loop_guard"] = self.controller.stats["loop_guard"]
        s["blocked_l1"] = self.controller.stats["blocked_l1"]
        s["blocked_l2"] = self.controller.stats["blocked_l2"]
        n = max(1, self.ticks)
        s["cost_avg_ms"] = (s["cost_avg_ms"] * (n - 1) + cost_ms) / n
        s["cost_peak_ms"] = max(s["cost_peak_ms"], cost_ms)
        if self.controller.state == "FALLBACK":
            s["timeouts"] += 1

    def _log_stats(self) -> None:
        s = self.stats
        LOG.info(
            "ai strategy=%s nodes=%d avg=%.2fms peak=%.2fms alive=%d eaten=%d "
            "blocked_l1=%d blocked_l2=%d follow=%d loop=%d reuse=%d",
            s["strategy"], s["nodes"], s["cost_avg_ms"], s["cost_peak_ms"],
            s["alive_ticks"], s["eaten"], s["blocked_l1"], s["blocked_l2"],
            s["follow_tail"], s["loop_guard"], s["reuse"],
        )

    # ---------- 供渲染/测试 ----------
    def current_path(self, tick: int) -> list[tuple[int, int]]:
        """只有 tick 对得上才返回路径，避免画到旧路径。"""
        return self.path if self.path_tick == tick else []
