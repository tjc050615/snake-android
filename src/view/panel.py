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


class Panel(BoxLayout):
    def __init__(self, game, on_wrap=None, on_restart=None, on_settings=None, **kwargs) -> None:
        super().__init__(orientation="vertical", padding=12, spacing=10, **kwargs)
        self.game = game
        self._on_wrap = on_wrap
        self._on_restart = on_restart
        self._on_settings = on_settings

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

        self.add_widget(self.lbl_score)
        self.add_widget(self.btn_wrap)
        self.add_widget(self.btn_restart)
        self.add_widget(self.btn_settings)
        self.add_widget(Label(text="", size_hint_y=1))  # 弹性占位

        self.refresh()

    # ---------- 刷新 ----------
    def refresh(self) -> None:
        self.lbl_score.text = f"{strings.t('score')} {self.game.score}"
        self.btn_wrap.text = strings.t("wrap_on" if self.game.wrap_mode else "wrap_off")

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
