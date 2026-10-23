"""输入缓冲队列（模块三）：连续滑动入队，逐 tick 出队，严格禁止 180° 掉头。"""

from __future__ import annotations

from collections import deque

MAX_QUEUE = 3


def is_reverse(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] + b[0] == 0 and a[1] + b[1] == 0


class InputQueue:
    def __init__(self, maxlen: int = MAX_QUEUE) -> None:
        self._q: deque[tuple[int, int]] = deque(maxlen=maxlen)

    def push(self, direction: tuple[int, int], current: tuple[int, int]) -> bool:
        """入队；与「队尾（或当前方向）」相反则拒绝。返回是否入队。"""
        last = self._q[-1] if self._q else current
        if is_reverse(direction, last):
            return False
        if direction == last:
            return False  # 同向去重
        self._q.append(direction)
        return True

    def pop(self) -> tuple[int, int] | None:
        return self._q.popleft() if self._q else None

    def clear(self) -> None:
        self._q.clear()

    def __len__(self) -> int:
        return len(self._q)
