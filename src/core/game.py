"""对局状态机（R2：RUNNING / DEAD）。

把 World + Snake + TickClock 组装成一个可无头驱动的对象，
渲染层只读它，键盘只写方向 —— 便于 pytest 直接跑完整局。
"""

from __future__ import annotations

from dataclasses import dataclass

from app import constants as C
from core.snake import Snake
from core.tick import TickClock
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
        self.reset(self.seed)

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
        result = self.snake.step(self.world)
        if result.ate:
            self.score += 1
        if result.died:
            self.state = STATE_DEAD
        return result
