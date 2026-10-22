"""固定步长 Tick（D-015 / D-016）。

逻辑与渲染解耦：渲染每帧调一次 `advance(dt)`，只有累加够一个 interval 才跑逻辑。
"""

from __future__ import annotations

from app import constants as C


class TickClock:
    """累加器式固定步长时钟。"""

    def __init__(
        self,
        interval: float = C.TICK_INTERVAL,
        max_ticks_per_advance: int = 4,
    ) -> None:
        if interval <= 0:
            raise ValueError("interval must be positive")
        self.base_interval = float(interval)
        self.interval = float(interval)
        self.max_ticks_per_advance = int(max_ticks_per_advance)
        self.accumulator = 0.0

    # ---------- 调速（D-016）----------
    def set_speed(self, speed: float) -> None:
        """0.5x~10x：只改 interval，不改渲染帧率与碰撞规则。"""
        speed = min(max(float(speed), C.SPEED_MIN), C.SPEED_MAX)
        self.interval = self.base_interval / speed

    @property
    def speed(self) -> float:
        return self.base_interval / self.interval

    # ---------- 推进 ----------
    def advance(self, dt: float) -> int:
        """推进 dt 秒，返回本次应执行的逻辑 Tick 数（有上限，防卡顿螺旋）。"""
        if dt <= 0:
            return 0
        self.accumulator += dt
        ticks = 0
        while self.accumulator >= self.interval and ticks < self.max_ticks_per_advance:
            self.accumulator -= self.interval
            ticks += 1
        # 掉帧过多时丢弃余量，避免"追帧"雪崩
        if self.accumulator >= self.interval:
            self.accumulator = 0.0
        return ticks

    def reset(self) -> None:
        self.accumulator = 0.0

    @property
    def progress(self) -> float:
        """当前 Tick 内进度，范围 [0, 1)。插值 t **只能**从这里取，禁止读墙钟。

        正常路径下 advance() 已保证 accumulator < interval，所以这里不会命中
        >= 1.0 的分支；该分支只是兜浮点误差（返回 0 表示下一 Tick 起点）。
        """
        if self.interval <= 0:
            return 0.0
        p = self.accumulator / self.interval
        if p < 0.0:
            return 0.0
        return p if p < 1.0 else 0.0
