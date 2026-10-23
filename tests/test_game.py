"""对局状态机（R2）：Tick 驱动、吃食物计分、死亡冻结、重开、出 chunk 不死。"""

from core.game import STATE_DEAD, STATE_RUNNING, Game
from core.snake import DIR_DOWN, DIR_LEFT, DIR_RIGHT, Snake


def test_update_runs_one_tick_per_interval():
    game = Game(7)
    summary = game.update(0.1)
    assert summary.ticks == 1
    assert game.snake.head == (1, 0)
    assert game.ticks == 1


def test_eating_scores_and_grows():
    game = Game(7)
    game.world._foods.add((1, 0))  # noqa: SLF001 - 测试注入
    summary = game.update(0.1)
    assert summary.ate is True
    assert game.score == 1
    assert len(game.snake) == 4


def test_death_freezes_updates():
    game = Game(7)
    game.snake = Snake([(0, 0), (1, 0), (1, -1), (0, -1), (-1, -1)], DIR_DOWN)

    summary = game.update(0.1)
    assert summary.died is True
    assert game.state == STATE_DEAD

    # 死亡后不再推进
    assert game.update(1.0).ticks == 0


def test_reset_restores_initial_state():
    game = Game(7)
    game.update(0.1)
    game.reset()

    assert game.state == STATE_RUNNING
    assert game.score == 0
    assert game.ticks == 0
    assert len(game.snake) == 3
    assert game.snake.head == (0, 0)


def test_reverse_rejected_through_game():
    game = Game(7)
    assert game.set_direction(DIR_LEFT) is False
    assert game.update(0.1).ticks == 1
    assert game.snake.head == (1, 0)


def test_leaving_chunk_does_not_kill():
    """D-054：走出单 chunk 区域必须存活。"""
    game = Game(7)
    game.snake = Snake([(31, 0), (30, 0), (29, 0)], DIR_RIGHT)

    summary = game.update(0.1)

    assert summary.died is False
    assert game.state == STATE_RUNNING
    assert game.snake.head == (32, 0)


def test_restart_uses_same_seed_world():
    """地图/障碍仍由 seed 决定；食物已改为纯随机（用户确认）。"""
    game = Game(99)
    blocked_before = set(game.world.blocked())
    game.reset(game.seed)
    assert set(game.world.blocked()) == blocked_before
