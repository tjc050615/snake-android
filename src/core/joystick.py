"""虚拟摇杆 / 滑动转向（纯逻辑，M4/R1，无 Kivy 依赖）。

规则：
- 摇杆死区 15%（D-012）：归一化位移 < deadzone → 不产生方向
- 四向转向：按主轴取方向（水平位移绝对值更大就左右，否则上下）
- 滑动：从按下点位移超过 swipe_px 才判定，方向同上
"""

from __future__ import annotations

DEADZONE = 0.15


class Joystick:
    def __init__(self, deadzone: float = DEADZONE, swipe_px: float = 36.0, radius_px: float = 90.0) -> None:
        self.deadzone = deadzone
        self.swipe_px = swipe_px
        self.radius_px = radius_px
        self.active = False
        self.origin: tuple[float, float] | None = None
        self.current: tuple[float, float] | None = None
        self._last_direction: tuple[int, int] | None = None

    # ---------- 生命周期 ----------
    def begin(self, x: float, y: float) -> None:
        self.active = True
        self.origin = (x, y)
        self.current = (x, y)
        self._last_direction = None

    def move(self, x: float, y: float) -> tuple[int, int] | None:
        if not self.active:
            return None
        self.current = (x, y)
        return self.direction()

    def end(self) -> tuple[int, int] | None:
        self.active = False
        self.origin = None
        self.current = None
        self._last_direction = None
        return None

    # ---------- 数值 ----------
    def vector(self) -> tuple[float, float]:
        """归一化位移向量（以 radius_px 为满量程）。"""
        if self.origin is None or self.current is None:
            return (0.0, 0.0)
        dx = self.current[0] - self.origin[0]
        dy = self.current[1] - self.origin[1]
        return (dx / self.radius_px, dy / self.radius_px)

    def magnitude(self) -> float:
        vx, vy = self.vector()
        return (vx * vx + vy * vy) ** 0.5

    def direction(self) -> tuple[int, int] | None:
        """返回四向方向；死区内或未达滑动阈值返回 None。"""
        if self.origin is None or self.current is None:
            return None
        dx = self.current[0] - self.origin[0]
        dy = self.current[1] - self.origin[1]
        dist = (dx * dx + dy * dy) ** 0.5

        # 死区用归一化量程判定；滑动用像素阈值判定（两者取其一满足即可）
        if self.magnitude() < self.deadzone and dist < self.swipe_px:
            return None

        if abs(dx) >= abs(dy):
            direction = (1, 0) if dx > 0 else (-1, 0)
        else:
            direction = (0, 1) if dy > 0 else (0, -1)

        if direction == self._last_direction:
            return None  # 同一方向只发一次，避免每帧重复
        self._last_direction = direction
        return direction
