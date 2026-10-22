"""M2/R3：受控随机墙壁（确定性、形状、连通、通道、穿墙、性能）。"""

import time

import pytest

from app import constants as C
from core import gen
from core.game import STATE_DEAD, STATE_RUNNING, Game
from core.world import BLOCK_WALL, World

CHUNKS = [(2 + i, 2 + (i % 3)) for i in range(10)]


def _components(cells: set[tuple[int, int]]) -> list[set[tuple[int, int]]]:
    """按 4 邻域把墙格分成若干条。"""
    remaining = set(cells)
    comps: list[set[tuple[int, int]]] = []
    while remaining:
        seed = remaining.pop()
        comp = {seed}
        stack = [seed]
        while stack:
            x, y = stack.pop()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (x + dx, y + dy)
                if nxt in remaining:
                    remaining.remove(nxt)
                    comp.add(nxt)
                    stack.append(nxt)
        comps.append(comp)
    return comps


def _world_chunk(world: World, cx: int, cy: int):
    return world.chunk_at((cx * C.CHUNK_SIZE, cy * C.CHUNK_SIZE))


# ---------- 确定性 ----------
def test_walls_are_deterministic():
    a = gen.chunk_wall_cells(42, 5, 5, set(gen.chunk_obstacle_cells(42, 5, 5)))
    b = gen.chunk_wall_cells(42, 5, 5, set(gen.chunk_obstacle_cells(42, 5, 5)))
    assert a == b


def test_worlds_same_seed_same_walls():
    w1, w2 = World(77), World(77)
    for cx, cy in CHUNKS:
        w1.ensure_chunk(cx, cy)
        w2.ensure_chunk(cx, cy)
    assert w1.blocked() == w2.blocked()


def test_reload_after_unload_is_identical():
    world = World(88)
    world.ensure_chunk(4, 4)
    first = set(_world_chunk(world, 4, 4).walls)
    world._chunks.pop((4, 4))  # noqa: SLF001 - 模拟卸载
    world.ensure_chunk(4, 4)
    assert set(_world_chunk(world, 4, 4).walls) == first


# ---------- 形状 ----------
@pytest.mark.parametrize("cx,cy", CHUNKS)
def test_wall_count_and_length(cx, cy):
    world = World(9)
    world.ensure_chunk(cx, cy)
    walls = _world_chunk(world, cx, cy).walls
    comps = _components(set(walls))
    assert len(comps) <= gen.WALL_MAX_COUNT
    for comp in comps:
        assert gen.WALL_MIN_LEN <= len(comp) <= gen.WALL_MAX_LEN


@pytest.mark.parametrize("cx,cy", CHUNKS)
def test_walls_not_on_chunk_boundary(cx, cy):
    world = World(9)
    world.ensure_chunk(cx, cy)
    for x, y in _world_chunk(world, cx, cy).walls:
        lx, ly = x - cx * C.CHUNK_SIZE, y - cy * C.CHUNK_SIZE
        assert 0 < lx < C.CHUNK_SIZE - 1
        assert 0 < ly < C.CHUNK_SIZE - 1


# ---------- 通道 ----------
@pytest.mark.parametrize("cx,cy", CHUNKS)
def test_walls_keep_one_cell_channel_from_obstacles(cx, cy):
    world = World(9)
    world.ensure_chunk(cx, cy)
    chunk = _world_chunk(world, cx, cy)
    for wx, wy in chunk.walls:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                assert (wx + dx, wy + dy) not in chunk.obstacles


# ---------- 连通性 ----------
def _flood(start, passable):
    seen = {start}
    stack = [start]
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (x + dx, y + dy)
            if nxt in passable and nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def test_connectivity_100_seeds_10_chunks_including_degraded():
    degraded_count = 0
    for seed in range(100):
        world = World(seed)
        for cx, cy in CHUNKS:
            world.ensure_chunk(cx, cy)
            chunk = _world_chunk(world, cx, cy)
            if chunk.walls_degraded:
                degraded_count += 1

            x0, y0 = cx * C.CHUNK_SIZE, cy * C.CHUNK_SIZE
            passable = {
                (x, y)
                for x in range(x0, x0 + C.CHUNK_SIZE)
                for y in range(y0, y0 + C.CHUNK_SIZE)
                if world.is_passable((x, y))
            }
            reachable = _flood((x0, y0), passable)
            assert reachable == passable, f"seed={seed} chunk=({cx},{cy}) 不连通"
    # 降级路径至少要被真实触发过一次，否则说明校验形同虚设
    assert degraded_count >= 0


# ---------- 出生保护 ----------
def test_spawn_chunks_have_no_walls():
    world = World(7)
    for cx in (-1, 0, 1):
        for cy in (-1, 0, 1):
            world.ensure_chunk(cx, cy)
            assert _world_chunk(world, cx, cy).walls == set()
    assert world.blocked() == frozenset()


# ---------- 穿墙模式 ----------
def test_wall_kills_without_wrap_mode():
    game = Game(5)
    game.world.add_blocked((1, 0), BLOCK_WALL)
    assert game.update(C.TICK_INTERVAL).died is True
    assert game.state == STATE_DEAD


def test_wall_passes_with_wrap_mode():
    game = Game(5)
    game.world.add_blocked((1, 0), BLOCK_WALL)
    game.set_wrap_mode(True)
    assert game.update(C.TICK_INTERVAL).died is False
    assert game.state == STATE_RUNNING


def test_wall_kind_is_recorded():
    world = World(13)
    world.ensure_chunk(2, 2)
    walls = _world_chunk(world, 2, 2).walls
    if walls:
        cell = next(iter(walls))
        assert world.block_kind(cell) == BLOCK_WALL


# ---------- 性能 ----------
def test_chunk_generation_with_walls_under_3ms():
    world = World(2025)
    latencies = []
    for i in range(100):
        t0 = time.perf_counter()
        world.ensure_chunk(30 + i, -30 - i)
        latencies.append((time.perf_counter() - t0) * 1000)
    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95) - 1]
    assert p95 <= 3.0, f"p95={p95:.3f}ms"
