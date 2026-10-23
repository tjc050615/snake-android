"""模块一/二/三：食物随机、输入队列、背景色板、蛇身渐变。"""

from core.colors import (
    GRADIENTS,
    SOLIDS,
    background_color,
    gradient_pair,
    snake_gradient,
)
from core.food import ensure_food, food_rng, free_cells, reroll_foods
from core.game import Game
from core.input_queue import InputQueue, is_reverse


# ---------- 食物 ----------
def test_food_not_fixed_across_seeds():
    a = Game(1)
    b = Game(2)
    assert a.world.foods() != b.world.foods(), "不同 seed 食物布局应不同"


def test_food_reproducible_for_same_seed():
    a = Game(42)
    b = Game(42)
    assert a.world.foods() == b.world.foods()


def test_food_ensure_when_empty():
    game = Game(3)
    for cell in list(game.world.foods()):
        game.world.discard_food(cell)
    assert game.world.food_count() == 0
    game.update(0.1)
    assert game.world.food_count() >= 1, "无食物时必须立刻补一个"


def test_free_cells_excludes_body_and_food():
    game = Game(4)
    cells = free_cells(game.world, game.snake)
    assert cells, "应有可用空格"
    body = set(game.snake.body)
    assert not (set(cells) & body)
    assert not (set(cells) & set(game.world.foods()))


def test_reroll_keeps_food_count():
    game = Game(5)
    before = len(game.world.foods())
    rng = food_rng(99)
    reroll_foods(game.world, game.snake, rng)
    assert len(game.world.foods()) == before


# ---------- 输入队列 ----------
def test_queue_rejects_reverse_and_duplicate():
    q = InputQueue()
    assert q.push((0, 1), (1, 0)) is True
    assert q.push((0, -1), (0, 1)) is False, "禁止 180 度掉头"
    assert q.push((0, 1), (0, 1)) is False, "同向去重"
    assert q.push((1, 0), (0, 1)) is True


def test_queue_fifo_and_bounded():
    q = InputQueue(maxlen=2)
    q.push((0, 1), (1, 0))
    q.push((1, 0), (0, 1))
    q.push((0, -1), (1, 0))
    assert len(q) == 2
    assert q.pop() == (1, 0)    # 满队列丢最旧
    assert q.pop() == (0, -1)
    assert q.pop() is None


def test_is_reverse():
    assert is_reverse((1, 0), (-1, 0))
    assert not is_reverse((1, 0), (0, 1))


# ---------- 颜色 ----------
def test_sixteen_solids_and_sixteen_gradients():
    assert len(SOLIDS) == 16
    assert len(GRADIENTS) == 16
    for i in range(16):
        rgb = background_color(i)
        assert len(rgb) == 3 and all(0.0 <= c <= 1.0 for c in rgb)
        a, b = gradient_pair(i)
        assert a != b


def test_snake_gradient_smooth_and_distinct_ends():
    colors = snake_gradient(10)
    assert len(colors) == 10
    assert colors[0] != colors[-1], "头尾颜色应不同（渐变）"
    for c in colors:
        assert all(0.0 <= v <= 1.0 for v in c)
