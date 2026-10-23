"""右侧 30% 面板（M4/R1）：分数 / 穿墙开关 / 重开。

按钮一律 `Button(font_name=FONT_NAME)`，且面板与 GameCanvas 同级（覆盖层），
避免被 canvas.clear() 连带清掉（KI-012）。
"""

from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from app import strings
from app.fonts import FONT_NAME
from app.theme import palette
from view.themed import ThemedMixin


class Panel(ThemedMixin, BoxLayout):
    def __init__(self, game, on_wrap=None, on_restart=None, on_settings=None,
                 on_history=None, on_achievements=None, on_stats=None,
                 on_ai=None, on_speed=None, on_ai_stats=None, **kwargs) -> None:
        super().__init__(orientation="vertical", padding=12, spacing=10, **kwargs)
        self.game = game
        self._on_wrap = on_wrap
        self._on_restart = on_restart
        self._on_settings = on_settings
        self._on_history = on_history
        self._on_achievements = on_achievements
        self._on_stats = on_stats
        self._on_ai = on_ai
        self._on_speed = on_speed

        self.lbl_score = Label(
            text="", font_name=FONT_NAME, font_size=20.0,
            size_hint_y=None, height=48, halign="center", valign="middle",
        )
        self.lbl_score.bind(size=lambda w, *_: setattr(w, "text_size", w.size))

        self.btn_wrap = Button(
            text="", font_name=FONT_NAME, font_size=16.0,
            size_hint_y=None, height=56,
        )
        self.btn_wrap.bind(on_release=lambda *_: self._wrap())

        self.btn_restart = Button(
            text=strings.t("restart"), font_name=FONT_NAME, font_size=16.0,
            size_hint_y=None, height=56,
        )
        self.btn_restart.bind(on_release=lambda *_: self._restart())

        self.btn_settings = Button(
            text=strings.t("settings"), font_name=FONT_NAME, font_size=16.0,
            size_hint_y=None, height=56,
        )
        self.btn_settings.bind(on_release=lambda *_: self._settings())

        self.btn_history = Button(
            text="", font_name=FONT_NAME, font_size=16.0,
            size_hint_y=None, height=56,
        )
        self.btn_history.bind(on_release=lambda *_: self._history())

        self.add_widget(self.lbl_score)
        self.add_widget(self.btn_wrap)
        self.add_widget(self.btn_restart)
        self.add_widget(self.btn_history)
        self.btn_ach = Button(text='', font_name=FONT_NAME, font_size=16.0,
                              size_hint_y=None, height=56)
        self.btn_ach.bind(on_release=lambda *_: self._achievements())
        self.btn_stats = Button(text='', font_name=FONT_NAME, font_size=16.0,
                               size_hint_y=None, height=56)
        self.btn_stats.bind(on_release=lambda *_: self._stats())
        self.add_widget(self.btn_ach)
        self.add_widget(self.btn_stats)
        self.btn_ai = Button(text='', font_name=FONT_NAME, font_size=16.0,
                             size_hint_y=None, height=56)
        self.btn_ai.bind(on_release=lambda *_: self._ai())
        self.speed_row = BoxLayout(size_hint_y=None, height=56, spacing=4)
        self.speed_buttons = {}
        for _v in (1.0, 2.0, 4.0):
            b = Button(text=f"{_v:g}x", font_name=FONT_NAME, font_size=14.0)
            b.bind(on_release=lambda _w, v=_v: self._set_speed(v))
            self.speed_row.add_widget(b)
            self.speed_buttons[_v] = b
        self.add_widget(self.btn_ai)
        self.add_widget(self.speed_row)
        self.add_widget(self.btn_settings)
        self.add_widget(Label(text="", size_hint_y=1))  # 弹性占位

        self.refresh()
        self.apply_theme(palette("dark"))

    # ---------- 刷新 ----------
    def refresh(self) -> None:
        self.lbl_score.text = f"{strings.t('score')} {self.game.score}"
        self.btn_wrap.text = strings.t("wrap_on" if self.game.wrap_mode else "wrap_off")
        self.btn_history.text = strings.t("history")
        self.btn_ach.text = strings.t("achievements")
        try:
            self.lbl_score.text = (f"{strings.t('score')} {self.game.score}\n"
                                   f"{strings.t('best')} {getattr(self, 'best_human', 0)}"
                                   f"/{getattr(self, 'best_ai', 0)}")
        except Exception:
            pass
        self.btn_stats.text = strings.t("ai_stats")
        self.btn_ai.text = strings.t("ai_off") if getattr(self, "ai_active", False) else strings.t("ai_on")
        current = getattr(self, "speed", 1.0)
        for v, b in getattr(self, "speed_buttons", {}).items():
            b.background_color = ((0.25, 0.55, 0.95, 1) if abs(v - current) < 1e-6
                                  else (0.22, 0.24, 0.29, 1))

    # ---------- 事件 ----------
    def _wrap(self) -> None:
        if self._on_wrap is not None:
            self._on_wrap()
        self.refresh()

    def _restart(self) -> None:
        if self._on_restart is not None:
            self._on_restart()
        self.refresh()

    def _settings(self) -> None:
        if self._on_settings is not None:
            self._on_settings()

    def _history(self) -> None:
        if self._on_history is not None:
            self._on_history()

    def _achievements(self) -> None:
        if self._on_achievements is not None:
            self._on_achievements()

    def _ai(self) -> None:
        if self._on_ai is not None:
            self._on_ai()
        self.refresh()

    def _speed(self) -> None:
        if self._on_speed is not None:
            self._on_speed()
        self.refresh()

    def _tap(self) -> None:
        """UI 点击震动钩子（未接线时安全 no-op）。"""
        cb = getattr(self, "_on_tap", None)
        if cb is not None:
            cb()

    def _set_speed(self, value: float) -> None:
        self._tap()
        if self._on_speed is not None:
            self._on_speed(value)
        self.refresh()

    def _stats(self) -> None:
        if self._on_stats is not None:
            self._on_stats()

    # ---------- 触控隔离 ----------
    def on_touch_down(self, touch) -> bool:
        if not self.collide_point(*touch.pos):
            return False
        super().on_touch_down(touch)  # 让按钮自己处理
        return True                    # 消费掉，绝不让事件漏到游戏区

    def on_touch_move(self, touch) -> bool:
        if not self.collide_point(*touch.pos):
            return False
        super().on_touch_move(touch)
        return True

    def on_touch_up(self, touch) -> bool:
        if not self.collide_point(*touch.pos):
            return False
        super().on_touch_up(touch)
        return True
