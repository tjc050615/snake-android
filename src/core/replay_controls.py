"""回放播放器控件状态（M4/R3）：暂停/继续 + 0.5x/1x/2x/4x 倍速，不支持拖拽后退。"""

from __future__ import annotations

SPEEDS = (0.5, 1.0, 2.0, 4.0)


def blocks_input(replay_mode: bool, confirm_active: bool) -> bool:
    """回放态与确认态都屏蔽全部输入源（键盘/摇杆/滑动/面板按钮）。"""
    return bool(replay_mode or confirm_active)


class ReplayControls:
    def __init__(self, total_ticks: int, speed_index: int = 1) -> None:
        self.total = max(0, int(total_ticks))
        self.tick = 0
        self.paused = True
        self.speed_index = max(0, min(speed_index, len(SPEEDS) - 1))

    @property
    def speed(self) -> float:
        return SPEEDS[self.speed_index]

    def toggle_pause(self) -> bool:
        self.paused = not self.paused
        return self.paused

    def next_speed(self) -> float:
        self.speed_index = (self.speed_index + 1) % len(SPEEDS)
        return self.speed

    def advance(self, dt: float) -> int:
        """按倍速推进；返回本帧应执行的 tick 数。"""
        if self.paused or dt <= 0:
            return 0
        # 逻辑 tick 基准 10Hz：一个 tick = 0.1s / speed
        ticks = int(dt * 10.0 * self.speed)
        ticks = min(ticks, self.total - self.tick)
        self.tick += max(0, ticks)
        return max(0, ticks)

    def finished(self) -> bool:
        return self.tick >= self.total

    def seek(self, tick: int) -> None:
        """不支持后退：只允许向前的跳转（拖拽后退被忽略）。"""
        if tick < self.tick:
            return
        self.tick = min(int(tick), self.total)
