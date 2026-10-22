"""调试面板数据（M4/R3）：默认关闭，关闭时零采集。

`collect()` 在 `enabled=False` 时直接返回空 dict，不访问 world/game/session，
因此关闭状态没有任何统计与字符串格式化开销。
"""

from __future__ import annotations

import time
from collections import deque


class DebugStats:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = bool(enabled)
        self.collect_calls = 0
        self.frame_times: deque[float] = deque(maxlen=60)  # 固定窗口，不重建列表
        self._last_frame = 0.0
        self._buf: dict = {}                              # collect() 复用同一个 dict
        self.last: dict = self._buf

    def collect(self, game=None, camera=None, session=None, viewport=None) -> dict:
        if not self.enabled:      # 关闭：完全不采样、不更新时间戳
            return self._buf
        self.collect_calls += 1
        if game is None:
            return self._buf

        now = time.perf_counter()
        if self._last_frame > 0:
            dt = now - self._last_frame
            if dt > 0:
                self.frame_times.append(dt)
        self._last_frame = now
        fps = (len(self.frame_times) / sum(self.frame_times)) if self.frame_times else 0.0

        self._buf["head"] = game.snake.head
        self._buf["fps"] = fps
        self._buf["camera"] = (
            (round(camera.current_x, 1), round(camera.current_y, 1)) if camera else None
        )
        self._buf["camera_target"] = (
            (round(camera.target_x, 1), round(camera.target_y, 1)) if camera else None
        )
        self._buf["chunk_border"] = viewport.grid_size if viewport else None
        self._buf["ai_path_nodes"] = len(session.path) if session is not None else 0
        return self._buf

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
