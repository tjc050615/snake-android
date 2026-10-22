"""固定步长 Tick（D-015 / D-016）。"""

import pytest

from core.tick import TickClock


def test_partial_dt_accumulates_then_fires():
    clock = TickClock()
    assert clock.advance(0.05) == 0
    assert clock.advance(0.05) == 1


def test_speed_doubles_tick_rate():
    clock = TickClock()
    clock.set_speed(2.0)
    assert clock.interval == pytest.approx(0.05)
    assert clock.advance(0.1) == 2


def test_speed_is_clamped():
    clock = TickClock()
    clock.set_speed(50.0)
    assert clock.speed == pytest.approx(10.0)
    clock.set_speed(0.01)
    assert clock.speed == pytest.approx(0.5)


def test_max_ticks_per_advance_caps_catchup():
    clock = TickClock(max_ticks_per_advance=4)
    assert clock.advance(5.0) == 4
    assert clock.accumulator == 0.0


def test_zero_and_negative_dt():
    clock = TickClock()
    assert clock.advance(0.0) == 0
    assert clock.advance(-1.0) == 0


def test_reset_clears_accumulator():
    clock = TickClock()
    clock.advance(0.05)
    clock.reset()
    assert clock.accumulator == 0.0


def test_interval_must_be_positive():
    with pytest.raises(ValueError):
        TickClock(interval=0)


def test_progress_is_fraction_of_interval():
    clock = TickClock()
    clock.accumulator = clock.interval * 0.25
    assert clock.progress == pytest.approx(0.25)


def test_progress_returns_zero_on_float_overshoot():
    """advance 正常路径保证 accumulator < interval；>= 1.0 只兜浮点误差。"""
    clock = TickClock()
    clock.accumulator = clock.interval + 1e-9
    assert clock.progress == 0.0


def test_progress_zero_after_tick():
    clock = TickClock()
    clock.advance(0.1)
    assert clock.accumulator == pytest.approx(0.0, abs=1e-9)
    assert clock.progress == pytest.approx(0.0)
