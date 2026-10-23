"""沉浸式 UI（模块二修正）：悬浮菜单按钮 + 半透明侧边栏 + 遮罩。"""

from __future__ import annotations

from kivy.uix.button import Button
from kivy.uix.widget import Widget

from app import strings
from app.fonts import FONT_NAME


class MenuButton(Button):
    """右上角悬浮「菜单」按钮。"""

    def __init__(self, on_toggle=None, **kw) -> None:
        kw.setdefault("text", strings.t("menu"))
        kw.setdefault("font_name", FONT_NAME)
        kw.setdefault("font_size", 15.0)
        kw.setdefault("size_hint", (None, None))
        kw.setdefault("size", (88, 42))
        super().__init__(**kw)
        if on_toggle is not None:
            self.bind(on_release=lambda *_: on_toggle())


class Scrim(Widget):
    """打开菜单时的半透明遮罩：点空白处关闭。"""

    def __init__(self, on_tap=None, **kw) -> None:
        super().__init__(**kw)
        self._on_tap = on_tap
        self.visible = False

    def show(self, visible: bool) -> None:
        self.visible = visible
        self.opacity = 1.0 if visible else 0.0
        self.disabled = not visible

    def on_touch_down(self, touch) -> bool:
        if not self.visible or not self.collide_point(*touch.pos):
            return False
        if self._on_tap is not None:
            self._on_tap()
        return True
