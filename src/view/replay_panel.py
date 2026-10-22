"""回放播放器覆盖层（M4/R3）：暂停/继续 + 0.5x/1x/2x/4x，无后退。"""

from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from app import strings
from app.fonts import FONT_NAME
from app.theme import palette
from core.replay_controls import SPEEDS
from view.themed import ThemedMixin


class ReplayPanel(ThemedMixin, BoxLayout):
    def __init__(self, driver, on_close=None, **kw) -> None:
        super().__init__(orientation="vertical", padding=10, spacing=6, **kw)
        self.driver = driver
        self.controls = driver.controls
        self._on_close = on_close

        self.lbl = Label(text="", font_name=FONT_NAME, font_size=15.0,
                         size_hint_y=None, height=26)
        self.add_widget(self.lbl)

        row = BoxLayout(size_hint_y=None, height=48, spacing=6)
        self.btn_pause = Button(text=strings.t("play_pause"), font_name=FONT_NAME, font_size=14.0)
        self.btn_pause.bind(on_release=lambda *_: self._toggle())
        row.add_widget(self.btn_pause)

        self.speed_buttons = []
        for i, s in enumerate(SPEEDS):
            b = Button(text=f"{s:g}x", font_name=FONT_NAME, font_size=13.0)
            b.bind(on_release=lambda _w, idx=i: self._set_speed(idx))
            row.add_widget(b)
            self.speed_buttons.append(b)
        self.add_widget(row)

        btn_close = Button(text=strings.t("close"), font_name=FONT_NAME, font_size=14.0,
                           size_hint_y=None, height=44)
        btn_close.bind(on_release=lambda *_: self._on_close and self._on_close())
        self.add_widget(btn_close)

        self.apply_theme(palette("dark"))
        self.refresh()

    def _toggle(self) -> None:
        self.controls.toggle_pause()
        self.refresh()

    def _set_speed(self, idx: int) -> None:
        self.controls.speed_index = idx
        self.refresh()

    def refresh(self) -> None:
        state = strings.t("paused") if self.controls.paused else strings.t("playing")
        self.lbl.text = (f"{strings.t('replay')} {self.controls.tick}/{self.controls.total} "
                         f"{self.controls.speed:g}x {state}")
        self.btn_pause.text = strings.t("resume") if self.controls.paused else strings.t("play_pause")

    def advance(self, dt: float) -> int:
        n = self.driver.advance(dt)
        self.refresh()
        return n
