"""M3/R2：两级安全校验、跟尾兜底、防循环、穿墙模式、三处标注。"""

import os
from collections import deque

from ai import safety
from ai.controller import STATE_FOLLOW_TAIL, AIController
from app import strings
from core.game import Game
from core.snake import DIR_DOWN, DIR_RIGHT, Snake
from core.world import World

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _pocket_world(size: int = 1) -> World:
    """构造一个只有中心 (2*size+1)^2 口袋可通行的世界。"""
    world = World(1)
    half = size
    for x in range(-half - 2, half + 3):
        for y in range(-half - 2, half + 3):
            inside = -half <= x <= half and -half <= y <= half
            if not inside:
                world.add_blocked((x, y))
    world.ensure_chunk(0, 0)
    return world


# ---------- 两级校验单元 ----------
def test_level1_blocks_when_tail_unreachable():
    """蛇尾被身体 + 墙完全围死时，一级校验必须拒绝。"""
    world = World(1)
    world.ensure_chunk(0, 0)
    # 尾巴 (0,0)：右 (1,0)、上 (0,1) 是身体，左 (-1,0)、下 (0,-1) 是墙
    world.add_blocked((-1, 0))
    world.add_blocked((0, -1))
    body = [(5, 0), (4, 0), (3, 0), (2, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
    snake = Snake(body, DIR_RIGHT)

    assert safety.level1_reachable(world, snake, (6, 0)) is False


def test_level2_blocks_in_small_pocket():
    world = _pocket_world(size=1)  # 3×3 = 9 格
    body = [(0, 0), (-1, 0), (0, -1)]
    snake = Snake(body, DIR_RIGHT)
    assert len(snake) == 3
    # 面积最多 9 - 3 = 6，小于 蛇长+10 = 13 → 拒绝
    assert safety.level2_area(world, snake, (1, 1)) <= 6
    assert safety.level2_ok(world, snake, (1, 1)) is False


def test_level2_accepts_in_open_area():
    world = World(1)
    world.ensure_chunk(0, 0)
    snake = Snake([(0, 0), (-1, 0), (-2, 0)], DIR_RIGHT)
    assert safety.level2_ok(world, snake, (3, 0)) is True


def test_wrap_mode_ignores_terrain_but_keeps_body():
    world = _pocket_world(size=1)
    snake = Snake([(0, 0), (-1, 0), (-2, 0)], DIR_RIGHT)
    # 普通模式：口袋外是墙
    assert safety.level2_area(world, snake, (1, 1)) <= 9
    # 穿墙模式：忽略墙，面积变大
    assert safety.level2_area(world, snake, (1, 1), wrap_mode=True) > 9


# ---------- 控制器集成 ----------
def test_unsafe_food_falls_back_to_follow_tail():
    world = _pocket_world(size=1)
    snake = Snake([(0, 0), (-1, 0), (-2, 0)], DIR_RIGHT)
    world._foods.clear()  # noqa: SLF001
    world._foods_by_chunk.clear()  # noqa: SLF001
    world._foods.add((1, 1))  # noqa: SLF001
    world._foods_by_chunk[(0, 0)] = {(1, 1)}  # noqa: SLF001

    ai = AIController()
    ai.plan(world, snake)
    assert ai.state in (STATE_FOLLOW_TAIL, "IDLE")
    assert ai.stats["blocked_l1"] + ai.stats["blocked_l2"] >= 1
    assert ai.stats["follow_tail"] >= 1


def test_follow_tail_keeps_snake_alive():
    """没有食物时跟尾，蛇不应在 200 tick 内死亡。"""
    game = Game(2026)
    game.world.ensure_chunk(0, 0)
    game.world._foods.clear()  # noqa: SLF001
    game.world._foods_by_chunk.clear()  # noqa: SLF001
    ai = AIController()

    for _ in range(200):
        d = ai.decide(game.world, game.snake)
        if d:
            game.set_direction(d)
        if game.update(0.1).died:
            break
    assert game.state == "running", f"跟尾死了：ticks={game.ticks}"


def test_loop_guard_triggers_on_repeated_head():
    game = Game(5)
    game.world.ensure_chunk(0, 0)
    ai = AIController()
    head = game.snake.head
    for _ in range(3):
        ai.recent_heads.append(head)
    ai.plan(game.world, game.snake)
    assert ai.stats["loop_guard"] >= 1
    assert ai.state == STATE_FOLLOW_TAIL


def test_follow_tail_switches_back_to_food_when_safe():
    """跟尾过程中出现安全食物 → 自动切回 SEEKING_FOOD。"""
    from ai.controller import STATE_SEEKING_FOOD

    game = Game(13)
    game.world.ensure_chunk(0, 0)
    game.world._foods.clear()  # noqa: SLF001
    game.world._foods_by_chunk.clear()  # noqa: SLF001

    ai = AIController()
    ai.plan(game.world, game.snake)
    assert ai.state == STATE_FOLLOW_TAIL

    head = game.snake.head
    food = (head[0] + 3, head[1])
    game.world._foods.add(food)  # noqa: SLF001
    game.world._foods_by_chunk.setdefault((0, 0), set()).add(food)  # noqa: SLF001

    ai.plan(game.world, game.snake)
    assert ai.state == STATE_SEEKING_FOOD


def test_nudge_offset_changes_follow_direction(monkeypatch):
    """防循环不能只切状态：offset 必须真的改变跟尾时的方向优先级。"""
    from core.snake import DIR_RIGHT, Snake as S

    world = World(9)
    world.ensure_chunk(0, 0)
    snake = S([(0, 0)], DIR_RIGHT)  # 长度 1，四邻全空

    ai = AIController()
    assert ai.fallback_direction(world, snake, offset=0) == (0, 1)   # 上
    assert ai.fallback_direction(world, snake, offset=1) == (1, 0)   # 右

    ai.state = STATE_FOLLOW_TAIL
    ai._nudge_offset = 1
    ai.path = []
    monkeypatch.setattr(ai, "plan", lambda *a, **k: [])
    assert ai.decide(world, snake) == (1, 0)


def test_wrap_mode_ai_survives_walls():
    game = Game(9)
    game.world.ensure_chunk(0, 0)
    game.set_wrap_mode(True)
    ai = AIController()
    for _ in range(100):
        d = ai.decide(game.world, game.snake, wrap_mode=True)
        if d:
            game.set_direction(d)
        if game.update(0.1).died:
            break
    assert game.state == "running"


# ---------- 三处标注一致 ----------
def test_l2_heuristic_annotated_in_three_places():
    src = open(os.path.join(ROOT, "src", "ai", "safety.py"), encoding="utf-8").read()
    arch = open(os.path.join(ROOT, "docs", "ARCH.md"), encoding="utf-8").read()
    assert "启发式加强" in src
    assert "启发式加强" in strings.STRINGS["zh"]["safety_l2_note"]
    assert "启发式加强" in arch
