"""设置覆盖层（M4/R1）：ScrollView + 逐项控件。

约束：
- 面板宽只有 30%（1280 下 384px），12+ 项必然溢出 → 必须可滚动
- 字体最大 24.0 时仍要能滚动访问所有项
- 所有文本走 strings.t；字号用数值（KI-019）
"""

from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox

from app import strings
from app.fonts import FONT_NAME
from app.theme import palette
from view.themed import ThemedMixin
from core.layout import content_height
from data.storage import PERF_MODES, THEMES

ROW_H = 56.0

# config key → strings key
LABEL_KEY = {
    "sound_on": "sound",
    "vibrate_on": "vibrate",
    "volume": "volume",
    "vibrate_strength": "vibrate_strength",
    "theme": "theme",
    "show_fps": "show_fps",
    "perf_mode": "perf_mode",
    "touch_sensitivity": "touch_sensitivity",
    "joystick_deadzone": "joystick_deadzone",
    "head_highlight": "head_highlight",
    "show_grid": "show_grid",
    "font_size": "font_size",
    "bg_mode": "bg",
    "bg_index": "bg_index",
    "view_scale": "view_scale",
}


class SettingsOverlay(ThemedMixin, BoxLayout):
    """右侧设置面板（覆盖层，与 GameCanvas 同级）。"""

    def __init__(self, cfg: dict, on_change, on_close=None, screen_awake: bool = True,
                 on_screen_awake=None, **kwargs) -> None:
        super().__init__(orientation="vertical", padding=10, spacing=6, **kwargs)
        self.cfg = dict(cfg)
        self._on_change = on_change
        self._on_close = on_close
        self._screen_awake = bool(screen_awake)
        self._on_screen_awake = on_screen_awake
        self._rows = 0

        header = BoxLayout(size_hint_y=None, height=44, spacing=6)
        self.lbl_title = Label(text=strings.t("settings"), font_name=FONT_NAME, font_size=self._fs(18))
        header.add_widget(self.lbl_title)
        btn_close = Button(text=strings.t("close"), font_name=FONT_NAME, font_size=self._fs(14), size_hint_x=None, width=90)
        btn_close.bind(on_release=lambda *_: self._close())
        header.add_widget(btn_close)
        self.add_widget(header)

        self.scroll = ScrollView(do_scroll_x=False)
        self.content = GridLayout(cols=1, spacing=4, size_hint_y=None)
        self.content.bind(minimum_height=self.content.setter("height"))
        self.scroll.add_widget(self.content)
        self.add_widget(self.scroll)

        self._build_rows()
        self._refresh_content_height()
        self.apply_theme(palette("dark"))

    # ---------- 工具 ----------
    def _fs(self, base: float) -> float:
        return max(12.0, min(24.0, base * self.cfg.get("font_size", 16.0) / 16.0))

    def _refresh_content_height(self) -> None:
        self.content.height = content_height(self._rows, self.cfg.get("font_size", 16.0))

    def _emit(self) -> None:
        self._refresh_content_height()
        self._on_change(dict(self.cfg))

    # ---------- 行 ----------
    def _row(self, label_key: str) -> BoxLayout:
        row = BoxLayout(size_hint_y=None, height=ROW_H, spacing=8)
        row.add_widget(
            Label(text=strings.t(LABEL_KEY.get(label_key, label_key)),
                  font_name=FONT_NAME, font_size=self._fs(15))
        )
        self._rows += 1
        self.content.add_widget(row)
        return row

    def _switch_row(self, key: str) -> None:
        # KI-023：不用 Kivy Switch（激活态贴图会显示成 NO），统一 CheckBox
        row = self._row(key)
        cb = CheckBox(active=bool(self.cfg.get(key)))
        cb.bind(active=lambda _w, v, k=key: self._set(k, bool(v)))
        row.add_widget(cb)

    def _slider_row(self, key: str, lo: float, hi: float) -> None:
        row = self._row(key)
        s = Slider(min=lo, max=hi, value=float(self.cfg.get(key, lo)))
        s.bind(value=lambda _w, v, k=key: self._set(k, round(float(v), 2)))
        row.add_widget(s)

    def _screen_awake_row(self) -> None:
        """屏幕常亮：状态存 profile（不是 config），实际效果 M5 用 pyjnius。"""
        row = self._row("screen_awake")
        cb = CheckBox(active=self._screen_awake)
        cb.bind(active=lambda _w, v: self._set_screen_awake(bool(v)))
        row.add_widget(cb)

    def _set_screen_awake(self, value: bool) -> None:
        self._screen_awake = value
        if self._on_screen_awake is not None:
            self._on_screen_awake(value)

    def _choice_row(self, key: str, values, label_map) -> None:
        row = self._row(key)
        sp = Spinner(
            text=label_map[self.cfg[key]], values=[label_map[v] for v in values],
            font_name=FONT_NAME, font_size=self._fs(14), size_hint_x=None, width=170,
        )
        back = {label_map[v]: v for v in values}

        def _pick(_w, text, k=key, b=back):
            self._set(k, b[text])

        sp.bind(text=_pick)
        row.add_widget(sp)

    def _build_rows(self) -> None:
        self._switch_row("sound_on")
        self._switch_row("vibrate_on")
        self._slider_row("volume", 0.0, 1.0)
        self._slider_row("vibrate_strength", 0.0, 1.0)
        self._choice_row(
            "theme", THEMES,
            {"dark": strings.t("theme_dark"), "light": strings.t("theme_light"),
             "high_contrast": strings.t("theme_high_contrast")},
        )
        self._choice_row("bg_mode", ("solid", "gradient"),
                         {"solid": strings.t("bg_solid"), "gradient": strings.t("bg_gradient")})
        self._slider_row("view_scale", 0.6, 2.0)
        self._choice_row("bg_index", tuple(range(16)), {i: str(i) for i in range(16)})
        self._switch_row("show_fps")
        self._choice_row(
            "perf_mode", PERF_MODES,
            {
                "battery": strings.t("perf_battery"),
                "balanced": strings.t("perf_balanced"),
                "performance": strings.t("perf_performance"),
            },
        )
        self._slider_row("touch_sensitivity", 0.5, 2.0)
        self._slider_row("joystick_deadzone", 0.05, 0.5)
        self._switch_row("head_highlight")
        self._switch_row("show_grid")
        self._screen_awake_row()
        self._slider_row("font_size", 12.0, 24.0)

        btn = Button(text=strings.t("reset_defaults"), font_name=FONT_NAME, font_size=self._fs(15),
                     size_hint_y=None, height=ROW_H)
        btn.bind(on_release=lambda *_: self._reset())
        self.content.add_widget(btn)
        self._rows += 1

    # ---------- 变更 ----------
    def _set(self, key: str, value) -> None:
        self.cfg[key] = value
        self._emit()

    def _reset(self) -> None:
        from data.storage import default_config

        self.cfg = default_config()
        self._emit()

    def _close(self) -> None:
        if self._on_close is not None:
            self._on_close()

    def scrollable_at_max_font(self) -> bool:
        """内容高度超过视口 → 必须可滚动（验收用）。"""
        return self.content.height > self.scroll.height
