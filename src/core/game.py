"""对局状态机（R2：RUNNING / DEAD）。

把 World + Snake + TickClock 组装成一个可无头驱动的对象，
渲染层只读它，键盘只写方向 —— 便于 pytest 直接跑完整局。
"""

from __future__ import annotations

from dataclasses import dataclass

from app import constants as C
from core.snake import Snake
from core.tick import TickClock
from core import food as food_mod
from core.world import World

STATE_RUNNING = "running"
STATE_DEAD = "dead"


@dataclass
class TickSummary:
    ticks: int = 0
    died: bool = False
    ate: bool = False


class Game:
    """一局游戏。reset() 之后即可复用实例。"""

    def __init__(self, seed: int = 0) -> None:
        self.seed = int(seed)
        # 穿墙模式（D-025）：True 时忽略障碍/墙壁，但自撞仍然死
        self.wrap_mode = False
        # 每个逻辑 tick 开始前的回调（AI 等），回调内可调用 set_direction
        self.tick_listeners: list = []
        self.reset(self.seed)

    # ---------- 模式 ----------
    def set_wrap_mode(self, enabled: bool) -> None:
        self.wrap_mode = bool(enabled)

    # ---------- 生命周期 ----------
    def reset(self, seed: int | None = None) -> None:
        if seed is not None:
            self.seed = int(seed)
        self.world = World(self.seed)
        self.world.ensure_chunk_at(C.SPAWN_CELL)
        self.snake = Snake.spawn()
        self.clock = TickClock()
        self.state = STATE_RUNNING
        self.score = 0
        self.ticks = 0
        # 食物随机化：由 seed 派生（同 seed 可复现，不同 seed 不同布局）
        self.food_rng = food_mod.food_rng(self.seed)
        food_mod.reroll_foods(self.world, self.snake, self.food_rng)

    # ---------- 输入 ----------
    def set_direction(self, direction: tuple[int, int]) -> bool:
        return self.snake.set_direction(direction)

    @property
    def tick_progress(self) -> float:
        """渲染插值进度：正常取 TickClock.progress；死亡时冻结为 1.0。"""
        if self.state != STATE_RUNNING:
            return 1.0
        return self.clock.progress

    # ---------- 驱动 ----------
    def update(self, dt: float) -> TickSummary:
        """渲染帧调用。返回这一帧实际执行了几个逻辑 Tick。"""
        if self.state != STATE_RUNNING:
            return TickSummary()
        n = self.clock.advance(dt)
        summary = TickSummary(ticks=0)
        for _ in range(n):
            result = self._tick()
            summary.ticks += 1
            summary.ate = summary.ate or result.ate
            if result.died:
                summary.died = True
                break
        return summary

    def _tick(self):
        self.ticks += 1
        food_mod.ensure_food(self.world, self.snake, self.food_rng)  # 保底：无食物立刻补
        for listener in self.tick_listeners:
            listener(self)
        result = self.snake.step(self.world, ignore_blocked=self.wrap_mode)
        if result.ate:
            self.score += 1
        if result.died:
            self.state = STATE_DEAD
        return result
