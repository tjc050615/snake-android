"""成就 / 新手引导覆盖层（M4/R2）。"""

from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar

from app import strings
from app.fonts import FONT_NAME
from app.theme import palette
from view.themed import ThemedMixin
from data.achievements import ACHIEVEMENTS, label, progress
from data.onboarding import STEPS


class AchievementPanel(ThemedMixin, BoxLayout):
    def __init__(self, profile, stats, on_close=None, **kw) -> None:
        super().__init__(orientation="vertical", padding=10, spacing=6, **kw)
        self._on_close = on_close
        header = BoxLayout(size_hint_y=None, height=44, spacing=6)
        header.add_widget(Label(text=strings.t("achievements"), font_name=FONT_NAME, font_size=18.0))
        btn = Button(text=strings.t("close"), font_name=FONT_NAME, font_size=14.0,
                     size_hint_x=None, width=90)
        btn.bind(on_release=lambda *_: on_close and on_close())
        header.add_widget(btn)
        self.add_widget(header)

        prog = progress(profile, stats)
        unlocked = profile.get("achievements", {})
        for key, target in ACHIEVEMENTS:
            current, _ = prog[key]
            row = BoxLayout(orientation="vertical", size_hint_y=None, height=64, spacing=2)
            mark = "✓" if unlocked.get(key) else f"{current}/{target}"
            row.add_widget(Label(text=f"{label(key)}  {mark}", font_name=FONT_NAME, font_size=14.0,
                                 size_hint_y=None, height=24))
            bar = ProgressBar(max=target, value=current, size_hint_y=None, height=10)
            row.add_widget(bar)
            self.add_widget(row)
        self.apply_theme(palette("dark"))


class OnboardingPanel(ThemedMixin, BoxLayout):
    def __init__(self, on_finish=None, **kw) -> None:
        super().__init__(orientation="vertical", padding=12, spacing=8, **kw)
        self.step = 0
        self._on_finish = on_finish
        self.lbl_title = Label(text=strings.t("onboarding_title"), font_name=FONT_NAME, font_size=18.0,
                               size_hint_y=None, height=40)
        self.lbl_body = Label(text="", font_name=FONT_NAME, font_size=15.0)
        self.btn_next = Button(text=strings.t("onboarding_next"), font_name=FONT_NAME, font_size=15.0,
                               size_hint_y=None, height=48)
        self.btn_next.bind(on_release=lambda *_: self._next())
        self.add_widget(self.lbl_title)
        self.add_widget(self.lbl_body)
        self.add_widget(self.btn_next)
        self._render()
        self.apply_theme(palette("dark"))

    def _render(self) -> None:
        keys = ("onboarding_step1", "onboarding_step2", "onboarding_step3")
        self.lbl_body.text = strings.t(keys[self.step])

    def _next(self) -> None:
        self.step += 1
        if self.step >= STEPS:
            if self._on_finish:
                self._on_finish()
            return
        self._render()
