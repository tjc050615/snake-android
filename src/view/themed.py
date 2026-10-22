"""覆盖层统一主题接口（M4/R3）：背景 + 文字 + 按钮色。"""

from __future__ import annotations

from kivy.graphics import Color, Rectangle


class ThemedMixin:
    """给 BoxLayout 类覆盖层加背景与文字着色能力。"""

    def apply_theme(self, colors: dict) -> None:
        self.colors = dict(colors)
        self._paint_background()
        self._paint_children()

    def _paint_background(self) -> None:
        if getattr(self, "_bg_rect", None) is None:
            with self.canvas.before:
                self._bg_color = Color(*self.colors["panel_bg"])
                self._bg_rect = Rectangle(pos=self.pos, size=self.size)
            self.bind(pos=self._sync_bg, size=self._sync_bg)
        else:
            self._bg_color.rgba = self.colors["panel_bg"]
            self._sync_bg()

    def _sync_bg(self, *_args) -> None:
        if getattr(self, "_bg_rect", None) is not None:
            self._bg_rect.pos = self.pos
            self._bg_rect.size = self.size

    def _paint_children(self) -> None:
        from kivy.uix.button import Button
        from kivy.uix.label import Label

        text = self.colors.get("text", (1, 1, 1, 1))
        btn_bg = self.colors.get("button_bg", (0.2, 0.2, 0.2, 1))
        btn_text = self.colors.get("button_text", (1, 1, 1, 1))
        for child in self.walk():
            if isinstance(child, Label):
                child.color = text
            elif isinstance(child, Button):
                child.background_color = btn_bg
                child.color = btn_text
