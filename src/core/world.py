"""无限世界（M2：稀疏哈希 + 全局阻挡索引）。

语义（D-054）：
- chunk 只是**预生成/渲染范围**，不是物理边界；世界逻辑无限。
- 未生成的区域按"无障碍、无食物、可通行"处理，走出已加载 chunk **不触发死亡**。

通行判定（M2 方案 B）：
- `is_passable(cell, ignore_blocked=False)`：
  - 默认查全局 `_blocked`（障碍 ∪ 墙壁），O(1)
  - `ignore_blocked=True` 时**只忽略地形阻挡**，蛇身由 Snake 自己查（穿墙模式）
"""

from __future__ import annotations

from core import gen
from core.chunk import Chunk
from app import constants as C

BLOCK_OBSTACLE = "obstacle"
BLOCK_WALL = "wall"


def chunk_coord(cell: tuple[int, int]) -> tuple[int, int]:
    """格坐标 → chunk 坐标（地板除，负坐标同样正确）。"""
    return (cell[0] // C.CHUNK_SIZE, cell[1] // C.CHUNK_SIZE)


class World:
    """无限网格世界。障碍/墙壁用全局集合索引，chunk 表只负责生成范围。"""

    def __init__(self, seed: int) -> None:
        self.seed = int(seed)
        self._chunks: dict[tuple[int, int], Chunk] = {}
        self._foods: set[tuple[int, int]] = set()
        # 障碍 ∪ 墙壁，通行判定的唯一索引（O(1) 查询）
        self._blocked: set[tuple[int, int]] = set()
        self._kinds: dict[tuple[int, int], str] = {}

    # ---------- 查询 ----------
    def has_chunk(self, cell: tuple[int, int]) -> bool:
        return chunk_coord(cell) in self._chunks

    def loaded_chunks(self) -> set[tuple[int, int]]:
        """已加载 chunk 的 key 集合（副本，供 ChunkManager 与调试面板用）。"""
        return set(self._chunks)

    # ---------- M3 AI 接口（只读，禁止 AI 直接碰 _blocked/_foods/_chunks） ----------
    def query_blocked_in_rect(
        self, x0: int, y0: int, x1: int, y1: int
    ) -> set[tuple[int, int]]:
        """返回矩形内所有阻挡格（障碍 + 墙壁）。含端点，坐标自动归一化。"""
        lo_x, hi_x = (x0, x1) if x0 <= x1 else (x1, x0)
        lo_y, hi_y = (y0, y1) if y0 <= y1 else (y1, y0)
        return {
            (x, y)
            for (x, y) in self._blocked
            if lo_x <= x <= hi_x and lo_y <= y <= hi_y
        }

    def foods_in_rect(self, x0: int, y0: int, x1: int, y1: int) -> set[tuple[int, int]]:
        """返回矩形内的食物格。含端点，坐标自动归一化。"""
        lo_x, hi_x = (x0, x1) if x0 <= x1 else (x1, x0)
        lo_y, hi_y = (y0, y1) if y0 <= y1 else (y1, y0)
        return {(x, y) for (x, y) in self._foods if lo_x <= x <= hi_x and lo_y <= y <= hi_y}

    def chunk_at(self, cell: tuple[int, int]) -> Chunk | None:
        return self._chunks.get(chunk_coord(cell))

    def is_passable(self, cell: tuple[int, int], ignore_blocked: bool = False) -> bool:
        """通行判定唯一入口（D-053 起 Snake 只调这里）。

        Args:
            cell: 目标格。
            ignore_blocked: 穿墙模式。**只让地形（障碍/墙壁）让路**：
                不忽略蛇身，也不忽略未来的特殊格子（陷阱/传送等）；
                蛇身碰撞由 `Snake.step` 用 `occupied` 独立判定。
        """
        if ignore_blocked:
            return True
        return cell not in self._blocked

    def is_blocked(self, cell: tuple[int, int]) -> bool:
        return cell in self._blocked

    def block_kind(self, cell: tuple[int, int]) -> str | None:
        return self._kinds.get(cell)

    def has_food(self, cell: tuple[int, int]) -> bool:
        return cell in self._foods

    def food_count(self) -> int:
        return len(self._foods)

    def foods(self) -> frozenset[tuple[int, int]]:
        return frozenset(self._foods)

    def blocked(self) -> frozenset[tuple[int, int]]:
        return frozenset(self._blocked)

    # ---------- 阻挡维护（R2/R3 由生成器调用） ----------
    def add_blocked(self, cell: tuple[int, int], kind: str = BLOCK_OBSTACLE) -> None:
        self._blocked.add(cell)
        self._kinds[cell] = kind

    def discard_blocked(self, cell: tuple[int, int]) -> None:
        self._blocked.discard(cell)
        self._kinds.pop(cell, None)

    # ---------- 预生成 ----------
    def ensure_chunk(self, cx: int, cy: int) -> Chunk:
        """按需实例化一个 chunk（幂等）。M2 由 ChunkManager 调用。

        生成顺序**写死**（顺序反了食物会落在障碍上）：
          ① 生成障碍
          ② 写入 World._blocked/_kinds 与 chunk.obstacles
          ③ 生成食物（用 is_passable 过滤，此时障碍已入索引）
          ④ 写入 chunk.foods / World._foods
        """
        key = (cx, cy)
        chunk = self._chunks.get(key)
        if chunk is not None:
            return chunk

        chunk = Chunk(cx=cx, cy=cy, foods=[])

        # ① + ② 障碍：先入全局索引，后续墙壁连通校验与食物过滤才能看到
        for cell in gen.chunk_obstacle_cells(self.seed, cx, cy):
            chunk.obstacles.add(cell)
            self.add_blocked(cell, BLOCK_OBSTACLE)

        # ②b 墙壁：障碍已在索引里，连通校验把障碍与墙一起算
        walls, degraded = gen.chunk_wall_cells(self.seed, cx, cy, set(chunk.obstacles))
        for cell in walls:
            chunk.walls.add(cell)
            self.add_blocked(cell, BLOCK_WALL)
        chunk.walls_degraded = degraded

        # ③ 食物候选（过滤阻挡格）
        wanted = gen.chunk_food_count(self.seed, cx, cy)
        accepted: list[tuple[int, int]] = []
        salt = 1
        while len(accepted) < wanted and salt < 1 + 4096:
            cell = gen.candidate_cell(self.seed, cx, cy, salt)
            salt += 1
            if cell in self._foods or cell in accepted:
                continue
            if not self.is_passable(cell):
                continue
            accepted.append(cell)

        # ④ 写入
        chunk.foods = sorted(accepted)
        for cell in chunk.foods:
            self._foods.add(cell)

        chunk.next_salt = max(salt, 1 + C.CHUNK_SIZE * C.CHUNK_SIZE)
        self._chunks[key] = chunk
        return chunk

    def ensure_chunk_at(self, cell: tuple[int, int]) -> Chunk:
        cx, cy = chunk_coord(cell)
        return self.ensure_chunk(cx, cy)

    def unload_chunk(self, cx: int, cy: int) -> None:
        """卸载 chunk：食物与阻挡索引一并移除，避免幽灵数据。"""
        chunk = self._chunks.pop((cx, cy), None)
        if chunk is None:
            return
        for cell in chunk.foods:
            self._foods.discard(cell)
        for cell in chunk.obstacles | chunk.walls:
            self.discard_blocked(cell)

    # ---------- 食物 ----------
    def consume_food(
        self,
        cell: tuple[int, int],
        occupied: frozenset[tuple[int, int]] = frozenset(),
    ) -> bool:
        """吃掉一个食物并**同 chunk 补充**（D-030）。返回是否真的吃到。"""
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
        """在同一个 chunk 内补一个食物，避开阻挡格与蛇身（D-030）。"""
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
