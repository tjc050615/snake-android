"""单 chunk 预生成（M1-2 / M1-15 / M1-16）：空网格 + 食物 3~5。"""

import pytest

from app import constants as C
from core import gen
from core.world import World, chunk_coord

CHUNKS = [(0, 0), (1, 0), (-1, -1), (5, -3), (-2, 4)]


@pytest.mark.parametrize("cx,cy", CHUNKS)
def test_food_count_in_range(cx, cy):
    n = gen.chunk_food_count(seed=1, cx=cx, cy=cy)
    assert C.FOOD_PER_CHUNK_MIN <= n <= C.FOOD_PER_CHUNK_MAX


@pytest.mark.parametrize("cx,cy", CHUNKS)
def test_food_cells_in_bounds_unique_sorted(cx, cy):
    cells = gen.chunk_food_cells(seed=42, cx=cx, cy=cy)
    assert len(cells) == gen.chunk_food_count(seed=42, cx=cx, cy=cy)
    assert len(set(cells)) == len(cells), "食物不能重叠"
    assert cells == sorted(cells), "输出需稳定排序"

    x0, y0 = cx * C.CHUNK_SIZE, cy * C.CHUNK_SIZE
    x1, y1 = x0 + C.CHUNK_SIZE, y0 + C.CHUNK_SIZE
    for x, y in cells:
        assert x0 <= x < x1
        assert y0 <= y < y1


def test_generation_is_pure_function():
    a = gen.chunk_food_cells(seed=7, cx=2, cy=3)
    b = gen.chunk_food_cells(seed=7, cx=2, cy=3)
    assert a == b


def test_two_worlds_same_seed_identical():
    w1, w2 = World(seed=99), World(seed=99)
    w1.ensure_chunk_at((0, 0))
    w2.ensure_chunk_at((0, 0))
    assert w1.foods() == w2.foods()


def test_different_seed_produces_different_world():
    w1, w2 = World(seed=1), World(seed=2)
    for cx, cy in CHUNKS:
        w1.ensure_chunk(cx, cy)
        w2.ensure_chunk(cx, cy)
    assert w1.foods() != w2.foods()


def test_consume_food_refills_same_chunk():
    """M1-15：吃掉后同 chunk 补充，总数不变。"""
    world = World(seed=5)
    world.ensure_chunk_at((0, 0))
    before = world.foods()
    eaten = sorted(before)[0]

    assert world.consume_food(eaten) is True

    after = world.foods()
    assert eaten not in after
    assert len(after) == len(before)

    new_cells = after - (before - {eaten})
    assert len(new_cells) == 1, "每次吃只补一个"
    nx, ny = next(iter(new_cells))
    assert chunk_coord((nx, ny)) == chunk_coord(eaten), "补充必须落在同一 chunk"


def test_consume_non_food_returns_false():
    world = World(seed=5)
    world.ensure_chunk_at((0, 0))
    assert world.consume_food((1000, 1000)) is False


def test_consume_avoids_occupied_cells():
    world = World(seed=11)
    world.ensure_chunk_at((0, 0))
    occupied = frozenset(world.foods())
    eaten = sorted(occupied)[0]
    assert world.consume_food(eaten, occupied=occupied) is True
    assert world.foods() - occupied != set()


def test_m1_has_no_walls_or_obstacles():
    """D-053：M1 全可通行。"""
    world = World(seed=3)
    world.ensure_chunk_at((0, 0))
    for x in range(C.CHUNK_SIZE):
        for y in range(C.CHUNK_SIZE):
            assert world.is_passable((x, y)) is True
