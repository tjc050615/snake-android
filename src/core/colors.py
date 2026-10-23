"""背景与蛇身颜色（模块二）：16 纯色 + 16 渐变 + HSV 蛇身渐变。"""

from __future__ import annotations

import colorsys

SOLIDS = (
    "#0b0e14", "#12161f", "#1b1f2a", "#232838", "#2b3040", "#343a4c", "#3d4457", "#4a5165",
    "#1a2b1f", "#2b3a1a", "#3a2f1a", "#3a1f1f", "#2f1a3a", "#1a2f3a", "#101820", "#000000",
)

GRADIENTS = (
    ("#0b0e14", "#1b2a4a"), ("#12161f", "#2b3a5c"), ("#000000", "#2a0a3a"), ("#001018", "#003a4a"),
    ("#0a0014", "#3a0050"), ("#001a0a", "#004a20"), ("#1a0a00", "#4a2a00"), ("#0a0a0a", "#3a3a3a"),
    ("#2a0a0a", "#0a0a2a"), ("#0a2a2a", "#2a0a2a"), ("#141414", "#2c3e50"), ("#0f2027", "#2c5364"),
    ("#232526", "#414345"), ("#1e130c", "#9a8478"), ("#000428", "#004e92"), ("#0f0c29", "#302b63"),
)


def _hex(c: str):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def background_color(index: int) -> tuple[float, float, float]:
    """纯色按 index 取（0~15）。"""
    return _hex(SOLIDS[index % len(SOLIDS)])


def gradient_pair(index: int):
    a, b = GRADIENTS[index % len(GRADIENTS)]
    return _hex(a), _hex(b)


def snake_gradient(length: int, hue_offset: float = 0.0) -> list[tuple[float, float, float]]:
    """0~255 色环平滑渐变：整条蛇按 index 取色，头亮尾暗。"""
    out = []
    for i in range(max(1, length)):
        t = i / max(1, length - 1) if length > 1 else 0.0
        hue = (hue_offset + t) % 1.0
        rgb = colorsys.hsv_to_rgb(hue, 0.65, 1.0 - 0.45 * t)  # 尾部压暗
        out.append(rgb)
    return out


def background_name(mode: str, index: int) -> str:
    from app.strings import GRADIENT_NAMES, SOLID_NAMES

    table = GRADIENT_NAMES if mode == "gradient" else SOLID_NAMES
    return table[int(index) % 16]
