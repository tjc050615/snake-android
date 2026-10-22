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


# ---------- g 值更新（重复访问同一格） ----------
def _bfs_len(start, goal, passable, rect):
    from collections import deque

    q = deque([(start, 0)])
    seen = {start}
    while q:
        cell, d = q.popleft()
        if cell == goal:
            return d
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (cell[0] + dx, cell[1] + dy)
            if nxt in seen or not passable(nxt):
                continue
            if not (rect[0] <= nxt[0] <= rect[2] and rect[1] <= nxt[1] <= rect[3]):
                continue
            seen.add(nxt)
            q.append((nxt, d + 1))
    return -1


def test_astar_prefers_shorter_g_when_revisiting_cell():
    """有墙的迷宫里，A* 必须有 g 值更新，否则会沿先入的长路径回溯进死路。"""
    layer1 = {(3, y) for y in range(-4, 4)}          # 竖墙，留上方缺口
    layer2 = {(7, y) for y in range(-4, 4)}          # 第二道竖墙
    blocked = layer1 | layer2

    def passable(c):
        return c not in blocked

    rect = _rect(-10, -10, 14, 14)
    path = astar((0, 0), (10, 0), passable, rect)
    shortest = _bfs_len((0, 0), (10, 0), passable, rect)

    assert path, "应该找到路径"
    assert path[-1] == (10, 0)
    assert len(path) == shortest
    assert len(set(path)) == len(path), "路径不应出现重复格（说明 parent 回溯错了）"


def test_astar_max_nodes_exhausted_returns_best_so_far():
    """max_nodes 用尽且未找到目标 → 返回空路径；已找到则返回当前最优。"""
    rect = _rect(-20, -20, 20, 20)
    far = astar((0, 0), (30, 0), lambda c: True, rect, max_nodes=5)
    assert far == []

    near = astar((0, 0), (2, 0), lambda c: True, rect, max_nodes=50)
    assert near == [(1, 0), (2, 0)]


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


def _inject_food(world, cells):
    """测试用：把食物同时写进全局集合与分桶。"""
    from core.world import chunk_coord

    for c in cells:
        world._foods.add(c)  # noqa: SLF001
        world._foods_by_chunk.setdefault(chunk_coord(c), set()).add(c)  # noqa: SLF001


def test_controller_picks_nearest_food():
    game = Game(7)
    for cx in (0, 1):
        for cy in (0, 1):
            game.world.ensure_chunk(cx, cy)
    head = game.snake.head
    near = (head[0] + 3, head[1])
    far = (head[0] + 9, head[1])
    game.world._foods.clear()  # noqa: SLF001
    game.world._foods_by_chunk.clear()  # noqa: SLF001
    _inject_food(game.world, {near, far})

    ai = AIController()
    path = ai.plan(game.world, game.snake)
    assert path[-1] == near


def test_controller_no_food_follows_tail():
    """R2：没有食物（或都不安全）→ FOLLOW_TAIL，而不是干等。"""
    world = World(3)
    world.ensure_chunk(0, 0)
    world._foods.clear()  # noqa: SLF001
    world._foods_by_chunk.clear()  # noqa: SLF001
    game = Game(3)
    game.world = world
    ai = AIController()
    assert ai.plan(world, game.snake) == []
    assert ai.state == "FOLLOW_TAIL"


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


def test_fallback_picks_first_available_in_order():
    """上被挡、右被挡 → 必须返回"下"，而不是随便挑一个安全方向。"""
    from core.snake import DIR_RIGHT, Snake as S

    world = World(9)
    world.ensure_chunk(0, 0)
    snake = S([(0, 0)], DIR_RIGHT)
    world.add_blocked((0, 1))  # 上
    world.add_blocked((1, 0))  # 右

    ai = AIController()
    assert ai.fallback_direction(world, snake) == (0, -1)


def test_decide_returns_direction_toward_food():
    game = Game(5)
    for cx in (0, 1):
        for cy in (0, 1):
            game.world.ensure_chunk(cx, cy)
    head = game.snake.head
    game.world._foods.clear()  # noqa: SLF001
    game.world._foods_by_chunk.clear()  # noqa: SLF001
    _inject_food(game.world, {(head[0] + 4, head[1])})

    ai = AIController()
    assert ai.decide(game.world, game.snake) == (1, 0)


def test_vision_uses_loaded_chunks_not_viewport():
    """视野 = 已加载 chunk 范围，不是视口一半（41×23 视口只给 20 格是错的）。"""
    from core.chunk_manager import ChunkManager

    game = Game(1)
    mgr = ChunkManager(game.world)
    for _ in range(120):
        mgr.update((0, 0, 40, 22))  # 视口 41×23，预加载 2 圈 → 6×5 chunk
    ai = AIController(view_w=41, view_h=23)
    rect = ai.rect_for(game.snake.head, snake_len=100, world=game.world)
    assert rect[2] - rect[0] > 100, rect
    assert rect[3] - rect[1] > 100, rect


def test_vision_is_clamped_to_loaded_rect():
    game = Game(1)
    game.world.ensure_chunk(0, 0)  # 只加载 1 个 chunk
    ai = AIController()
    rect = ai.rect_for(game.snake.head, snake_len=100, world=game.world)
    loaded = game.world.loaded_rect()
    assert rect[0] >= loaded[0] and rect[2] <= loaded[2]
    assert rect[1] >= loaded[1] and rect[3] <= loaded[3]


def test_search_radius_formula():
    ai = AIController()
    assert ai.search_radius(3) == C.AI_RADIUS_BASE + 3
    assert ai.search_radius(100) == C.AI_RADIUS_MAX


def test_manhattan_helper():
    assert manhattan((0, 0), (3, 4)) == 7
