"""蛇模型（R2）：出生几何、180° 反向、吃食物、自撞、跟尾、出 chunk。"""

from app import constants as C
from core.snake import DIR_DOWN, DIR_LEFT, DIR_RIGHT, DIR_UP, Snake
from core.world import World


def _bare_world(seed: int = 1) -> World:
    """不 ensure_chunk：食物表为空，便于精确注入。"""
    return World(seed)


def test_spawn_geometry():
    snake = Snake.spawn()
    assert snake.head == C.SPAWN_CELL
    assert len(snake) == 3
    assert list(snake.body) == [(0, 0), (-1, 0), (-2, 0)]
    assert snake.direction == (1, 0)


def test_reverse_direction_rejected():
    snake = Snake.spawn()
    assert snake.set_direction(DIR_LEFT) is False
    assert snake.pending == DIR_RIGHT


def test_perpendicular_direction_accepted():
    snake = Snake.spawn()
    assert snake.set_direction(DIR_UP) is True
    assert snake.pending == DIR_UP


def test_quick_two_key_combo_allowed():
    """同一 Tick 内"先上再左"是合法转弯，不能被当成相对已提交方向的反向。"""
    snake = Snake.spawn()
    assert snake.set_direction(DIR_UP) is True
    assert snake.set_direction(DIR_LEFT) is True
    assert snake.pending == DIR_LEFT


def test_reverse_of_pending_rejected():
    snake = Snake.spawn()
    assert snake.set_direction(DIR_UP) is True
    assert snake.set_direction(DIR_DOWN) is False  # 与 pending 相反
    assert snake.pending == DIR_UP


def test_move_without_food_keeps_length():
    snake = Snake.spawn()
    result = snake.step(_bare_world())
    assert result.died is False
    assert result.ate is False
    assert len(snake) == 3
    assert snake.head == (1, 0)


def test_eat_grows_and_sets_ate_flag():
    snake = Snake.spawn()
    world = _bare_world()
    world._foods.add((1, 0))  # noqa: SLF001 - 测试注入

    result = snake.step(world)

    assert result.ate is True
    assert snake.ate_food is True
    assert len(snake) == 4
    assert snake.head == (1, 0)
    assert world.has_food((1, 0)) is False


def test_self_collision_dies():
    body = [(0, 0), (1, 0), (1, -1), (0, -1), (-1, -1)]
    snake = Snake(body, DIR_DOWN)

    result = snake.step(_bare_world())

    assert result.died is True
    assert len(snake) == 5


def test_moving_into_tail_cell_is_allowed():
    """没吃食物时尾巴让位，走进当前尾巴格不算自撞。"""
    body = [(0, 0), (0, 1), (1, 1), (1, 0)]
    snake = Snake(body, DIR_RIGHT)

    result = snake.step(_bare_world())

    assert result.died is False
    assert snake.head == (1, 0)
    assert (0, 0) in snake.occupied
    assert len(snake.occupied) == len(snake.body)


def test_walking_out_of_chunk_is_alive():
    """D-054：chunk 不是物理边界。"""
    snake = Snake([(31, 0), (30, 0), (29, 0)], DIR_RIGHT)
    world = _bare_world()
    world.ensure_chunk_at((0, 0))

    result = snake.step(world)

    assert result.died is False
    assert snake.head == (32, 0)


def test_occupied_stays_consistent_after_many_steps():
    snake = Snake.spawn()
    world = _bare_world()
    for _ in range(50):
        result = snake.step(world)
        assert not result.died
        assert len(snake.occupied) == len(snake.body)
