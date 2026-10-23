"""网格平铺纹理（R5C 渲染降载）：整屏网格 1 个 draw call。"""

from __future__ import annotations

from kivy.graphics.texture import Texture

_TEX: Texture | None = None


def grid_texture() -> Texture:
    global _TEX
    if _TEX is not None:
        return _TEX
    size = 16
    buf = bytearray(size * size * 4)
    for y in range(size):
        for x in range(size):
            i = (y * size + x) * 4
            on_line = (x == 0) or (y == 0)
            v = 255 if on_line else 0
            buf[i:i + 4] = bytes((v, v, v, 255 if on_line else 0))
    tex = Texture.create(size=(size, size))
    tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
    tex.wrap = "repeat"
    tex.mag_filter = "nearest"
    tex.min_filter = "nearest"
    _TEX = tex
    return tex


def grid_tex_coords(origin_x: float, origin_y: float, grid_size: float,
                    width: float, height: float):
    """按相机偏移对齐瓷砖，返回 Rectangle 的 tex_coords。"""
    g = max(1.0, float(grid_size))
    ox = (origin_x % g) / g
    oy = (origin_y % g) / g
    u1 = ox + width / g
    v1 = oy + height / g
    # Rectangle 需要 8 个值（4 个角）
    return (ox, oy, u1, oy, u1, v1, ox, v1)
