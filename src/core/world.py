"""无限世界（M1：稀疏哈希 + 按需预生成 chunk）。

关键语义（D-054）：
- chunk 只是**预生成/渲染范围**，不是物理边界。
- 世界逻辑无限：任何坐标都可通行；未生成的区域按"无障碍、无食物"处理，
  蛇走出已生成 chunk **不触发死亡**。M2 才由 ChunkManager 按圈数加载。
"""

from __future__ import annotations

from core import gen
from core.chunk import Chunk
from app import constants as C


def chunk_coord(cell: tuple[int, int]) -> tuple[int, int]:
    """格坐标 → chunk 坐标（地板除，负坐标同样正确）。"""
    return (cell[0] // C.CHUNK_SIZE, cell[1] // C.CHUNK_SIZE)


class World:
    """无限网格世界。食物用稀疏集合存，pytest 可直接构造。"""

    def __init__(self, seed: int) -> None:
        self.seed = int(seed)
        self._chunks: dict[tuple[int, int], Chunk] = {}
        self._foods: set[tuple[int, int]] = set()

    # ---------- 查询 ----------
    def has_chunk(self, cell: tuple[int, int]) -> bool:
        return chunk_coord(cell) in self._chunks

    def is_passable(self, cell: tuple[int, int]) -> bool:
        """M1：全图可通行（D-053 / D-054）。M2 接入地形表。"""
        return gen.is_passable(cell)

    def has_food(self, cell: tuple[int, int]) -> bool:
        return cell in self._foods

    def food_count(self) -> int:
        return len(self._foods)

    def foods(self) -> frozenset[tuple[int, int]]:
        return frozenset(self._foods)

    # ---------- 预生成 ----------
    def ensure_chunk(self, cx: int, cy: int) -> Chunk:
        """按需实例化一个 chunk（幂等）。M1 只被调用一次（原点 chunk）。"""
        key = (cx, cy)
        chunk = self._chunks.get(key)
        if chunk is not None:
            return chunk
        chunk = Chunk(cx=cx, cy=cy, foods=[])
        for cell in gen.chunk_food_cells(self.seed, cx, cy):
            if not self.is_passable(cell):
                continue
            chunk.foods.append(cell)
            self._foods.add(cell)
        # 补充食物的取点序号从 chunk 容量之后开始，避免与初始食物重合
        chunk.next_salt = 1 + C.CHUNK_SIZE * C.CHUNK_SIZE
        self._chunks[key] = chunk
        return chunk

    def ensure_chunk_at(self, cell: tuple[int, int]) -> Chunk:
        cx, cy = chunk_coord(cell)
        return self.ensure_chunk(cx, cy)

    # ---------- 食物 ----------
    def consume_food(
        self,
        cell: tuple[int, int],
        occupied: frozenset[tuple[int, int]] = frozenset(),
    ) -> bool:
        """吃掉一个食物并**同 chunk 补充**（D-030）。返回是否真的吃到。

        occupied 用于补充时避开蛇身（M1 无蛇时为默认空集）。
        """
        if cell not in self._foods:
            return False
        self._foods.discard(cell)
        cx, cy = chunk_coord(cell)
        chunk = self._chunks.get((cx, cy))
        if chunk is not None and cell in chunk.foods:
            chunk.foods.remove(cell)
            self._refill(chunk, occupied)
        return True

    def _refill(self, chunk: Chunk, occupied: frozenset[tuple[int, int]]) -> None:
        """在同一个 chunk 内补一个食物，取点序号单调递增 → 结果确定。"""
        for _ in range(4096):
            cell = gen.candidate_cell(self.seed, chunk.cx, chunk.cy, chunk.next_salt)
            chunk.next_salt += 1
            if cell in self._foods or cell in occupied:
                continue
            if not self.is_passable(cell):
                continue
            chunk.foods.append(cell)
            chunk.foods.sort()
            self._foods.add(cell)
            return
