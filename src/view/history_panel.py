"""历史 + 种子面板（M4/R2）。"""

from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from app import strings
from app.fonts import FONT_NAME


class HistoryPanel(BoxLayout):
    def __init__(self, profile: dict, current_seed: int, on_apply_seed, on_copy_seed, on_close=None, **kw) -> None:
        super().__init__(orientation="vertical", padding=10, spacing=6, **kw)
        self.profile = profile
        self._on_apply_seed = on_apply_seed
        self._on_copy_seed = on_copy_seed
        self._on_close = on_close

        header = BoxLayout(size_hint_y=None, height=44, spacing=6)
        header.add_widget(Label(text=strings.t("history"), font_name=FONT_NAME, font_size=18.0))
        btn_close = Button(text=strings.t("close"), font_name=FONT_NAME, font_size=14.0,
                           size_hint_x=None, width=90)
        btn_close.bind(on_release=lambda *_: self._close())
        header.add_widget(btn_close)
        self.add_widget(header)

        # 种子行
        seed_row = BoxLayout(size_hint_y=None, height=52, spacing=6)
        seed_row.add_widget(Label(text=strings.t("seed"), font_name=FONT_NAME, font_size=15.0,
                                  size_hint_x=None, width=60))
        # 种子只含 ASCII 数字：用默认字体（Noto OTF 在 TextInput 里不渲染，见 KI-024）
        self.txt_seed = TextInput(
            text=str(current_seed), multiline=False, font_size=16.0,
            foreground_color=(1, 1, 1, 1), background_color=(0.25, 0.27, 0.32, 1),
            cursor_color=(1, 1, 1, 1),
        )
        seed_row.add_widget(self.txt_seed)
        btn_apply = Button(text=strings.t("apply_seed"), font_name=FONT_NAME, font_size=14.0,
                           size_hint_x=None, width=80)
        btn_apply.bind(on_release=lambda *_: self._apply())
        seed_row.add_widget(btn_apply)
        btn_copy = Button(text=strings.t("copy_seed"), font_name=FONT_NAME, font_size=14.0,
                          size_hint_x=None, width=70)
        btn_copy.bind(on_release=lambda *_: self._copy())
        seed_row.add_widget(btn_copy)
        self.add_widget(seed_row)

        self.lbl_status = Label(text="", font_name=FONT_NAME, font_size=14.0, size_hint_y=None, height=26)
        self.add_widget(self.lbl_status)

        scroll = ScrollView(do_scroll_x=False)
        self.list = BoxLayout(orientation="vertical", spacing=2, size_hint_y=None)
        self.list.bind(minimum_height=self.list.setter("height"))
        scroll.add_widget(self.list)
        self.add_widget(scroll)

        self._render_history()

    # ---------- 列表 ----------
    def _render_history(self) -> None:
        self.list.clear_widgets()
        hist = self.profile.get("history", [])
        if not hist:
            self.list.add_widget(Label(text=strings.t("no_history"), font_name=FONT_NAME, font_size=14.0,
                                       size_hint_y=None, height=36))
            return
        for entry in reversed(hist):
            mode = strings.t("mode_ai") if entry.get("is_ai") else strings.t("mode_human")
            wrap = strings.t("wrap_on") if entry.get("wrap") else strings.t("wrap_off")
            text = f"{mode} {strings.t('score')} {entry.get('score')} {strings.t('seed')} {entry.get('seed')} {wrap}"
            self.list.add_widget(Label(text=text, font_name=FONT_NAME, font_size=14.0,
                                       size_hint_y=None, height=32, halign="left", valign="middle"))

    # ---------- 动作 ----------
    def _apply(self) -> None:
        from core.seed import parse_seed

        seed = parse_seed(self.txt_seed.text)
        if seed is None:
            self.lbl_status.text = strings.t("seed_invalid")
            return
        self.lbl_status.text = ""
        self._on_apply_seed(seed)

    def _copy(self) -> None:
        from core.seed import parse_seed

        seed = parse_seed(self.txt_seed.text)
        if seed is None:
            self.lbl_status.text = strings.t("seed_invalid")
            return
        self._on_copy_seed(seed)
        self.lbl_status.text = strings.t("seed_copied")

    def _close(self) -> None:
        if self._on_close is not None:
            self._on_close()
