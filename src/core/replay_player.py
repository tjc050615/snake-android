"""回放真实驱动（M4/R3）：把录制数据映射回 Game，逐 tick 重演。

与 `ReplayControls` 配合：
- controls 决定"本帧该走几个回放 tick"（受暂停与倍速影响）
- driver 对每个 tick 注入录制方向并推进一逻辑 tick
- 蛇身/食物/分数自然按录制结果重演（同 seed + 同方向 ⇒ 同轨迹）
"""

from __future__ import annotations

from app import constants as C
from core.replay import Player
from core.replay_controls import ReplayControls


class ReplayDriver:
    def __init__(self, game, payload: dict, speed_index: int = 1) -> None:
        self.game = game
        self.payload = payload
        self.player = Player(payload)
        self.controls = ReplayControls(int(payload.get("ticks", 0)), speed_index)
        self.controls.paused = False  # 打开即播
        self.heads: list[tuple[int, int]] = []
        self.finished = False
        self._acc = 0.0  # 帧间累积：16ms 帧不能直接取整成 0 tick
        self._recorded_heads(payload)

    # ---------- 录制数据里的蛇头轨迹（无则留空） ----------
    def _recorded_heads(self, payload: dict) -> None:
        heads = payload.get("heads") or []
        self.expected_heads = [tuple(h) for h in heads]

    # ---------- 播放 ----------
    def step(self, n: int) -> int:
        played = 0
        for _ in range(max(0, n)):
            if self.controls.finished():
                self.finished = True
                break
            tick = self.controls.tick
            direction = self.player.direction_at(tick)
            if direction is not None:
                self.game.set_direction(direction)
            self.game.update(C.TICK_INTERVAL)
            self.controls.tick += 1
            played += 1
            self.heads.append(self.game.snake.head)
            if self.controls.finished():
                self.finished = True
                break
        return played

    def advance(self, dt: float) -> int:
        """按暂停/倍速推进；用累积时间换算 tick，避免小 dt 永远取整成 0。"""
        if self.finished or self.controls.paused:
            return 0
        self._acc += max(0.0, float(dt)) * 10.0 * self.controls.speed
        n = int(self._acc)
        if n <= 0:
            return 0
        self._acc -= n
        n = min(n, self.controls.total - self.controls.tick)
        if n <= 0:
            return 0
        return self.step(n)

    # ---------- 控制 ----------
    def toggle_pause(self) -> bool:
        return self.controls.toggle_pause()

    def set_speed(self, index: int) -> None:
        self.controls.speed_index = max(0, min(index, 3))

    def progress(self) -> tuple[int, int]:
        return self.controls.tick, self.controls.total

    def overlay_text(self) -> str:
        """同一帧返回正确文案：已结束立刻显示"回放结束"。"""
        if self.finished:
            return self.end_text()
        done, total = self.progress()
        from app import strings

        return f"{strings.t('replay')} {done}/{total}"

    def end_text(self) -> str:
        from app import strings

        return strings.t("replay_end")
