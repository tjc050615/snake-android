"""M3 前置：三种中文按钮方案实验（不影响游戏逻辑）。

用法： python tools/button_probe.py A|B|C [out.png]
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
os.environ.setdefault("KIVY_NO_FILELOG", "1")
os.environ.setdefault("KIVY_HOME", os.path.join(ROOT, ".kivyhome"))
os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.app import App  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.uix.behaviors import ButtonBehavior  # noqa: E402
from kivy.uix.button import Button  # noqa: E402
from kivy.uix.floatlayout import FloatLayout  # noqa: E402
from kivy.uix.label import Label  # noqa: E402

from app.fonts import FONT_NAME, register_fonts  # noqa: E402

VARIANT = sys.argv[1] if len(sys.argv) > 1 else "A"
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "docs", "evidence", f"btn_{VARIANT}.png")


class ProbeApp(App):
    def build(self):
        register_fonts()
        Window.size = (480, 200)
        root = FloatLayout()
        text = "穿墙: 关"

        if VARIANT == "A":
            w = Button(text=text, size_hint=(None, None), size=(220, 64),
                       pos_hint={"center_x": 0.5, "center_y": 0.5}, font_name=FONT_NAME)
        elif VARIANT == "B":
            class Btn(ButtonBehavior, Label):
                pass

            w = Btn(text=text, size_hint=(None, None), size=(220, 64),
                    pos_hint={"center_x": 0.5, "center_y": 0.5}, font_name=FONT_NAME)
        else:
            w = Button(text=text, markup=True, size_hint=(None, None), size=(220, 64),
                       pos_hint={"center_x": 0.5, "center_y": 0.5}, font_name=FONT_NAME)

        root.add_widget(w)
        Clock.schedule_once(lambda _dt: self._shot(), 0.8)
        Clock.schedule_once(lambda _dt: self.stop(), 1.4)
        return root

    def _shot(self):
        path = Window.screenshot(name=OUT)
        print("SHOT", os.path.basename(str(path)))


ProbeApp().run()
