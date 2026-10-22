"""AI 统计面板（M4/R3）：只读 AISession.stats，2Hz 刷新。"""

from __future__ import annotations

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from app import strings
from app.fonts import FONT_NAME
from data.ai_stats import FIELDS


class StatsPanel(BoxLayout):
    def __init__(self, session, on_close=None, **kw) -> None:
        super().__init__(orientation="vertical", padding=10, spacing=4, **kw)
        self.session = session
        header = BoxLayout(size_hint_y=None, height=40, spacing=6)
        header.add_widget(Label(text=strings.t("ai_stats"), font_name=FONT_NAME, font_size=18.0))
        btn = Button(text=strings.t("close"), font_name=FONT_NAME, font_size=14.0,
                     size_hint_x=None, width=90)
        btn.bind(on_release=lambda *_: on_close and on_close())
        header.add_widget(btn)
        self.add_widget(header)

        self.labels: dict[str, Label] = {}
        for key in FIELDS:
            lbl = Label(text="", font_name=FONT_NAME, font_size=14.0,
                        size_hint_y=None, height=26, halign="left", valign="middle")
            lbl.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
            self.add_widget(lbl)
            self.labels[key] = lbl

        self._event = Clock.schedule_interval(self.refresh, 0.5)  # 2Hz
        self.refresh()

    def refresh(self, _dt=None) -> None:
        stats = getattr(self.session, "stats", {}) if self.session is not None else {}
        for key, lbl in self.labels.items():
            value = stats.get(key, "-")
            if isinstance(value, float):
                value = f"{value:.2f}"
            lbl.text = f"{key}: {value}"

    def on_parent(self, _w, parent) -> None:
        if parent is None and getattr(self, "_event", None) is not None:
            self._event.cancel()
