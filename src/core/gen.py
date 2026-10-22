"""地形/食物生成（纯函数，D-029 / D-053）。

M1 范围（D-053）：只生成
  1) 32×32 空网格（全可通行，无墙无障碍）
  2) 每 chunk 3~5 个食物，只落在可通行格

M2 才引入：障碍 5%、受控随机墙、出生保护。
所有函数不得持有状态，不得 import kivy。
"""

from __future__ import annotations

from app import constants as C
from core import rng


def chunk_food_count(seed: int, cx: int, cy: int) -> int:
    """每 chunk 食物数量：3~5（D-030），由 chunk 哈希决定，稳定可复现。"""
    span = C.FOOD_PER_CHUNK_MAX - C.FOOD_PER_CHUNK_MIN + 1
    return C.FOOD_PER_CHUNK_MIN + rng.chunk_hash(seed, cx, cy, salt=0x1) % span


def candidate_cell(seed: int, cx: int, cy: int, salt: int) -> tuple[int, int]:
    """第 salt 个候选格：落在该 chunk 内部（M1 全可通行）。"""
    h = rng.chunk_hash(seed, cx, cy, salt=salt)
    x = cx * C.CHUNK_SIZE + (h % C.CHUNK_SIZE)
    y = cy * C.CHUNK_SIZE + ((h >> 32) % C.CHUNK_SIZE)
    return (x, y)


def chunk_food_cells(
    seed: int,
    cx: int,
    cy: int,
    count: int | None = None,
    salt_start: int = 1,
) -> list[tuple[int, int]]:
    """生成该 chunk 的食物格列表（去重、按坐标排序）。

    count 为 None 时用 chunk_food_count；salt_start 让"补充食物"从新序号继续，
    保证补充结果依然确定（D-029）。
    """
    need = chunk_food_count(seed, cx, cy) if count is None else count
    cells: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    salt = salt_start
    # 上限保护：极端情况下也不会死循环
    while len(cells) < need and salt < salt_start + 4096:
        cell = candidate_cell(seed, cx, cy, salt)
        salt += 1
        if cell in seen:
            continue
        seen.add(cell)
        cells.append(cell)
    cells.sort()
    return cells


def is_passable(cell: tuple[int, int]) -> bool:  # noqa: ARG001
    """M1：所有格可通行（无墙无障碍）。M2 会按地形重写。"""
    return True
