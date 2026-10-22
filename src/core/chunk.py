"""chunk 数据记录（M1：只有食物；M2 增加障碍/墙壁字段）。"""

from __future__ import annotations

from dataclasses import dataclass, field

from app import constants as C


@dataclass
class Chunk:
    """一个 32×32 的预生成单元。M1 只保存食物。"""

    cx: int
    cy: int
    foods: list[tuple[int, int]] = field(default_factory=list)
    # 下一次"补充食物"使用的随机序号，保证同 seed 下补充结果确定（D-029）
    next_salt: int = 1

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
