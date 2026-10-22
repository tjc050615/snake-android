"""回放（M4/R2）：人类输入事件 / AI 每 tick 决策字节 / 中途切换。

约束：
- 文件 ≤ 100KB
- AI 回放最多 MAX_REPLAY_TICKS = 90000 个 tick（约 2.5 小时），超出停止录制、游戏继续
- 人类事件稀疏存储：只在方向变化 / 模式切换 / 调速时记录
- 回放只支持暂停与倍速，不支持拖拽后退
"""

from __future__ import annotations

MAX_REPLAY_BYTES = 100 * 1024
MAX_REPLAY_TICKS = 90000

DIR_CODE = {(0, 1): 0, (1, 0): 1, (0, -1): 2, (-1, 0): 3}
CODE_DIR = {0: (0, 1), 1: (1, 0), 2: (0, -1), 3: (-1, 0)}

MODE_HUMAN = "human"
MODE_AI = "ai"


class Recorder:
    def __init__(self, seed: int, mode: str = MODE_HUMAN) -> None:
        self.seed = int(seed)
        self.initial_mode = mode
        self.mode = mode
        self.ticks = 0
        self.events: list[tuple[int, str, object]] = []  # (tick, kind, value)
        self.decisions: list[str] = []                    # AI：每 tick 1 字节（A-D，JSON 安全）
        self.capped = False
        self.stopped = False
        self._last_dir: tuple[int, int] | None = None

    # ---------- 录制 ----------
    def tick(self, direction, mode: str | None = None) -> None:
        """每次逻辑 tick 调用；direction 为本 tick 实际生效方向。"""
        if self.stopped:
            return
        if mode is not None and mode != self.mode:
            self.events.append((self.ticks, "switch", mode))
            self.mode = mode

        if self.mode == MODE_AI:
            if self.ticks >= MAX_REPLAY_TICKS:
                self.stopped = True
                self.capped = True
                return
            self.decisions.append(chr(65 + DIR_CODE.get(direction, 1)))
        else:
            if direction != self._last_dir:
                self.events.append((self.ticks, "input", DIR_CODE.get(direction, 1)))
                self._last_dir = direction

        self.ticks += 1

    def speed_event(self, tick: int, speed: float) -> None:
        self.events.append((tick, "speed", round(float(speed), 2)))

    # ---------- 产物 ----------
    def to_payload(self) -> dict:
        return {
            "version": 1,
            "seed": self.seed,
            "mode": self.initial_mode,
            "ticks": self.ticks,
            "capped": self.capped,
            "stopped": self.stopped,
            "events": [(t, k, v) for (t, k, v) in self.events],
            "decisions": "".join(self.decisions),
        }

    def payload_size(self) -> int:
        import json

        return len(json.dumps(self.to_payload()).encode("utf-8"))

    def over_size_limit(self) -> bool:
        return self.payload_size() > MAX_REPLAY_BYTES


class Player:
    """按 tick 还原方向；用于回放与确定性测试。"""

    def __init__(self, payload: dict) -> None:
        self.seed = int(payload["seed"])
        self.ticks = int(payload.get("ticks", 0))
        self.initial_mode = payload.get("mode", MODE_HUMAN)
        self.events = [(int(t), k, v) for (t, k, v) in payload.get("events", [])]
        self.decisions = payload.get("decisions", "")
        self._input_iter = sorted((t, v) for (t, k, v) in self.events if k == "input")
        self._switch = sorted((t, v) for (t, k, v) in self.events if k == "switch")
        self._speed = sorted((t, v) for (t, k, v) in self.events if k == "speed")

    def mode_at(self, tick: int) -> str:
        mode = self.initial_mode
        for t, m in self._switch:
            if t <= tick:
                mode = m
        return mode

    def direction_at(self, tick: int) -> tuple[int, int] | None:
        if self.mode_at(tick) == MODE_AI:
            if tick < len(self.decisions):
                return CODE_DIR.get(ord(self.decisions[tick]) - 65, (1, 0))
            return None
        code = None
        for t, v in self._input_iter:
            if t <= tick:
                code = v
            else:
                break
        return CODE_DIR.get(code) if code is not None else None

    def speed_at(self, tick: int) -> float | None:
        speed = None
        for t, v in self._speed:
            if t <= tick:
                speed = v
        return speed
