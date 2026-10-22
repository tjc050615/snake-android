"""世界坐标 / chunk 坐标 / 视口变换（M1-1 / M1-16）。"""

import pytest

from app import constants as C
from core.viewport import Viewport
from core.world import World, chunk_coord


@pytest.mark.parametrize(
    "cell,expected",
    [
        ((0, 0), (0, 0)),
        ((31, 31), (0, 0)),
        ((32, 0), (1, 0)),
        ((0, 32), (0, 1)),
        ((-1, -1), (-1, -1)),
        ((-32, -1), (-1, -1)),
        ((-33, 0), (-2, 0)),
        ((64, -64), (2, -2)),
    ],
)
def test_chunk_coord_negative_safe(cell, expected):
    assert chunk_coord(cell) == expected


def test_chunk_coord_is_floor_not_truncate():
    # int() 截断会得到 0，地板除得到 -1
    assert chunk_coord((-1, 0)) == (-1, 0)
    assert chunk_coord((1, 0)) == (0, 0)


def test_viewport_centers_spawn_cell():
    vp = Viewport.centered_on_cell(C.SPAWN_CELL, 32, 1280, 720)
    x, y, w, h = vp.cell_rect((0, 0))
    assert (x + w / 2, y + h / 2) == pytest.approx((640, 360))


def test_viewport_roundtrip_screen_to_cell():
    vp = Viewport.centered_on_cell((5, -3), 32, 1280, 720)
    sx, sy = vp.cell_rect((5, -3))[:2]
    assert vp.cell_at_screen(sx + 1, sy + 1) == (5, -3)


def test_visible_bounds_cover_origin():
    vp = Viewport.centered_on_cell((0, 0), 32, 1280, 720)
    assert vp.covers((0, 0))
    cells = list(vp.iter_visible_cells())
    assert (0, 0) in cells
    # 至少 21 格（D-014）
    xs = {c[0] for c in cells}
    ys = {c[1] for c in cells}
    assert len(xs) >= C.VIEWPORT_MIN_CELLS
    assert len(ys) >= C.VIEWPORT_MIN_CELLS


def test_world_is_infinite_outside_generated_chunk():
    """D-054：走出单 chunk 不死亡、全可通行、无食物。

    注意（M1 语义）：该测试能通过，是因为 M1 的 World.is_passable 恒为 True，
    且从未 ensure_chunk 过 (500,500) 所在 chunk。这是**有意为之的阶段语义**，
    不是"已实现无限地形"。M2 引入障碍/墙壁后，is_passable 改为查 chunk 地形表，
    本测试的预期需要同步变更（改为"未加载 chunk 按可通行处理"或先 ensure_chunk）。
    届时若本测试变红，应视为**预期变更**，不是回归。
    """
    world = World(seed=1)
    world.ensure_chunk_at((0, 0))
    far = (500, 500)
    assert world.has_chunk(far) is False
    assert world.is_passable(far) is True
    assert world.has_food(far) is False


def test_world_negative_coords_passable():
    world = World(seed=7)
    assert world.is_passable((-1000, -1000)) is True
