"""M3/R1：AI 无头跑一局，验证真的会吃食物（R1 允许死）。"""

from ai.controller import AIController
from app import constants as C
from core.game import Game


def _run(seed: int, ticks: int = 600):
    game = Game(seed)
    ai = AIController()
    for _ in range(ticks):
        direction = ai.decide(game.world, game.snake)
        if direction is not None:
            game.set_direction(direction)
        summary = game.update(C.TICK_INTERVAL)
        if summary.died:
            break
    return game, ai


def test_ai_eats_at_least_once_r1():
    game, ai = _run(20261022)
    assert game.score >= 1, f"AI 没吃到食物（ticks={game.ticks}）"
    assert ai.stats["plans"] > 0


def test_ai_plans_are_bounded():
    game, ai = _run(11, ticks=200)
    assert ai.pool.in_use == 0, "规划结束后节点池必须归零"
