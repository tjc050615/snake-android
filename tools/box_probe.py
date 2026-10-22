"""探针：BoxLayout 里的 Button 中文渲染。"""

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
from kivy.uix.boxlayout import BoxLayout  # noqa: E402
from kivy.uix.button import Button  # noqa: E402
from kivy.uix.floatlayout import FloatLayout  # noqa: E402
from kivy.uix.label import Label  # noqa: E402

from app.fonts import FONT_NAME, register_fonts  # noqa: E402


class Probe(App):
    def build(self):
        register_fonts()
        Window.size = (640, 360)
        root = FloatLayout()
        box = BoxLayout(orientation="vertical", size_hint=(0.3, 1), pos_hint={"right": 1})
        box.add_widget(Label(text="得分7 abc123", font_name=FONT_NAME, size_hint_y=None, height=48))
        box.add_widget(Button(text="穿墙关", font_name=FONT_NAME, size_hint_y=None, height=56))
        box.add_widget(Button(text="重新开始", font_name=FONT_NAME, size_hint_y=None, height=56))
        box.add_widget(Label(text="", size_hint_y=1))
        root.add_widget(box)
        Clock.schedule_once(lambda _dt: self._shot(), 0.8)
        Clock.schedule_once(lambda _dt: self.stop(), 1.4)
        return root

    def _shot(self):
        path = Window.screenshot(name=os.path.join(ROOT, "docs", "evidence", "boxprobe.png"))
        print("SHOT", os.path.basename(str(path)))


Probe().run()
