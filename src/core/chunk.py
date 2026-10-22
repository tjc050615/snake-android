"""chunk 数据记录（M2：食物 + 障碍 + 墙壁）。

分开存 obstacles / walls 而不是合成一个 set：
- 穿墙模式（D-025）只忽略"阻挡"，但仍要知道哪些格是墙（渲染/语义/未来 AI）；
- 渲染层需要区分两者的绘制样式；
- 连通性校验只关心"是否阻挡"，由 World._blocked 提供 O(1) 查询。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app import constants as C


@dataclass
class Chunk:
    """一个 32×32 的预生成单元。"""

    cx: int
    cy: int
    foods: list[tuple[int, int]] = field(default_factory=list)
    obstacles: set[tuple[int, int]] = field(default_factory=set)
    walls: set[tuple[int, int]] = field(default_factory=set)
    # 下一次"补充食物"使用的随机序号，保证同 seed 下补充结果确定（D-029）
    next_salt: int = 1
    # 墙壁是否因连通校验失败而降级为"只生成障碍"（D-027）
    walls_degraded: bool = False

    @property
    def key(self) -> tuple[int, int]:
        return (self.cx, self.cy)

    @property
    def origin(self) -> tuple[int, int]:
        return (self.cx * C.CHUNK_SIZE, self.cy * C.CHUNK_SIZE)

    def bounds(self) -> tuple[int, int, int, int]:
        """返回 (x0, y0, x1, y1)，x1 / y1 为开区间。"""
        x0, y0 = self.origin
        return (x0, y0, x0 + C.CHUNK_SIZE, y0 + C.CHUNK_SIZE)

    def contains(self, cell: tuple[int, int]) -> bool:
        x0, y0, x1, y1 = self.bounds()
        return x0 <= cell[0] < x1 and y0 <= cell[1] < y1
