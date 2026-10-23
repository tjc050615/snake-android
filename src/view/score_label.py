"""常驻计分板：得分 + 长度。"""

from __future__ import annotations

from kivy.uix.label import Label

from app import strings
from app.fonts import FONT_NAME


class ScoreLabel(Label):
    def __init__(self, **kw) -> None:
        kw.setdefault("font_name", FONT_NAME)
        kw.setdefault("font_size", 18.0)
        kw.setdefault("color", (1, 1, 1, 1))
        kw.setdefault("size_hint", (None, None))
        kw.setdefault("size", (260, 30))
        kw.setdefault("halign", "left")
        kw.setdefault("valign", "middle")
        super().__init__(text="", **kw)
        self.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        self.update_score(0, 3)

    def update_score(self, score: int, length: int) -> None:
        self.text = f"{strings.t('score')}: {score} | {strings.t('length')}: {length}"
