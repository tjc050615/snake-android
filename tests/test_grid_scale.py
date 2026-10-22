"""像素缩放（M1-9）：grid_size = max(16, round(32 * density))。"""

import pytest

from app import constants as C
from core.scale import (
    cells_for,
    fit_grid_size,
    grid_size_for_density,
    viewport_cells,
    viewport_ok,
)


@pytest.mark.parametrize(
    "density,expected",
    [
        (1.0, 32),
        (1.5, 48),
        (2.0, 64),
        (3.0, 96),
        (2.625, 84),
    ],
)
def test_grid_size_formula(density, expected):
    assert grid_size_for_density(density) == expected


@pytest.mark.parametrize("density", [0.25, 0.4, 0.49])
def test_grid_size_min_clamp(density):
    assert grid_size_for_density(density) == C.GRID_SIZE_MIN


def test_grid_size_positive_density_required():
    with pytest.raises(ValueError):
        grid_size_for_density(0)


def test_cells_for_is_floor_not_round():
    assert cells_for(100, 32) == 3
    assert cells_for(32 * 3 - 1, 32) == 2


def test_viewport_cells_and_ok():
    assert viewport_cells(1280, 720, 32) == (40, 22)
    assert viewport_ok(1280, 720, 32) is True
    assert viewport_ok(960, 540, 32) is False  # 只有 16 行，<21


def test_fit_grid_size_downgrades_to_meet_min_cells():
    grid = fit_grid_size(1.0, 960, 540)
    assert grid < 32
    assert grid >= C.GRID_SIZE_MIN
    assert viewport_ok(960, 540, grid) is True


def test_fit_grid_size_keeps_formula_when_roomy():
    assert fit_grid_size(1.0, 1280, 720) == 32


def test_fit_grid_size_raises_when_window_too_small():
    """兜底失败路径：降到 16 仍不足 21 格 → 必须抛错，不得静默返回 16。"""
    with pytest.raises(ValueError, match="viewport too small"):
        fit_grid_size(1.0, 300, 300)


def test_fit_grid_size_accepts_exact_minimum():
    """21 × 16 = 336 px 是临界值，刚好通过。"""
    assert fit_grid_size(1.0, 336, 336) == C.GRID_SIZE_MIN


def test_min_viewport_px_matches_constants():
    from core.scale import min_viewport_px

    assert min_viewport_px() == C.VIEWPORT_MIN_CELLS * C.GRID_SIZE_MIN == 336
