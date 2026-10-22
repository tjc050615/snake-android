"""M2/R4：ChunkManager 加载/卸载、食物补充、内存与确定性。"""

import tracemalloc

import pytest

from app import constants as C
from core.chunk_manager import ChunkManager
from core.world import World, chunk_coord


def _rect_at_chunk(cx: int, cy: int, size: int = C.CHUNK_SIZE) -> tuple[int, int, int, int]:
    """构造"恰好覆盖 1 个 chunk"的视口矩形（含端点）。"""
    x0, y0 = cx * C.CHUNK_SIZE, cy * C.CHUNK_SIZE
    return (x0, y0, x0 + size - 1, y0 + size - 1)


def _walk(mgr: ChunkManager, steps: int = 200, start=(0, 0)):
    """沿 +x 走 steps 格，每格推进一次 manager（模拟每帧）。"""
    x, y = start
    for _ in range(steps):
        x += 1
        cx, cy = chunk_coord((x, y))
        mgr.update(_rect_at_chunk(cx, cy))


# ---------- 加载数量 ----------
def test_loaded_chunk_count_after_200_cells():
    world = World(20261022)
    mgr = ChunkManager(world)
    _walk(mgr)
    # 视口 1 个 chunk + 2 圈 → 5×5 = 25
    assert 20 <= mgr.loaded_count() <= 30, mgr.loaded_count()


def test_chunk_count_is_stable_while_walking():
    world = World(7)
    mgr = ChunkManager(world)
    _walk(mgr, steps=50)
    first = mgr.loaded_count()
    _walk(mgr, steps=100, start=(50, 0))
    assert mgr.loaded_count() == first


# ---------- 卸载 ----------
def test_far_chunks_are_unloaded():
    world = World(11)
    mgr = ChunkManager(world)
    _walk(mgr, steps=200)

    loaded = world.loaded_chunks()
    head_cx = 200 // C.CHUNK_SIZE
    for cx, cy in loaded:
        assert abs(cx - head_cx) <= C.CHUNK_UNLOAD_RINGS + 1
        assert abs(cy) <= C.CHUNK_UNLOAD_RINGS + 1

    assert (0, 0) not in loaded, "原点 chunk 应已卸载"


def test_unload_drops_food_and_blocked():
    world = World(12)
    world.ensure_chunk(3, 3)
    chunk = world.chunk_at((3 * C.CHUNK_SIZE, 3 * C.CHUNK_SIZE))
    assert chunk.foods
    blocked_before = set(chunk.obstacles | chunk.walls)

    world.unload_chunk(3, 3)

    assert world.has_chunk((3 * C.CHUNK_SIZE, 3 * C.CHUNK_SIZE)) is False
    for cell in chunk.foods:
        assert world.has_food(cell) is False
    for cell in blocked_before:
        assert world.is_passable(cell) is True


# ---------- 未加载区域 ----------
def test_walking_out_of_loaded_region_is_safe():
    world = World(5)
    world.ensure_chunk_at((0, 0))
    far = (5000, 5000)
    assert world.is_passable(far) is True
    assert world.has_chunk(far) is False


# ---------- 食物补充 ----------
def test_refill_avoids_blocked_and_keeps_count():
    world = World(21)
    world.ensure_chunk(2, 2)
    chunk = world.chunk_at((2 * C.CHUNK_SIZE, 2 * C.CHUNK_SIZE))
    before = len(chunk.foods)
    assert C.FOOD_PER_CHUNK_MIN <= before <= C.FOOD_PER_CHUNK_MAX

    for _ in range(5):
        cell = sorted(chunk.foods)[0]
        assert world.consume_food(cell) is True
        assert C.FOOD_PER_CHUNK_MIN <= len(chunk.foods) <= C.FOOD_PER_CHUNK_MAX
        for food in chunk.foods:
            assert world.is_passable(food) is True
            assert food not in world.blocked()


def test_refill_respects_next_salt_sequence():
    """补充位置由 next_salt 递增决定 → 同种子同消费顺序结果一致。"""
    w1, w2 = World(33), World(33)
    for w in (w1, w2):
        w.ensure_chunk(4, 4)
        chunk = w.chunk_at((4 * C.CHUNK_SIZE, 4 * C.CHUNK_SIZE))
        for _ in range(3):
            w.consume_food(sorted(chunk.foods)[0])
    assert w1.foods() == w2.foods()


# ---------- 确定性 ----------
def test_same_path_same_world():
    results = []
    for _ in range(2):
        world = World(101)
        mgr = ChunkManager(world)
        _walk(mgr, steps=120)
        results.append((world.loaded_chunks(), world.blocked(), world.foods()))
    assert results[0] == results[1]


# ---------- 内存 ----------
def test_memory_under_50mb_after_200_cells():
    tracemalloc.start()
    world = World(2026)
    mgr = ChunkManager(world)
    _walk(mgr, steps=200)
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak / (1024 * 1024)
    assert peak_mb < 50.0, f"peak={peak_mb:.2f}MB"
    assert 20 <= mgr.loaded_count() <= 30


# ---------- M3 接口 ----------
def test_rect_queries_for_ai():
    world = World(8)
    world.ensure_chunk(2, 2)
    x0, y0 = 2 * C.CHUNK_SIZE, 2 * C.CHUNK_SIZE
    rect = (x0, y0, x0 + C.CHUNK_SIZE - 1, y0 + C.CHUNK_SIZE - 1)

    blocked = world.query_blocked_in_rect(*rect)
    foods = world.foods_in_rect(*rect)
    assert blocked == {c for c in world.blocked() if x0 <= c[0] <= rect[2] and y0 <= c[1] <= rect[3]}
    assert foods == {c for c in world.foods() if x0 <= c[0] <= rect[2] and y0 <= c[1] <= rect[3]}


def test_rect_queries_normalize_reversed_bounds():
    world = World(8)
    world.ensure_chunk(2, 2)
    a = world.foods_in_rect(100, 100, 60, 60)
    b = world.foods_in_rect(60, 60, 100, 100)
    assert a == b
