"""暂停恢复倒计时（M4/R2）：3 秒内不接受输入。"""

from __future__ import annotations

COUNTDOWN = 3.0


class PauseGate:
    def __init__(self, countdown: float = COUNTDOWN) -> None:
        self.countdown = float(countdown)
        self.remaining = 0.0
        self.paused = False

    def pause(self) -> None:
        self.paused = True
        self.remaining = self.countdown

    def resume_requested(self) -> None:
        """玩家点"继续"：开始倒计时（仍在暂停态，输入被屏蔽）。"""
        if self.paused and self.remaining <= 0:
            self.remaining = self.countdown

    def update(self, dt: float) -> None:
        if self.paused and self.remaining > 0:
            self.remaining = max(0.0, self.remaining - max(0.0, dt))
            if self.remaining <= 0:
                self.paused = False  # 倒计时结束自动恢复

    @property
    def counting_down(self) -> bool:
        return self.paused and self.remaining > 0

    @property
    def active(self) -> bool:
        return self.paused

    def accept_input(self) -> bool:
        """倒计时期间与暂停期间都不接受输入。"""
        return not self.paused

    def label_seconds(self) -> int:
        return int(self.remaining + 0.999)

    def finish(self) -> None:
        self.paused = False
        self.remaining = 0.0
