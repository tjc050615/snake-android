"""KI-011：矩形查询分桶后的性能与语义一致性。"""

import time

from app import constants as C
from core.chunk_manager import ChunkManager
from core.world import World, chunk_coord


def _load_ring(world: World, cx: int, cy: int, rings: int = 3) -> None:
    for dx in range(-rings, rings + 1):
        for dy in range(-rings, rings + 1):
            world.ensure_chunk(cx + dx, cy + dy)


def test_rect_queries_match_full_scan():
    world = World(2026)
    _load_ring(world, 5, 5, rings=3)

    rect = (5 * C.CHUNK_SIZE - 10, 5 * C.CHUNK_SIZE - 10, 5 * C.CHUNK_SIZE + 40, 5 * C.CHUNK_SIZE + 40)
    x0, y0, x1, y1 = rect

    blocked = world.query_blocked_in_rect(*rect)
    foods = world.foods_in_rect(*rect)

    expect_blocked = {c for c in world.blocked() if x0 <= c[0] <= x1 and y0 <= c[1] <= y1}
    expect_foods = {c for c in world.foods() if x0 <= c[0] <= x1 and y0 <= c[1] <= y1}
    assert blocked == expect_blocked
    assert foods == expect_foods
    assert blocked, "用例应至少命中一个阻挡格"


def test_buckets_follow_unload():
    world = World(11)
    world.ensure_chunk(3, 3)
    before = world.query_blocked_in_rect(3 * C.CHUNK_SIZE, 3 * C.CHUNK_SIZE,
                                         3 * C.CHUNK_SIZE + 31, 3 * C.CHUNK_SIZE + 31)
    assert before
    world.unload_chunk(3, 3)
    after = world.query_blocked_in_rect(3 * C.CHUNK_SIZE, 3 * C.CHUNK_SIZE,
                                        3 * C.CHUNK_SIZE + 31, 3 * C.CHUNK_SIZE + 31)
    assert after == set()


def test_buckets_follow_refill():
    world = World(21)
    world.ensure_chunk(2, 2)
    chunk = world.chunk_at((2 * C.CHUNK_SIZE, 2 * C.CHUNK_SIZE))
    eaten = sorted(chunk.foods)[0]
    world.consume_food(eaten)

    rect = (2 * C.CHUNK_SIZE, 2 * C.CHUNK_SIZE,
            2 * C.CHUNK_SIZE + 31, 2 * C.CHUNK_SIZE + 31)
    assert eaten not in world.foods_in_rect(*rect)
    assert world.foods_in_rect(*rect) == set(chunk.foods)


def test_rect_query_perf_under_05ms_with_42_chunks():
    """42 个 chunk（约 2500 个阻挡格）下，矩形查询 p95 < 0.5ms。"""
    world = World(20261022)
    mgr = ChunkManager(world)
    # 构造 42 个已加载 chunk：视口跨 2×1 chunk + 2 圈预加载 + 3 圈卸载
    mgr.update((0, -10, 60, 10))
    for _ in range(80):
        mgr.update((100, -10, 160, 10))
    assert 30 <= len(world.loaded_chunks()) <= 45

    rect = (100 - 20, -10, 100 + 20, 10)
    latencies = []
    for _ in range(200):
        t0 = time.perf_counter()
        world.query_blocked_in_rect(*rect)
        world.foods_in_rect(*rect)
        latencies.append((time.perf_counter() - t0) * 1000)

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95) - 1]
    assert p95 < 0.5, f"p95={p95:.4f}ms"
