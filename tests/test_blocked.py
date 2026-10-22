"""M2/R1：阻挡索引与 is_passable 语义（方案 B）。"""

import inspect

import pytest

from app import constants as C
from core import gen
from core.chunk import Chunk
from core.game import STATE_DEAD, STATE_RUNNING, Game
from core.snake import DIR_DOWN, DIR_RIGHT, Snake
from core.world import BLOCK_OBSTACLE, BLOCK_WALL, World


def test_default_world_is_passable_everywhere():
    world = World(1)
    assert world.is_passable((0, 0)) is True
    assert world.is_passable((-999, 12345)) is True
    assert world.blocked() == frozenset()


def test_blocked_cell_is_not_passable():
    world = World(1)
    world.add_blocked((3, 4), BLOCK_OBSTACLE)
    assert world.is_passable((3, 4)) is False
    assert world.is_blocked((3, 4)) is True
    assert world.block_kind((3, 4)) == BLOCK_OBSTACLE


def test_ignore_blocked_bypasses_terrain():
    world = World(1)
    world.add_blocked((3, 4), BLOCK_WALL)
    assert world.is_passable((3, 4), ignore_blocked=True) is True
    assert world.is_passable((3, 4), ignore_blocked=False) is False


def test_discard_blocked_restores_passability():
    world = World(1)
    world.add_blocked((1, 1), BLOCK_WALL)
    world.discard_blocked((1, 1))
    assert world.is_passable((1, 1)) is True
    assert world.block_kind((1, 1)) is None


# ---------- Snake 集成 ----------
def test_snake_dies_into_blocked():
    world = World(7)
    world.add_blocked((1, 0), BLOCK_OBSTACLE)
    snake = Snake.spawn()
    result = snake.step(world)
    assert result.died is True


def test_snake_passes_through_when_ignore_blocked():
    world = World(7)
    world.add_blocked((1, 0), BLOCK_OBSTACLE)
    snake = Snake.spawn()
    result = snake.step(world, ignore_blocked=True)
    assert result.died is False
    assert snake.head == (1, 0)


def test_ignore_blocked_does_not_bypass_self_collision():
    world = World(7)
    world.add_blocked((0, -1), BLOCK_OBSTACLE)
    body = [(0, 0), (1, 0), (1, -1), (0, -1), (-1, -1)]
    snake = Snake(body, DIR_DOWN)
    result = snake.step(world, ignore_blocked=True)
    assert result.died is True, "穿墙模式撞自身仍然死（D-025）"


# ---------- Game 集成 ----------
def test_game_wrap_mode_flag():
    game = Game(3)
    assert game.wrap_mode is False
    game.set_wrap_mode(True)
    assert game.wrap_mode is True


def test_game_wrap_mode_survives_obstacle():
    game = Game(3)
    game.world.add_blocked((1, 0), BLOCK_OBSTACLE)
    game.set_wrap_mode(True)
    summary = game.update(C.TICK_INTERVAL)
    assert summary.died is False
    assert game.state == STATE_RUNNING
    assert game.snake.head == (1, 0)


def test_game_without_wrap_dies_on_obstacle():
    game = Game(3)
    game.world.add_blocked((1, 0), BLOCK_OBSTACLE)
    summary = game.update(C.TICK_INTERVAL)
    assert summary.died is True
    assert game.state == STATE_DEAD


# ---------- 结构 ----------
def test_chunk_keeps_obstacles_and_walls_separate():
    chunk = Chunk(0, 0)
    chunk.obstacles.add((1, 1))
    chunk.walls.add((2, 2))
    assert chunk.obstacles == {(1, 1)}
    assert chunk.walls == {(2, 2)}
    assert chunk.walls_degraded is False


def test_chunk_does_not_expose_blocked_property():
    """阻挡查询统一走 World._blocked，Chunk 不再每次访问都新建 set。"""
    assert not hasattr(Chunk(0, 0), "blocked")


def test_r1_generates_no_blocked_cells():
    """R1 只切数据结构，不生成障碍/墙壁。"""
    world = World(5)
    world.ensure_chunk_at((0, 0))
    assert world.blocked() == frozenset()


def test_gen_no_longer_exposes_is_passable():
    """通行判定只允许走 World.is_passable（防止绕过 _blocked）。"""
    assert not hasattr(gen, "is_passable")


def test_world_is_passable_signature():
    params = inspect.signature(World.is_passable).parameters
    assert "ignore_blocked" in params
    assert params["ignore_blocked"].default is False
