"""ChunkManager（M2/R4）：按视口圈数加载/卸载 chunk。

规则（D-005）：
- 预加载：视口覆盖的 chunk + 向外 `preload_rings` 圈
- 卸载：超出视口 + `unload_rings` 圈的 chunk（比预加载多一圈，形成滞回带）
- 同帧最多生成 `max_generate_per_update` 个 chunk（默认 1，避免生成尖峰）

只依赖 World 的公开方法，不直接碰 `_chunks`。
"""

from __future__ import annotations

from app import constants as C
from core.world import World, chunk_coord


def _chunk_span(rect: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """格矩形（含端点）→ 覆盖的 chunk 坐标范围（含端点）。"""
    x0, y0, x1, y1 = rect
    cx0, cy0 = chunk_coord((x0, y0))
    cx1, cy1 = chunk_coord((x1, y1))
    return (cx0, cy0, cx1, cy1)


class ChunkManager:
    def __init__(
        self,
        world: World,
        preload_rings: int = C.CHUNK_PRELOAD_RINGS,
        unload_rings: int = C.CHUNK_UNLOAD_RINGS,
        max_generate_per_update: int = 1,
        initial_rect: tuple[int, int, int, int] | None = None,
    ) -> None:
        self.world = world
        self.preload_rings = max(0, int(preload_rings))
        self.unload_rings = max(self.preload_rings, int(unload_rings))
        self.max_generate_per_update = max(1, int(max_generate_per_update))
        if initial_rect is not None:
            for _ in range(256):
                self.update(initial_rect)
                if self.desired(initial_rect) <= set(self.world.loaded_chunks()):
                    break

    # ---------- 目标集合 ----------
    def desired(self, rect: tuple[int, int, int, int]) -> set[tuple[int, int]]:
        cx0, cy0, cx1, cy1 = _chunk_span(rect)
        r = self.preload_rings
        return {
            (cx, cy)
            for cx in range(cx0 - r, cx1 + r + 1)
            for cy in range(cy0 - r, cy1 + r + 1)
        }

    def keep(self, rect: tuple[int, int, int, int]) -> set[tuple[int, int]]:
        cx0, cy0, cx1, cy1 = _chunk_span(rect)
        r = self.unload_rings
        return {
            (cx, cy)
            for cx in range(cx0 - r, cx1 + r + 1)
            for cy in range(cy0 - r, cy1 + r + 1)
        }

    # ---------- 更新 ----------
    def update(self, rect: tuple[int, int, int, int]) -> int:
        """按视口矩形推进加载/卸载，返回本帧新生成的 chunk 数。"""
        keep = self.keep(rect)
        self._unload_outside(keep)

        need = sorted(self.desired(rect) - self.world.loaded_chunks())
        generated = 0
        for cx, cy in need:
            if generated >= self.max_generate_per_update:
                break
            self.world.ensure_chunk(cx, cy)
            generated += 1
        return generated

    def _unload_outside(self, keep: set[tuple[int, int]]) -> None:
        for key in list(self.world.loaded_chunks()):
            if key not in keep:
                self.world.unload_chunk(key[0], key[1])

    # ---------- 查询 ----------
    def loaded_count(self) -> int:
        return len(self.world.loaded_chunks())
