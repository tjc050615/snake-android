"""M3/R2 回归：A* 空路径时必须继续尝试下一个食物。"""

import ai.controller as controller_mod
from ai.controller import AIController
from core.game import Game


def test_astar_empty_continues_to_next_food(monkeypatch):
    """第一个食物安全但 A* 不可达 → 必须试第二个，而不是直接跟尾。"""
    game = Game(17)
    for cx in (0, 1):
        for cy in (0, 1):
            game.world.ensure_chunk(cx, cy)

    head = game.snake.head
    first = (head[0] + 2, head[1])      # 距离更近，但被"假装"不可达
    second = (head[0] + 5, head[1])     # 更远，可达

    game.world._foods.clear()  # noqa: SLF001
    game.world._foods_by_chunk.clear()  # noqa: SLF001
    for c in (first, second):
        game.world._foods.add(c)  # noqa: SLF001
        game.world._foods_by_chunk.setdefault((0, 0), set()).add(c)  # noqa: SLF001

    real_astar = controller_mod.astar

    def fake_astar(start, goal, *args, **kwargs):
        if goal == first:
            return []
        return real_astar(start, goal, *args, **kwargs)

    monkeypatch.setattr(controller_mod, "astar", fake_astar)

    ai = AIController()
    path = ai.plan(game.world, game.snake)

    assert path, "应该退到第二个食物"
    assert path[-1] == second
    assert ai.state == "SEEKING_FOOD"
