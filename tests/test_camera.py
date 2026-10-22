"""相机（R3）：死区 / 滞回 / 硬吸附 / 指数平滑 / 负坐标。"""

import math

import pytest

from app import constants as C
from core.camera import Camera

G = 32
VW, VH = 1280.0, 720.0
HALF_W, HALF_H = VW / 2, VH / 2


def make_camera(cell: tuple[int, int] = (0, 0)) -> Camera:
    cam = Camera(G, VW, VH)
    cam.reset(cell)
    return cam


def place(cam: Camera, d_cells: float, cell: tuple[int, int] = (0, 0)) -> tuple[int, int]:
    """把相机摆到"蛇头距右边缘恰好 d_cells 格"的位置，返回蛇头格。"""
    hx = cell[0] * G + G / 2
    hy = cell[1] * G + G / 2
    cam.current_x = hx + d_cells * G - HALF_W
    cam.current_y = hy
    return cell


# ---------- 死区 ----------
def test_no_move_outside_deadzone():
    cam = make_camera()
    head = place(cam, 11)
    x0, y0 = cam.center()
    for _ in range(30):
        cam.update(1 / 60, head)
    assert (cam.current_x, cam.current_y) == (x0, y0)


def test_push_is_zero_at_exactly_ten_cells():
    cam = make_camera()
    head = place(cam, 10)
    x0 = cam.current_x
    cam.update(1 / 60, head)
    assert cam.target_x == pytest.approx(x0)
    assert cam.current_x == pytest.approx(x0)


def test_push_offset_formula():
    """9 格 → 推 1 格；8 格 → 推 2 格。"""
    for d, push in ((9, 1), (8, 2)):
        cam = make_camera()
        head = place(cam, d)
        c0 = cam.current_x
        cam.update(1 / 60, head)
        assert cam.target_x - c0 == pytest.approx(push * G)


def test_axes_are_independent():
    cam = make_camera()
    head = place(cam, 8)  # 只有 x 越界
    cam.update(1 / 60, head)
    assert cam.target_y == cam.current_y == G / 2


# ---------- 滞回 ----------
def test_hysteresis_armed_then_holds_until_twelve():
    cam = make_camera()
    cam.update(1 / 60, place(cam, 8))
    assert cam.armed_x is True

    frozen = cam.target_x
    # 11 格：仍在 10~12 的滞回带内 → 保持 armed，且 target 冻结
    cam.update(1 / 60, place(cam, 11))
    assert cam.armed_x is True
    assert cam.target_x == pytest.approx(frozen)

    # 13 格：解除
    cam.update(1 / 60, place(cam, 13))
    assert cam.armed_x is False


def test_converges_without_overshoot():
    """蛇头固定在 9 格处：相机单调逼近 target，不越过、不反向抽动。"""
    cam = make_camera()
    head = place(cam, 9)
    target = None
    prev = cam.current_x
    for _ in range(90):
        cam.update(1 / 60, head)
        target = cam.target_x
        assert cam.current_x >= prev - 1e-9, "不得反向"
        prev = cam.current_x
    assert cam.current_x <= target + 1e-9, "不得越过 target"
    assert abs(target - cam.current_x) < 1e-3, "应已收敛"


# ---------- 硬吸附 ----------
def test_snap_inside_three_cells():
    cam = make_camera()
    cam.update(1 / 60, place(cam, 2))
    assert cam.current_x == pytest.approx(cam.target_x)


def test_snap_beats_slow_smoothing():
    cam = make_camera()
    cam.smooth_k = 0.001
    cam.update(1 / 60, place(cam, 1))
    assert cam.current_x == pytest.approx(cam.target_x)


# ---------- 平滑：帧率无关 ----------
@pytest.mark.parametrize("dt", [1 / 60, 1 / 30, 1 / 120])
def test_smoothing_matches_analytic_solution(dt):
    cam = make_camera()
    head = place(cam, 9)
    start_x = cam.current_x

    steps = int(round(0.5 / dt))
    for _ in range(steps):
        cam.update(dt, head)

    t = steps * dt
    expected = cam.target_x + (start_x - cam.target_x) * math.exp(-C.CAMERA_SMOOTH_K * t)
    assert cam.current_x == pytest.approx(expected, rel=1e-9, abs=1e-9)


def test_three_frame_rates_agree():
    results = []
    for dt in (1 / 60, 1 / 30, 1 / 120):
        cam = make_camera()
        head = place(cam, 6)
        for _ in range(int(round(0.5 / dt))):
            cam.update(dt, head)
        results.append(cam.current_x)
    assert max(results) - min(results) < 1e-6


# ---------- 负坐标 ----------
def test_negative_coordinates_follow():
    cam = Camera(G, VW, VH)
    cam.reset((-50, -50))
    assert cam.current_x == pytest.approx(-50 * G + G / 2)

    head = place(cam, 7, cell=(-50, -50))
    cam.update(1 / 60, head)
    assert cam.target_x > cam.current_x
    assert cam.viewport().origin_x == pytest.approx(cam.current_x - HALF_W)


def test_viewport_origin_follows_camera():
    cam = make_camera()
    cam.update(1 / 60, place(cam, 8))
    vp = cam.viewport()
    assert vp.origin_x == pytest.approx(cam.current_x - HALF_W)
    assert vp.origin_y == pytest.approx(cam.current_y - HALF_H)


def test_negative_dt_does_not_move():
    cam = make_camera()
    head = place(cam, 8)
    cam.update(1 / 60, head)
    x_after = cam.current_x
    cam.update(-1.0, head)
    assert cam.current_x == pytest.approx(x_after)


# ---------- 滞回边界（精确构造，避免浮点误差） ----------
def test_exit_exactly_at_twelve():
    """d == 12.0 → 解除（解除条件为 d >= 10+2）。"""
    cam = make_camera()
    cam.update(1 / 60, place(cam, 8))
    assert cam.armed_x is True

    head = place(cam, 12.0)
    assert cam.current_x == pytest.approx(16 + 12.0 * G - HALF_W)  # 构造校验
    cam.update(1 / 60, head)
    assert cam.armed_x is False


def test_frozen_just_inside_twelve():
    """d == 11.999 → 仍在滞回带内：保持 armed 且 target 冻结。"""
    cam = make_camera()
    cam.update(1 / 60, place(cam, 8))
    frozen = cam.target_x

    head = place(cam, 11.999)
    cam.update(1 / 60, head)
    assert cam.armed_x is True
    assert cam.target_x == pytest.approx(frozen)


def test_exit_just_outside_twelve():
    """d == 12.001 → 解除。"""
    cam = make_camera()
    cam.update(1 / 60, place(cam, 8))
    head = place(cam, 12.001)
    cam.update(1 / 60, head)
    assert cam.armed_x is False
