"""M4/R1 第一步：分栏几何、摇杆逻辑、触控隔离。"""

import pytest

from core.joystick import Joystick
from core.layout import GAME_RATIO, in_rect, split_rects


# ---------- 分栏 ----------
@pytest.mark.parametrize("w,h", [(1280, 720), (1920, 1080), (800, 480), (1366, 768)])
def test_split_ratio_within_one_pixel(w, h):
    game, panel = split_rects(w, h)
    assert game[2] + panel[2] == w, "两区宽度之和必须等于窗口宽"
    assert abs(game[2] - w * GAME_RATIO) <= 0.5, "70% 误差需 < 1px"
    assert game[3] == panel[3] == h


def test_split_rects_do_not_overlap():
    game, panel = split_rects(1280, 720)
    assert in_rect(game, game[2] - 0.1, 10)
    assert not in_rect(game, game[2] + 0.1, 10)
    assert in_rect(panel, panel[0] + 0.1, 10)


def test_split_rejects_bad_input():
    with pytest.raises(ValueError):
        split_rects(0, 720)
    with pytest.raises(ValueError):
        split_rects(1280, 720, ratio=1.5)


# ---------- 摇杆死区 ----------
def test_joystick_deadzone_blocks_small_drag():
    joy = Joystick(deadzone=0.15, swipe_px=1000)  # 关掉滑动阈值，只测死区
    joy.begin(0, 0)
    assert joy.move(10, 0) is None       # 10/90 ≈ 0.11 < 0.15
    assert joy.move(5, 0) is None


def test_joystick_fires_past_deadzone():
    joy = Joystick(deadzone=0.15, swipe_px=1000)
    joy.begin(0, 0)
    assert joy.move(20, 0) == (1, 0)     # 20/90 ≈ 0.22


def test_joystick_direction_is_four_way():
    joy = Joystick(deadzone=0.15, swipe_px=1000)
    for (x, y), expected in (
        ((50, 10), (1, 0)),
        ((-50, 10), (-1, 0)),
        ((10, 50), (0, 1)),
        ((10, -50), (0, -1)),
    ):
        joy.begin(0, 0)
        assert joy.move(x, y) == expected


def test_joystick_emits_once_per_direction():
    joy = Joystick(deadzone=0.15, swipe_px=1000)
    joy.begin(0, 0)
    assert joy.move(50, 0) == (1, 0)
    assert joy.move(60, 0) is None, "同方向不重复发"


# ---------- 滑动 ----------
def test_swipe_threshold():
    joy = Joystick(deadzone=0.99, swipe_px=30)  # 关掉死区影响，只测滑动阈值
    joy.begin(0, 0)
    assert joy.move(20, 0) is None
    assert joy.move(40, 0) == (1, 0)


def test_swipe_diagonal_picks_dominant_axis():
    joy = Joystick(deadzone=0.99, swipe_px=30)
    joy.begin(0, 0)
    assert joy.move(40, 10) == (1, 0)
    joy.begin(0, 0)
    assert joy.move(10, -40) == (0, -1)


# ---------- 触控隔离（几何层） ----------
def test_panel_area_never_maps_to_game_area():
    game, panel = split_rects(1280, 720)
    for x in (panel[0] + 1, panel[0] + panel[2] / 2, panel[0] + panel[2] - 1):
        assert not in_rect(game, x, 100)


def test_touch_isolation():
    """面板区的点绝不会落进游戏区（反之亦然）。"""
    game, panel = split_rects(1280, 720)
    for x in range(int(panel[0]), 1280, 7):
        assert not in_rect(game, x, 300), f"x={x} 同时属于游戏区"
        assert in_rect(panel, x, 300)


def test_joystick_deadzone():
    joy = Joystick()
    joy.begin(0, 0)
    assert joy.move(90 * 0.14, 0) is None
    assert joy.move(90 * 0.16, 0) == (1, 0)
    game, _panel = split_rects(1280, 720)
    # 摇杆中心固定在游戏区左下角
    assert in_rect(game, 114, 114)
    assert not in_rect(game, 1280 - 10, 114)
