"""真·平滑渐变背景（模块二修正）：生成纵向渐变纹理，一次铺满全屏。

不再用两段矩形拼接（会出横线）。256 行逐行插值，GPU 线性过滤拉伸到任意尺寸。
"""

from __future__ import annotations

from kivy.graphics.texture import Texture

from core.colors import gradient_pair

_CACHE: dict[int, Texture] = {}
H = 2   # 只用两端颜色，GPU 线性过滤拉伸 → 无 banding
W = 2


def gradient_texture(index: int) -> Texture:
    index = int(index) % 16
    tex = _CACHE.get(index)
    if tex is not None:
        return tex

    top, bottom = gradient_pair(index)
    buf = bytearray(W * H * 4)
    for y, c in enumerate((top, bottom)):
        row = bytes((int(round(c[0] * 255)), int(round(c[1] * 255)),
                     int(round(c[2] * 255)), 255)) * W
        buf[y * W * 4:(y + 1) * W * 4] = row

    tex = Texture.create(size=(W, H))
    tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
    tex.mag_filter = "linear"
    tex.min_filter = "linear"
    tex.wrap = "clamp_to_edge"
    _CACHE[index] = tex
    return tex
