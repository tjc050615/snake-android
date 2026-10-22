"""调试面板数据（M4/R3）：默认关闭，关闭时零采集。

`collect()` 在 `enabled=False` 时直接返回空 dict，不访问 world/game/session，
因此关闭状态没有任何统计与字符串格式化开销。
"""

from __future__ import annotations


class DebugStats:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = bool(enabled)
        self.collect_calls = 0
        self.last: dict = {}

    def collect(self, game=None, camera=None, session=None, viewport=None) -> dict:
        self.collect_calls += 1
        if not self.enabled or game is None:
            return {}

        data = {
            "head": game.snake.head,
            "fps": 0.0,
            "camera": (round(camera.current_x, 1), round(camera.current_y, 1)) if camera else None,
            "camera_target": (round(camera.target_x, 1), round(camera.target_y, 1)) if camera else None,
            "chunk_border": viewport.grid_size if viewport else None,
            "ai_path_nodes": len(session.path) if session is not None else 0,
        }
        self.last = data
        return data

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
