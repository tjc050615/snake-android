"""桌面平台适配（M1 只提供 density / 尺寸）。

M5 会新增 android.py，用 pyjnius 读 DisplayMetrics 与 WindowInsets；
业务代码只通过本包取值，禁止直接 import kivy 的 Window。
"""

from __future__ import annotations


def is_android() -> bool:
    try:
        from kivy.utils import platform as kivy_platform

        return kivy_platform == "android"
    except Exception:  # pragma: no cover - 无 kivy 环境（pytest）时
        return False


def get_density() -> float:
    """逻辑像素密度；无 kivy 时退回 1.0（纯逻辑测试用）。"""
    try:
        from kivy.metrics import Metrics

        density = float(Metrics.density)
        return density if density > 0 else 1.0
    except Exception:  # pragma: no cover
        return 1.0


def get_window_size() -> tuple[float, float]:
    try:
        from kivy.core.window import Window

        return (float(Window.width), float(Window.height))
    except Exception:  # pragma: no cover
        return (960.0, 540.0)
