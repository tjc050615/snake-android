"""调试面板（M4/R3）：默认关闭；开启时显示 FPS/相机/蛇头/chunk 边界/AI 路径节点数。"""

from __future__ import annotations

from collections import deque

from app import strings
from app.fonts import FONT_NAME
from app.theme import palette
from kivy.uix.label import Label

from view.themed import ThemedMixin


class DebugOverlay(ThemedMixin, Label):
    def __init__(self, **kw) -> None:
        kw.setdefault("font_name", FONT_NAME)
        kw.setdefault("font_size", 12.0)
        kw.setdefault("halign", "left")
        kw.setdefault("valign", "top")
        kw.setdefault("size_hint", (None, None))
        kw.setdefault("size", (250, 130))
        super().__init__(text="", **kw)
        self.colors = palette("dark")
        self.apply_theme(self.colors)

    def show(self, data: dict) -> None:
        if not data:
            self.text = ""
            return
        lines = [
            f"{strings.t('fps')}: {data.get('fps', 0):.1f}",
            f"camera: {data.get('camera')} -> {data.get('camera_target')}",
            f"head: {data.get('head')}",
            f"grid: {data.get('chunk_border')}",
            f"ai path: {data.get('ai_path_nodes')}",
        ]
        self.text = "\n".join(lines)

    def apply_theme(self, colors: dict) -> None:
        self.colors = dict(colors)
        self.color = self.colors["text"]
