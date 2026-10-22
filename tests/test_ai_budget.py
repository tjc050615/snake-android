"""M4 前置：8ms 总预算（A* + 两级 BFS 共用 deadline）。"""

import time

from ai import safety
from ai.session import AISession
from app import constants as C
from core.chunk_manager import ChunkManager
from core.game import Game
from core.snake import DIR_RIGHT, Snake
from core.world import World


def test_level1_respects_deadline():
    world = World(1)
    world.ensure_chunk(0, 0)
    snake = Snake([(0, 0), (-1, 0), (-2, 0)], DIR_RIGHT)
    t0 = time.perf_counter()
    ok = safety.level1_reachable(world, snake, (30, 30), deadline=0.0)
    elapsed = (time.perf_counter() - t0) * 1000
    assert ok is False, "超时应保守拒绝"
    assert elapsed < 2.0, f"超时未生效：{elapsed:.2f}ms"


def test_level2_respects_deadline():
    world = World(1)
    world.ensure_chunk(0, 0)
    snake = Snake([(0, 0), (-1, 0), (-2, 0)], DIR_RIGHT)
    t0 = time.perf_counter()
    area = safety.level2_area(world, snake, (30, 30), limit=400, deadline=0.0)
    elapsed = (time.perf_counter() - t0) * 1000
    assert area >= 1
    assert elapsed < 2.0, f"超时未生效：{elapsed:.2f}ms"
    # 面积未达标 → 保守拒绝
    assert safety.level2_ok(world, snake, (30, 30), deadline=0.0) is False


def test_session_total_cost_peak_under_8ms():
    """1000 tick 的决策耗时 p99 必须 < 8ms（A* 与两级 BFS 共用预算）。"""
    game = Game(42)
    session = AISession()
    mgr = ChunkManager(game.world)
    costs = []

    for _ in range(1000):
        h = game.snake.head
        mgr.update((h[0] - 18, h[1] - 10, h[0] + 18, h[1] + 10))
        t0 = time.perf_counter()
        d = session.tick(game.world, game.snake, game.wrap_mode, 1.0)
        costs.append((time.perf_counter() - t0) * 1000)
        if d:
            game.set_direction(d)
        if game.update(C.TICK_INTERVAL).died:
            break

    costs.sort()
    p99 = costs[int(len(costs) * 0.99) - 1]
    print(f"[BUDGET] ticks={len(costs)} p50={costs[len(costs)//2]:.2f}ms p99={p99:.2f}ms max={costs[-1]:.2f}ms")
    assert p99 < 8.0, f"p99={p99:.2f}ms 超过 8ms 预算"
