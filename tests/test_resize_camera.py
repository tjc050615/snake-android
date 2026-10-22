"""M4/R3：resize 相机换算（KI-005）。"""

from core.camera import Camera, rescale_for_grid


class _FakeCam:
    current_x = 10.0
    current_y = -4.0
    target_x = 12.0
    target_y = -2.0


def test_rescale_camera_keeps_world_position():
    cam = _FakeCam()
    rescale_for_grid(cam, 48.0, 64.0)   # 网格放大 4/3
    assert abs(cam.current_x - 10.0 * 64 / 48) < 1e-9
    assert abs(cam.current_y - (-4.0) * 64 / 48) < 1e-9
    assert abs(cam.target_x - 12.0 * 64 / 48) < 1e-9


def test_rescale_ignores_invalid_grid():
    cam = _FakeCam()
    before = (cam.current_x, cam.target_y)
    rescale_for_grid(cam, 0, 64)
    rescale_for_grid(cam, -1, 64)
    assert (cam.current_x, cam.target_y) == before


def test_rescale_real_camera():
    cam = Camera(48, 800, 600, target_x=3.0 * 48, target_y=3.0 * 48,
                 current_x=3.0 * 48, current_y=3.0 * 48)
    rescale_for_grid(cam, 48.0, 96.0)
    # 相机存像素坐标：世界格 3 在 96px/格 下是 288px
    assert abs(cam.current_x - 288.0) < 1e-6
    assert abs(cam.target_y - 288.0) < 1e-6
