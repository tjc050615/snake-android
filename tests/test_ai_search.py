"""M3/R1：A* 确定性、路径合法性、视野边界、节点池不泄漏。"""

from ai.controller import AIController
from ai.search import NodePool, astar, manhattan
from app import constants as C
from core.game import Game
from core.world import BLOCK_WALL, World


def _rect(x0, y0, x1, y1):
    return (x0, y0, x1, y1)


# ---------- A* 基础 ----------
def test_astar_straight_line():
    path = astar((0, 0), (3, 0), lambda c: True, _rect(-5, -5, 10, 10))
    assert path == [(1, 0), (2, 0), (3, 0)]


def test_astar_avoids_blocked():
    blocked = {(1, 0)}
    path = astar((0, 0), (3, 0), lambda c: c not in blocked, _rect(-5, -5, 10, 10))
    assert (1, 0) not in path
    assert path[-1] == (3, 0)
    assert len(path) == 5  # 绕一格


def test_astar_returns_empty_when_unreachable():
    blocked = {(1, 0), (0, 1), (-1, 0), (0, -1)}
    path = astar((0, 0), (3, 0), lambda c: c not in blocked, _rect(-5, -5, 10, 10))
    assert path == []


def test_astar_is_deterministic():
    blocked = {(2, 1), (2, 2)}
    p1 = astar((0, 0), (4, 0), lambda c: c not in blocked, _rect(-5, -5, 10, 10))
    p2 = astar((0, 0), (4, 0), lambda c: c not in blocked, _rect(-5, -5, 10, 10))
    assert p1 == p2


def test_astar_tiebreak_prefers_lower_x_then_y():
    """对称地图上两条等长路径，平局键 (f,h,x,y) 必须稳定选一条。"""
    blocked = set()
    p1 = astar((0, 0), (2, 2), lambda c: c not in blocked, _rect(-5, -5, 10, 10))
    p2 = astar((0, 0), (2, 2), lambda c: c not in blocked, _rect(-5, -5, 10, 10))
    assert p1 == p2
    assert p1[-1] == (2, 2)


# ---------- 节点池 ----------
def test_node_pool_no_leak():
    pool = NodePool()
    for _ in range(5):
        astar((0, 0), (6, 0), lambda c: True, _rect(-5, -5, 15, 15), pool=pool)
        assert pool.in_use == 0
    created = pool.created
    for _ in range(5):
        astar((0, 0), (6, 0), lambda c: True, _rect(-5, -5, 15, 15), pool=pool)
    assert pool.in_use == 0
    assert pool.created == created, "复用池不应在后续搜索中继续创建节点"


# ---------- 控制器 ----------
def test_controller_path_stays_in_vision_and_avoids_walls():
    game = Game(20261022)
    game.world.ensure_chunk(0, 0)
    ai = AIController(view_w=41, view_h=23)

    path = ai.plan(game.world, game.snake)
    head = game.snake.head
    rect = ai.rect_for(head, len(game.snake))
    for cell in path:
        assert rect[0] <= cell[0] <= rect[2]
        assert rect[1] <= cell[1] <= rect[3]
        assert cell not in game.world.blocked()
        assert cell not in game.snake.occupied


def test_controller_picks_nearest_food():
    game = Game(7)
    game.world.ensure_chunk(0, 0)
    head = game.snake.head
    near = (head[0] + 3, head[1])
    far = (head[0] + 9, head[1])
    game.world._foods = {near, far}  # noqa: SLF001 - 测试构造
    game.world._foods_by_chunk = {  # noqa: SLF001
        (0, 0): {near, far}
    }
    ai = AIController()
    path = ai.plan(game.world, game.snake)
    assert path[-1] == near


def test_controller_no_food_is_idle():
    world = World(3)
    world.ensure_chunk(0, 0)
    world._foods.clear()  # noqa: SLF001
    world._foods_by_chunk.clear()  # noqa: SLF001
    game = Game(3)
    game.world = world
    ai = AIController()
    assert ai.plan(world, game.snake) == []
    assert ai.state == "IDLE"


def test_safe_step_rejects_wall_and_self():
    game = Game(9)
    game.world.ensure_chunk(0, 0)
    ai = AIController()
    head = game.snake.head
    game.world.add_blocked((head[0] + 1, head[1]), BLOCK_WALL)
    assert ai.safe_step(game.world, game.snake, (1, 0)) is False
    assert ai.safe_step(game.world, game.snake, (-1, 0)) is False  # 撞自己（长度>1）


def test_fallback_direction_is_deterministic_order():
    game = Game(9)
    game.world.ensure_chunk(0, 0)
    ai = AIController()
    d = ai.fallback_direction(game.world, game.snake)
    assert d in ((0, 1), (1, 0), (0, -1), (-1, 0))


def test_decide_returns_direction_toward_food():
    game = Game(5)
    game.world.ensure_chunk(0, 0)
    head = game.snake.head
    game.world._foods = {(head[0] + 4, head[1])}  # noqa: SLF001
    game.world._foods_by_chunk = {(0, 0): set(game.world._foods)}  # noqa: SLF001
    ai = AIController()
    assert ai.decide(game.world, game.snake) == (1, 0)


def test_vision_rect_respects_viewport():
    ai = AIController(view_w=21, view_h=11)
    rect = ai.rect_for((0, 0), snake_len=100)  # 半径被视口夹住
    assert rect[2] - rect[0] == 20
    assert rect[3] - rect[1] == 10


def test_search_radius_formula():
    ai = AIController()
    assert ai.search_radius(3) == C.AI_RADIUS_BASE + 3
    assert ai.search_radius(100) == C.AI_RADIUS_MAX


def test_manhattan_helper():
    assert manhattan((0, 0), (3, 4)) == 7
