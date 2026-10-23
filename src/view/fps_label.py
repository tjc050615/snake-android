"""FPS 显示（模块一.3）：左上角固定 Label，Clock 每秒刷新。"""

from __future__ import annotations

import time

from kivy.clock import Clock
from kivy.uix.label import Label

from app.fonts import FONT_NAME
from app.theme import palette


class FpsLabel(Label):
    def __init__(self, **kw) -> None:
        kw.setdefault("font_name", FONT_NAME)
        kw.setdefault("font_size", 15.0)
        kw.setdefault("size_hint", (None, None))
        kw.setdefault("size", (96, 26))
        kw.setdefault("halign", "left")
        super().__init__(text="fps: --", **kw)
        self.color = (0.2, 1.0, 0.4, 1)   # 醒目绿
        self._t0 = time.perf_counter()
        self._frames = 0
        self._event = Clock.schedule_interval(self._tick, 1.0)

    def _tick(self, _dt: float) -> None:
        now = time.perf_counter()
        elapsed = max(1e-6, now - self._t0)
        self.text = f"fps: {int(round(self._frames / elapsed))}"
        self._frames = 0
        self._t0 = now

    def count_frame(self) -> None:
        self._frames += 1

    def apply_theme(self, colors: dict) -> None:
        self.color = (0.2, 1.0, 0.4, 1)
