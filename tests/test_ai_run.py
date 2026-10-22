"""M3/R2：AI 无头跑一局（带 ChunkManager，模拟真实视野）。"""

from ai.controller import AIController
from app import constants as C
from core.chunk_manager import ChunkManager
from core.game import Game


def _run(seed: int, ticks: int = 600):
    game = Game(seed)
    ai = AIController()
    mgr = ChunkManager(game.world)

    for _ in range(ticks):
        head = game.snake.head
        mgr.update((head[0] - 18, head[1] - 10, head[0] + 18, head[1] + 10))
        direction = ai.decide(game.world, game.snake)
        if direction is not None:
            game.set_direction(direction)
        summary = game.update(C.TICK_INTERVAL)
        if summary.died:
            break
    return game, ai


def test_ai_eats_and_survives():
    game, ai = _run(20261022, ticks=600)
    assert game.score >= 2, f"AI 吃得太少（score={game.score}, ticks={game.ticks}）"
    assert game.state == "running", f"AI 死了（ticks={game.ticks}）"
    assert ai.stats["plans"] > 0


def test_ai_pool_clean_and_stats_present():
    game, ai = _run(11, ticks=200)
    assert ai.pool.in_use == 0
    for key in ("state", "plans", "blocked_l1", "blocked_l2", "follow_tail", "loop_guard"):
        assert key in ai.stats
