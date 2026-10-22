"""M3/R3：8ms 超时降级、决策同步、高速档、路径时间戳、统计、障碍场景基线。"""

import time

import pytest

from ai import search
from ai.controller import AIController
from ai.session import AISession
from app import constants as C
from core.chunk_manager import ChunkManager
from core.game import Game
from core.world import World


def _open_game(seed=20261022):
    game = Game(seed)
    mgr = ChunkManager(game.world)
    for _ in range(4):
        h = game.snake.head
        mgr.update((h[0] - 18, h[1] - 10, h[0] + 18, h[1] + 10))
    return game, mgr


# ---------- 超时 ----------
def test_astar_deadline_returns_best_effort_deterministically():
    rect = (-60, -60, 60, 60)
    d = 0.0  # 立刻到期
    a = search.astar((-60, -60), (60, 60), lambda c: True, rect, deadline=d)
    b = search.astar((-60, -60), (60, 60), lambda c: True, rect, deadline=d)
    assert a == b, "超时中断必须确定性"
    assert len(a) < 120, "超时应返回部分路径而不是完整最长路径"


def test_timeout_marks_state_and_falls_back():
    game, _ = _open_game()
    ai = AIController()
    d = ai.decide(game.world, game.snake, timeout_s=1e-9)
    # 超时后仍要给出一个通过 O(1) 校验的方向（除非真的无路）
    if d is not None:
        assert ai.safe_step(game.world, game.snake, d)


# ---------- 决策同步 ----------
def test_session_applies_direction_on_next_tick():
    game, mgr = _open_game()
    ai = AISession()
    d1 = ai.tick(game.world, game.snake)
    # 第一次 tick 可能只是算完缓存，方向下一 tick 才生效
    d2 = ai.tick(game.world, game.snake)
    assert d1 is not None or d2 is not None
    assert ai.stats["alive_ticks"] == 2


def test_decision_applies_to_current_step():
    """KI-016 定为方案 B：本 tick 计算的方向作用于本次 step；
    真正的"下一步生效"由 Snake.pending 保证（set_direction 只写 pending）。"""
    game, _ = _open_game()
    ai = AISession()
    d1 = ai.tick(game.world, game.snake)
    assert d1 is not None, "第一 tick 就应有可用方向"
    assert ai.path_tick == ai.ticks
    if d1 is not None:
        assert game.snake.set_direction(d1) in (True, False)


def test_session_reuses_last_direction_without_plan(monkeypatch):
    game, _ = _open_game()
    ai = AISession()
    ai.last_direction = (1, 0)
    monkeypatch.setattr(ai.controller, "plan", lambda *a, **k: [])
    d = ai.tick(game.world, game.snake)
    assert d is not None
    assert ai.stats["reuse"] >= 1


def test_high_speed_decides_every_two_ticks():
    game, _ = _open_game()
    ai = AISession()
    plans = []
    for i in range(6):
        ai.tick(game.world, game.snake, speed=10.0)
        plans.append(ai.controller.stats["plans"])
    # 6 个 tick、period=2 → 决策 3 次
    assert plans[-1] - plans[0] >= 2
    assert ai.period == 2
    assert ai.timeout_s <= 0.004
    assert ai.controller.radius_cap == 40


def test_normal_speed_decides_every_tick():
    game, _ = _open_game()
    ai = AISession()
    for _ in range(4):
        ai.tick(game.world, game.snake, speed=1.0)
    assert ai.period == 1
    assert ai.controller.radius_cap == 80


# ---------- 路径时间戳 ----------
def test_path_tick_must_match():
    game, _ = _open_game()
    ai = AISession()
    ai.tick(game.world, game.snake)
    if ai.path:
        assert ai.current_path(ai.path_tick) == ai.path
        assert ai.current_path(ai.path_tick - 1) == []


def test_path_cells_inside_loaded_rect():
    game, _ = _open_game()
    ai = AISession()
    ai.tick(game.world, game.snake)
    loaded = game.world.loaded_rect()
    for cell in ai.path:
        assert loaded[0] <= cell[0] <= loaded[2]
        assert loaded[1] <= cell[1] <= loaded[3]


# ---------- 统计 ----------
def test_stats_fields_complete():
    game, _ = _open_game()
    ai = AISession()
    ai.tick(game.world, game.snake)
    for key in (
        "strategy", "nodes", "cost_avg_ms", "cost_peak_ms", "alive_ticks",
        "eaten", "blocked_l1", "blocked_l2", "follow_tail", "loop_guard",
        "timeouts", "reuse",
    ):
        assert key in ai.stats


# ---------- 障碍场景基线（KI-015） ----------
def _dense_world(seed=7):
    world = World(seed)
    world.ensure_chunk(0, 0)
    # 棋盘格柱子：blocked 当且仅当 x、y 都为偶数 → 密集但保持连通
    for x in range(-32, 32):
        for y in range(-32, 32):
            if x % 2 == 0 and y % 2 == 0:
                world.add_blocked((x, y))
    return world


def test_astar_baseline_with_dense_obstacles_p95_under_8ms():
    world = _dense_world()
    start = (-31, -31)   # (x+y) % 4 == 2 → 可通行
    goal = (31, 31)
    rect = (-32, -32, 32, 32)
    blocked = world.blocked()

    def passable(c):
        return c not in blocked

    latencies = []
    for _ in range(30):
        t0 = time.perf_counter()
        path = search.astar(start, goal, passable, rect, max_nodes=20000)
        latencies.append((time.perf_counter() - t0) * 1000)
        assert path and path[-1] == goal

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95) - 1]
    print(f"[BASELINE] dense obstacle A* p50={latencies[len(latencies)//2]:.2f}ms p95={p95:.2f}ms max={latencies[-1]:.2f}ms")
    assert p95 < 8.0, f"p95={p95:.2f}ms"
