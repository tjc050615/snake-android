"""二次确认弹窗（M4/R3）：重开/退出前确认，确认期间冻结游戏。"""

from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from app import strings
from app.fonts import FONT_NAME
from app.theme import palette
from view.themed import ThemedMixin


class ConfirmDialog(ThemedMixin, BoxLayout):
    def __init__(self, action: str, on_confirm=None, on_cancel=None, **kw) -> None:
        super().__init__(orientation="vertical", padding=14, spacing=10, **kw)
        self.action = action
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel

        key = "restart_confirm" if action == "restart" else "quit_confirm"
        self.add_widget(Label(text=strings.t(key), font_name=FONT_NAME, font_size=16.0,
                              size_hint_y=None, height=60, halign="center", valign="middle"))

        row = BoxLayout(size_hint_y=None, height=52, spacing=10)
        self.btn_cancel = Button(text=strings.t("cancel"), font_name=FONT_NAME, font_size=15.0)
        self.btn_cancel.bind(on_release=lambda *_: self._cancel())
        self.btn_ok = Button(text=strings.t("confirm"), font_name=FONT_NAME, font_size=15.0)
        self.btn_ok.bind(on_release=lambda *_: self._confirm())
        row.add_widget(self.btn_cancel)
        row.add_widget(self.btn_ok)
        self.add_widget(row)

        self.apply_theme(palette("dark"))

    def _confirm(self) -> None:
        if self._on_confirm:
            self._on_confirm(self.action)

    def _cancel(self) -> None:
        if self._on_cancel:
            self._on_cancel()
