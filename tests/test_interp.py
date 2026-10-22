"""蛇身插值（R4）：解析对拍、尾节两分支、边界、长度 1、死亡冻结。"""

import pytest

from app import constants as C
from core.game import STATE_DEAD, Game
from core.interp import segment_cells, to_pixel
from core.snake import DIR_RIGHT, Snake


def make_snake(cells, prev_tail=(2, 0)):
    snake = Snake(list(cells), DIR_RIGHT)
    snake.prev_tail = prev_tail
    return snake


def test_head_and_middle_at_t0():
    snake = make_snake([(5, 0), (4, 0), (3, 0)], prev_tail=(2, 0))
    assert segment_cells(snake, 0.0) == [(4.0, 0.0), (3.0, 0.0), (2.0, 0.0)]


def test_all_cells_at_t1():
    snake = make_snake([(5, 0), (4, 0), (3, 0)], prev_tail=(2, 0))
    assert segment_cells(snake, 1.0) == [(5.0, 0.0), (4.0, 0.0), (3.0, 0.0)]


def test_midpoint_is_half_cell():
    snake = make_snake([(5, 0), (4, 0), (3, 0)], prev_tail=(2, 0))
    assert segment_cells(snake, 0.5) == [(4.5, 0.0), (3.5, 0.0), (2.5, 0.0)]


def test_vertical_interpolation():
    snake = Snake([(0, 5), (0, 4), (0, 3)], DIR_RIGHT)
    snake.prev_tail = (0, 2)
    # body[1]=(0,4) → body[0]=(0,5)，t=0.25 → 4.25
    assert segment_cells(snake, 0.25) == [(0.0, 4.25), (0.0, 3.25), (0.0, 2.25)]


# ---------- 尾节两分支 ----------
def test_tail_moves_when_not_eating():
    snake = make_snake([(5, 0), (4, 0), (3, 0)], prev_tail=(2, 0))
    snake.ate_food = False
    assert segment_cells(snake, 0.0)[-1] == (2.0, 0.0)
    assert segment_cells(snake, 1.0)[-1] == (3.0, 0.0)


def test_tail_stays_when_eating():
    snake = make_snake([(5, 0), (4, 0), (3, 0)], prev_tail=(2, 0))
    snake.ate_food = True
    for t in (0.0, 0.5, 0.999):
        assert segment_cells(snake, t)[-1] == (3.0, 0.0)


# ---------- 边界 ----------
def test_t1_is_exact_endpoint():
    """t=1.0 是死亡冻结值，必须精确落在整格（interp 不再二次夹取）。"""
    snake = make_snake([(5, 0), (4, 0), (3, 0)], prev_tail=(2, 0))
    assert segment_cells(snake, 1.0) == [(5.0, 0.0), (4.0, 0.0), (3.0, 0.0)]


def test_length_one_is_not_interpolated():
    snake = Snake([(0, 0)], DIR_RIGHT)
    for t in (0.0, 0.3, 1.0):
        assert segment_cells(snake, t) == [(0.0, 0.0)]


# ---------- 与 Game 集成 ----------
def test_progress_comes_from_tick_clock():
    game = Game(7)
    game.update(0.05)          # 半格
    assert 0.0 <= game.tick_progress < 1.0
    assert game.tick_progress == pytest.approx(game.clock.progress)


def test_progress_frozen_when_dead():
    game = Game(7)
    game.state = STATE_DEAD
    assert game.tick_progress == 1.0


def test_prev_tail_is_recorded_before_move():
    game = Game(7)
    old_tail = game.snake.tail
    game.update(C.TICK_INTERVAL)
    assert game.snake.prev_tail == old_tail


# ---------- 像素换算 ----------
def test_to_pixel_uses_cell_center():
    assert to_pixel((2.0, 3.0), 32, -100.0, -50.0) == (2 * 32 + 16 + 100.0, 3 * 32 + 16 + 50.0)


def test_to_pixel_half_cell_offset():
    x, y = to_pixel((2.5, 3.0), 32, 0.0, 0.0)
    assert (x, y) == (2.5 * 32 + 16, 3.0 * 32 + 16)
