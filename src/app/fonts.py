"""中文字体注册。

Kivy 默认字体 Roboto 不含中文，必须随包带字体，不能依赖系统字体。
字体文件放在 `assets/fonts/` 并进 git。
"""

from __future__ import annotations

import os

FONT_NAME = "SnakeCJK"
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_CANDIDATES = (
    os.path.join(_ROOT, "assets", "fonts", "NotoSansSC-Regular.otf"),
    os.path.join(_ROOT, "assets", "fonts", "DroidSansFallback.ttf"),
    os.path.join(_ROOT, "assets", "fonts", "ChineseFallback.ttf"),
)

_registered: str | None = None


def font_path() -> str | None:
    for path in _CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def register_fonts() -> str | None:
    """注册随包字体；返回实际使用的路径，找不到返回 None（调用方退回默认字体）。

    kivy 在函数内才 import：让"字体文件是否存在"这类检查能在无 Kivy 环境跑。
    """
    global _registered
    if _registered is not None:
        return _registered
    path = font_path()
    if path is None:
        return None
    from kivy.core.text import LabelBase  # noqa: PLC0415

    LabelBase.register(name=FONT_NAME, fn_regular=path)
    _registered = path
    return path


def font_name() -> str | None:
    """CoreLabel/Label 用的 font_name；未注册时返回 None 让 Kivy 用默认字体。"""
    if _registered is not None:
        return FONT_NAME
    return FONT_NAME if register_fonts() else None
