"""暂停 / 恢复倒计时（M4/R2，R3 修正语义）。

- 暂停可以无限久
- 玩家点"继续"后才启动 3-2-1 倒计时
- 暂停中与倒计时中都 **不接受输入**（防误触）
- 倒计时结束才真正恢复
"""

from __future__ import annotations

COUNTDOWN = 3.0


class PauseGate:
    def __init__(self, countdown: float = COUNTDOWN) -> None:
        self.countdown = float(countdown)
        self.paused = False
        self.counting = False
        self.remaining = 0.0

    def pause(self) -> None:
        self.paused = True
        self.counting = False
        self.remaining = 0.0

    def request_resume(self) -> None:
        """玩家点"继续"：开始 3-2-1，此时仍未恢复。"""
        if self.paused and not self.counting:
            self.counting = True
            self.remaining = self.countdown

    def update(self, dt: float) -> None:
        if not (self.paused and self.counting):
            return
        self.remaining = max(0.0, self.remaining - max(0.0, dt))
        if self.remaining <= 0:
            self.counting = False
            self.paused = False

    # ---------- 状态 ----------
    @property
    def counting_down(self) -> bool:
        return self.paused and self.counting

    @property
    def active(self) -> bool:
        return self.paused

    def accept_input(self) -> bool:
        return not self.paused  # 暂停与倒计时阶段都属于 paused

    def label_seconds(self) -> int:
        return int(self.remaining + 0.999)

    def finish(self) -> None:
        self.paused = False
        self.counting = False
        self.remaining = 0.0
