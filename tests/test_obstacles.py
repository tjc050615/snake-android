"""M2/R2：障碍生成（密度、确定性、出生保护、边界、食物避障、渲染前置）。"""

import time

import pytest

from app import constants as C
from core import gen
from core.chunk import Chunk
from core.game import STATE_DEAD, STATE_RUNNING, Game
from core.world import BLOCK_OBSTACLE, World

BOUNDARY = set(range(C.CHUNK_SIZE))


def _chunks(n=20, start=2):
    return [(start + i, start + (i % 3)) for i in range(n)]


# ---------- 结构：Chunk 不再暴露 blocked ----------
def test_chunk_has_no_blocked_property():
    assert not hasattr(Chunk(0, 0), "blocked")
    assert not hasattr(Chunk, "blocked")


# ---------- 密度 ----------
@pytest.mark.parametrize("cx,cy", _chunks(10))
def test_obstacle_density_in_range(cx, cy):
    n = len(gen.chunk_obstacle_cells(1, cx, cy))
    density = n / (C.CHUNK_SIZE * C.CHUNK_SIZE)
    assert 0.04 <= density <= 0.06, f"density={density:.4f}"


def test_obstacle_count_matches_density_formula():
    assert gen.chunk_obstacle_count(1, 5, 5) == round(0.05 * 32 * 32)


# ---------- 确定性 ----------
def test_obstacles_are_deterministic_per_chunk():
    a = gen.chunk_obstacle_cells(42, 3, -2)
    b = gen.chunk_obstacle_cells(42, 3, -2)
    assert a == b


def test_two_worlds_same_seed_same_obstacles():
    w1, w2 = World(99), World(99)
    for cx, cy in _chunks(6):
        w1.ensure_chunk(cx, cy)
        w2.ensure_chunk(cx, cy)
    assert w1.blocked() == w2.blocked()


def test_different_seed_differs():
    w1, w2 = World(1), World(2)
    for cx, cy in _chunks(4):
        w1.ensure_chunk(cx, cy)
        w2.ensure_chunk(cx, cy)
    assert w1.blocked() != w2.blocked()


# ---------- 出生保护 ----------
def test_spawn_protection_covers_9_chunks():
    for cx in (-1, 0, 1):
        for cy in (-1, 0, 1):
            assert gen.in_spawn_protection(cx, cy)
            assert gen.chunk_obstacle_cells(7, cx, cy) == []
            assert gen.chunk_obstacle_count(7, cx, cy) == 0
    assert not gen.in_spawn_protection(2, 0)
    assert not gen.in_spawn_protection(0, -2)


def test_spawn_chunks_have_zero_obstacles_in_world():
    world = World(7)
    for cx in (-1, 0, 1):
        for cy in (-1, 0, 1):
            world.ensure_chunk(cx, cy)
    assert world.blocked() == frozenset()


# ---------- 边界禁止 ----------
@pytest.mark.parametrize("cx,cy", _chunks(8))
def test_boundary_rows_and_cols_have_no_obstacles(cx, cy):
    for x, y in gen.chunk_obstacle_cells(3, cx, cy):
        lx, ly = x - cx * C.CHUNK_SIZE, y - cy * C.CHUNK_SIZE
        assert lx != 0 and lx != C.CHUNK_SIZE - 1
        assert ly != 0 and ly != C.CHUNK_SIZE - 1


# ---------- 食物避障 ----------
@pytest.mark.parametrize("cx,cy", _chunks(8))
def test_food_never_on_obstacle(cx, cy):
    world = World(11)
    world.ensure_chunk(cx, cy)
    chunk = world.chunk_at((cx * C.CHUNK_SIZE, cy * C.CHUNK_SIZE))
    for cell in chunk.foods:
        assert cell not in chunk.obstacles
        assert world.is_passable(cell) is True


def test_food_count_still_in_range_with_obstacles():
    """全局食物上限 5 后：单 chunk 可能为 0，总量不得超 5。"""
    world = World(11)
    world.ensure_chunk(0, 0)
    count = world.food_count()
    assert 0 <= count <= 5

def test_obstacle_kills_without_wrap_mode():
    game = Game(5)
    game.world.add_blocked((1, 0), BLOCK_OBSTACLE)
    assert game.update(C.TICK_INTERVAL).died is True
    assert game.state == STATE_DEAD


def test_obstacle_is_passable_with_wrap_mode():
    game = Game(5)
    game.world.add_blocked((1, 0), BLOCK_OBSTACLE)
    game.set_wrap_mode(True)
    assert game.update(C.TICK_INTERVAL).died is False
    assert game.state == STATE_RUNNING
    assert game.snake.head == (1, 0)


# ---------- 性能 ----------
def test_single_chunk_generation_under_3ms():
    world = World(2024)
    latencies = []
    for i in range(100):
        cx, cy = 10 + i, -10 - i
        t0 = time.perf_counter()
        world.ensure_chunk(cx, cy)
        latencies.append((time.perf_counter() - t0) * 1000)

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95) - 1]
    assert p95 <= 3.0, f"p95={p95:.3f}ms"


# ---------- 连通性 ----------
def _flood_count(passable: set, start) -> int:
    seen = {start}
    stack = [start]
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (x + dx, y + dy)
            if nxt in passable and nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return len(seen)


def test_connectivity_100_seeds_10_chunks():
    """100 个种子 × 10 个 chunk：每个 chunk 内所有可通行格必须连通。"""
    for seed in range(100):
        world = World(seed)
        for cx, cy in _chunks(10, start=2):
            world.ensure_chunk(cx, cy)
            x0, y0 = cx * C.CHUNK_SIZE, cy * C.CHUNK_SIZE
            passable = {
                (x, y)
                for x in range(x0, x0 + C.CHUNK_SIZE)
                for y in range(y0, y0 + C.CHUNK_SIZE)
                if world.is_passable((x, y))
            }
            reachable = _flood_count(passable, (x0, y0))
            assert reachable == len(passable), (
                f"seed={seed} chunk=({cx},{cy}) 连通 {reachable}/{len(passable)}"
            )
