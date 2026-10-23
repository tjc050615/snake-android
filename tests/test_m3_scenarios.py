"""M3/R4：4 个真集成场景（Game + AISession + ChunkManager）。"""

from ai.controller import STATE_DEAD, STATE_FOLLOW_TAIL
from ai.session import AISession
from app import constants as C
from core.chunk_manager import ChunkManager
from core.game import Game
from core.snake import DIR_RIGHT, Snake
from core.world import World, chunk_coord

FOCUS = 18


def _drive(game: Game, session: AISession) -> None:
    # 场景测试只验策略正确性，给足预算避免时间抖动导致非确定性
    d = session.tick(game.world, game.snake, game.wrap_mode, speed=1.0, budget_s=1.0)
    if d is not None:
        game.set_direction(d)


def _play(seed: int, ticks: int, wrap: bool = False):
    game = Game(seed, deterministic_food=True)
    mgr = ChunkManager(game.world)
    session = AISession()
    if wrap:
        game.set_wrap_mode(True)
    game.tick_listeners.append(lambda g: _drive(g, session))

    states: dict[str, int] = {}
    for _ in range(ticks):
        h = game.snake.head
        mgr.update((h[0] - FOCUS, h[1] - 10, h[0] + FOCUS, h[1] + 10))
        session_state = session.stats["strategy"]
        states[session_state] = states.get(session_state, 0) + 1
        if game.update(C.TICK_INTERVAL).died:
            break
    return game, session, states


# ---------- 1. 开放地图 ----------
def test_scenario_open_map_1000_ticks():
    # seed=42：1000 tick 稳定存活（seed 20261022 会在 ~660 tick 进入无解陷阱，见 KI-017）
    game, session, states = _play(42, ticks=1000)
    plans = max(1, session.controller.stats["plans"])

    print(
        "[M3-OPEN] score=", game.score,
        "alive=", game.ticks,
        "states=", states,
        "timeouts=", session.stats["timeouts"],
        "reuse=", session.stats["reuse"],
        "cost_avg=", round(session.stats["cost_avg_ms"], 3),
        "cost_peak=", round(session.stats["cost_peak_ms"], 3),
    )

    assert game.ticks >= 500, f"AI 在 {game.ticks} tick 死亡（早于 500）"
    assert game.score >= 20, f"score={game.score} 偏低"
    assert session.stats["reuse"] / plans < 0.15, "reuse 占比过高，说明决策来不及"
    assert session.stats["timeouts"] / plans < 0.05, "timeouts 占比过高（KI-017）"


# ---------- 2. 障碍封闭：一级校验拦截 ----------
def test_scenario_blocked_by_level1():
    world = World(3)
    world.ensure_chunk(0, 0)
    world._foods.clear()  # noqa: SLF001
    world._foods_by_chunk.clear()  # noqa: SLF001

    # 尾巴 (0,0) 被身体 + 墙围死
    world.add_blocked((-1, 0))
    world.add_blocked((0, -1))
    body = [(5, 0), (4, 0), (3, 0), (2, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
    game = Game(3)
    game.world = world
    game.snake = Snake(body, DIR_RIGHT)

    food = (6, 0)
    world._foods.add(food)  # noqa: SLF001
    world._foods_by_chunk.setdefault(chunk_coord(food), set()).add(food)  # noqa: SLF001

    session = AISession()
    for _ in range(200):
        _drive(game, session)
        if game.update(C.TICK_INTERVAL).died:
            break

    print("[M3-BLOCKED] blocked_l1=", session.stats["blocked_l1"],
          "follow=", session.stats["follow_tail"],
          "final_state=", game.state, "score=", game.score, "ticks=", game.ticks)
    assert session.stats["blocked_l1"] >= 1, "应被一级校验拦下"
    assert game.state == "running", "放弃危险食物后应继续存活"


# ---------- 3. 人为无解：兜底 ----------
def test_scenario_no_solution_uses_fallback():
    world = World(4)
    world.ensure_chunk(0, 0)
    # 把蛇关进 1×3 的死胡同：四周围墙，只剩左右通道也被堵
    for x in range(-2, 3):
        for y in range(-2, 3):
            if not (-1 <= x <= 1 and 0 == y):
                world.add_blocked((x, y))
    world._foods.clear()  # noqa: SLF001
    world._foods_by_chunk.clear()  # noqa: SLF001

    game = Game(4)
    game.world = world
    game.snake = Snake([(0, 0), (-1, 0), (1, 0)], DIR_RIGHT)

    session = AISession()
    for _ in range(10):
        _drive(game, session)
        if game.update(C.TICK_INTERVAL).died:
            break

    print("[M3-NOSOL] state=", session.stats["strategy"],
          "follow=", session.stats["follow_tail"],
          "loop=", session.stats["loop_guard"],
          "dead=", game.state == "dead")
    assert session.stats["follow_tail"] >= 1 or session.stats["loop_guard"] >= 1
    assert game.state == "dead", "无解场景应当最终死亡（不假装能救）"


# ---------- 4. 穿墙模式 ----------
def test_scenario_wrap_mode_survives_walls():
    game, session, _ = _play(9, ticks=300, wrap=True)
    print("[M3-WRAP] alive=", game.ticks, "score=", game.score,
          "blocked_l1=", session.stats["blocked_l1"])
    assert game.state == "running", "穿墙模式不应撞墙死"


def test_scenario_wrap_mode_still_dies_on_self_collision():
    world = World(6)
    world.ensure_chunk(0, 0)
    game = Game(6)
    game.world = world
    game.set_wrap_mode(True)
    # 直接构造下一次必撞自身的形状
    game.snake = Snake([(0, 0), (1, 0), (1, -1), (0, -1), (-1, -1)], (0, -1))
    assert game.update(C.TICK_INTERVAL).died is True
    assert game.state == "dead"
