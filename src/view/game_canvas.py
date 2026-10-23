"""R4 渲染：网格 + 食物 + 插值蛇身 + 死亡叠层。

插值 t 只来自 `Game.tick_progress`（内部是 TickClock.progress），死亡冻结 1.0。
几何全部交给 `core.interp`，渲染器不做数学。
"""

from __future__ import annotations

from kivy.clock import Clock, ClockEvent
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.logger import Logger
from kivy.uix.widget import Widget

from app import constants as C
from app import strings
from app.theme import palette
from core.colors import background_color, gradient_pair, snake_gradient
from view.gradient_bg import gradient_texture
from view.grid_tex import grid_tex_coords, grid_texture
from app.fonts import font_name
from core.camera import Camera
from core.game import Game
from core.interp import segment_cells, to_pixel
from core.joystick import Joystick
from core.scale import fit_grid_size
from core.viewport import Viewport
from platform_layer import desktop

BG_COLOR = (0.09, 0.10, 0.12, 1)
GRID_COLOR = (0.16, 0.17, 0.20, 1)
FOOD_COLOR = (0.95, 0.55, 0.25, 1)
BODY_COLOR = (0.24, 0.78, 0.44, 1)
HEAD_COLOR = (0.55, 1.00, 0.66, 1)
OBSTACLE_COLOR = (0.42, 0.44, 0.50, 1)
WALL_COLOR = (0.72, 0.58, 0.30, 1)
DEAD_TINT = (0.45, 0.06, 0.10, 0.45)


class GameCanvas(Widget):
    def __init__(self, game: Game, **kwargs) -> None:
        super().__init__(**kwargs)
        self.game = game
        self.grid_size = C.GRID_SIZE_BASE
        self.viewport: Viewport | None = None
        self.camera: Camera | None = None
        self.too_small = False
        self._resize_event: ClockEvent | None = None
        self.ai_path: list[tuple[int, int]] = []  # M3：AI 路径（半透明折线）
        self.overlay_text = ""                    # 暂停倒计时 / 回放提示
        self.bg_mode = "solid"
        self.bg_index = 0
        self.snake_hue = 0.33
        self.view_zoom = 1.0
        from kivy.graphics import InstructionGroup
        self._static = InstructionGroup()
        self.canvas.before.add(self._static)
        self._static_dirty = True
        self._cells_buf: list = []                 # R5A：蛇身插值缓冲复用
        self.colors = palette("dark")
        self.show_grid = True
        self.head_highlight = True
        self._joystick = Joystick(swipe_px=30.0)
        self._joy_origin = None
        self.joy_radius = 90.0
        self.on_direction = None          # 回调：direction -> None
        self._touch_uid = None
        self._status_text = ""

        self.bind(size=self._on_resize)
        Clock.schedule_once(self._first_build, 0)

    # ---------- 生命周期 ----------
    def _first_build(self, _dt: float) -> None:
        self._apply_metrics()
        self.rebuild()

    def _on_resize(self, *_args) -> None:
        """下一帧执行（delay=0）；连续 resize 取消上一次。"""
        if self._resize_event is not None:
            self._resize_event.cancel()
        self._resize_event = Clock.schedule_once(self._rebuild_after_resize, 0)

    def _rebuild_after_resize(self, _dt: float) -> None:
        self._resize_event = None
        if self.width > 0 and self.height > 0:
            self._static_dirty = True   # 尺寸变了，背景缓存必须重建
            self._apply_metrics()
            self.rebuild()

    # ---------- 计算 ----------
    def _apply_metrics(self) -> None:
        if self.width < 300 or self.height < 300:
            return   # 初始布局阶段：等真实尺寸再建相机，避免 100x100 警告
        density = desktop.get_density()
        try:
            self.grid_size = fit_grid_size(density / self.view_zoom, self.width, self.height)
            self.too_small = False
        except ValueError as exc:
            self.grid_size = C.GRID_SIZE_MIN
            self.too_small = True
            Logger.warning(
                "Snake: viewport too small (%.0fx%.0f px): %s; fallback grid_size=%d",
                self.width,
                self.height,
                exc,
                self.grid_size,
            )

        if self.camera is None:
            self.camera = Camera(self.grid_size, self.width, self.height)
            self.camera.reset(self.game.snake.head)
        else:
            self.camera.resize(self.grid_size, self.width, self.height)
        self.viewport = self.camera.viewport()

    def advance(self, dt: float) -> bool:
        if self.camera is None or self.viewport is None:
            return False
        bx, by = self.camera.current_x, self.camera.current_y
        self.camera.update(dt, self.game.snake.head)
        moved = abs(self.camera.current_x - bx) + abs(self.camera.current_y - by) >= 0.5
        if moved:
            self.viewport = self.camera.viewport()
        return moved

    def _draw_status_text(self) -> None:
        label = CoreLabel(
            text=self._status_text,
            font_size=34,
            halign="center",
            valign="middle",
            color=(1, 0.86, 0.86, 1),
            font_name=font_name() or "Roboto",
        )
        label.refresh()
        tex = label.texture
        Color(1, 1, 1, 1)
        Rectangle(
            texture=tex,
            size=tex.size,
            pos=(self.center_x - tex.width / 2, self.center_y - tex.height / 2),
        )

    def head_screen_pos(self) -> tuple[float, float]:
        """蛇头（整格）在屏幕上的像素位置，用于"是否出屏"断言。"""
        vp = self.viewport
        if vp is None:
            return (0.0, 0.0)
        g = vp.grid_size
        hx, hy = self.game.snake.head
        return (hx * g + g / 2.0 - vp.origin_x, hy * g + g / 2.0 - vp.origin_y)

    def metrics(self) -> dict[str, object]:
        vp = self.viewport
        if vp is None or self.camera is None:
            return {"grid_size": self.grid_size, "cols": 0, "rows": 0, "too_small": self.too_small}
        x0, y0, x1, y1 = vp.visible_bounds()
        sx, sy = self.head_screen_pos()
        inside = 0.0 <= sx <= vp.width and 0.0 <= sy <= vp.height
        return {
            "grid_size": self.grid_size,
            "cols": x1 - x0,
            "rows": y1 - y0,
            "too_small": self.too_small,
            "width": vp.width,
            "height": vp.height,
            "cam_current": (self.camera.current_x, self.camera.current_y),
            "cam_target": (self.camera.target_x, self.camera.target_y),
            "cam_armed": (self.camera.armed_x, self.camera.armed_y),
            "head_screen": (sx, sy),
            "head_inside": inside,
            "progress": self.game.tick_progress,
        }

    # ---------- 死亡态 ----------
    def show_game_over(self, score: int) -> None:
        self._status_text = "\n".join(
            (
                strings.t("game_over"),
                f"{strings.t('score')} {score}",
                strings.t("restart_hint"),
            )
        )
        self.rebuild()

    def hide_game_over(self) -> None:
        self._status_text = ""

    # ---------- 绘制 ----------
    def _rebuild_static(self) -> None:
        """背景层缓存：只在 resize / 主题 / 背景变化时重建（不再每帧重画）。"""
        from core.colors import background_color, gradient_pair
        from kivy.graphics import Color, Rectangle

        self._static.clear()
        if self.bg_mode == "gradient":
            top, bottom = gradient_pair(self.bg_index)
            bands = 40
            for i in range(bands):
                t = i / (bands - 1)
                self._static.add(Color(
                    top[0] + (bottom[0] - top[0]) * t,
                    top[1] + (bottom[1] - top[1]) * t,
                    top[2] + (bottom[2] - top[2]) * t, 1,
                ))
                self._static.add(Rectangle(
                    pos=(self.x, self.y + self.height * (bands - 1 - i) / bands),
                    size=(self.width, self.height / bands + 1),
                ))
        else:
            r, g, b = background_color(self.bg_index)
            self._static.add(Color(r, g, b, 1))
            self._static.add(Rectangle(pos=self.pos, size=self.size))
        self._static_dirty = False

    def rebuild(self) -> None:
        self.canvas.clear()
        vp = self.viewport
        if vp is None:
            return

        if self._static_dirty:
            self._rebuild_static()

        g = vp.grid_size
        with self.canvas:
            if self.show_grid:
                # 单张 16x16 平铺纹理：整屏网格 1 个 draw call（不再逐条 Line）
                Color(*self.colors["grid"])
                Rectangle(texture=grid_texture(), pos=self.pos, size=self.size,
                          tex_coords=grid_tex_coords(vp.origin_x, vp.origin_y, g,
                                                     self.width, self.height))

            Color(*self.colors["food"])
            food = g * 0.5
            pad = (g - food) / 2.0
            for cell in vp.iter_visible_cells():
                if self.game.world.has_food(cell):
                    rx, ry, _w, _h = vp.cell_rect(cell)
                    Ellipse(pos=(rx + pad, ry + pad), size=(food, food))

            # 障碍与墙壁（R3）：只画视口内；墙壁用暖色 + 内缩边框区分
            from core.world import BLOCK_WALL

            Color(*self.colors["obstacle"])
            for cell in vp.iter_visible_cells():
                if self.game.world.is_blocked(cell) and self.game.world.block_kind(cell) != BLOCK_WALL:
                    rx, ry, w, h = vp.cell_rect(cell)
                    Rectangle(pos=(rx + 2, ry + 2), size=(w - 4, h - 4))

            Color(*self.colors["wall"])
            for cell in vp.iter_visible_cells():
                if self.game.world.block_kind(cell) == BLOCK_WALL:
                    rx, ry, w, h = vp.cell_rect(cell)
                    Rectangle(pos=(rx + 1, ry + 1), size=(w - 2, h - 2))

            # AI 路径：隔格画小圆点（虚线效果），无 dash 兼容性问题
            if self.ai_path:
                path_color = self.colors.get("path", (0.45, 0.75, 1.0, 0.35))
                Color(path_color[0], path_color[1], path_color[2], min(0.75, path_color[3] + 0.25))
                dot = max(2.0, g * 0.16)
                for idx, cell in enumerate(self.ai_path):
                    if idx % 2:          # 隔一格，形成虚线节奏
                        continue
                    if not vp.covers(cell):
                        continue
                    px, py = to_pixel((float(cell[0]), float(cell[1])), g,
                                      vp.origin_x, vp.origin_y)
                    Ellipse(pos=(px - dot / 2, py - dot / 2), size=(dot, dot))

            # 蛇身：浮点格坐标 → 像素，矩形以格中心为锚点
            cells = segment_cells(self.game.snake, self.game.tick_progress, self._cells_buf)
            pad_snake = 1.0

            grad = snake_gradient(len(cells), self.snake_hue)
            # 对比度检查：蛇头颜色与背景亮度差 < 0.22 时，逐节加白色描边
            if self.bg_mode == "gradient":
                a, b = gradient_pair(self.bg_index)
                bg_rgb = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2)
            else:
                bg_rgb = background_color(self.bg_index)
            bg_lum = 0.299 * bg_rgb[0] + 0.587 * bg_rgb[1] + 0.114 * bg_rgb[2]
            head_lum = 0.299 * grad[0][0] + 0.587 * grad[0][1] + 0.114 * grad[0][2]
            low_contrast = abs(head_lum - bg_lum) < 0.22

            # 整条蛇 = 1 条折线（round cap/joint）+ 1 个圆头
            points: list[float] = []
            for cell in cells:
                px, py = to_pixel(cell, g, vp.origin_x, vp.origin_y)
                points.extend((px, py))
            if len(points) >= 4:
                mid = grad[len(grad) // 2]
                Color(mid[0], mid[1], mid[2], 1)
                Line(points=points, width=g * 0.60, cap="round", joint="round")

            Color(grad[0][0], grad[0][1], grad[0][2], 1)
            hx, hy = to_pixel(cells[0], g, vp.origin_x, vp.origin_y)
            Ellipse(
                pos=(hx - g / 2 + pad_snake, hy - g / 2 + pad_snake),
                size=(g - 2 * pad_snake, g - 2 * pad_snake),
            )
            if self.head_highlight or low_contrast:
                # 可访问性 / 低对比度兜底：蛇头外圈白色描边
                Color(1.0, 1.0, 1.0, 0.9)
                Line(rectangle=(hx - g / 2 + 1, hy - g / 2 + 1, g - 2, g - 2), width=2)

            if low_contrast:
                # 纯色/渐变与蛇身颜色接近时，逐节描白边，确保绝对可见
                Color(1.0, 1.0, 1.0, 0.75)
                for idx in range(1, len(cells)):
                    px, py = to_pixel(cells[idx], g, vp.origin_x, vp.origin_y)
                    Line(rectangle=(px - g / 2 + 1, py - g / 2 + 1, g - 2, g - 2), width=1)

            if self.game.state == "dead":
                Color(*self.colors["dead_tint"])
                Rectangle(pos=self.pos, size=self.size)

            if self._status_text:
                self._draw_status_text()

            self._draw_joystick()
            if self.overlay_text:
                self._draw_overlay_text()

    # ---------- 触控（M4/R1）：游戏区内摇杆/滑动，面板区由 Panel 自己消费 ----------
    def on_touch_down(self, touch) -> bool:
        if not self.collide_point(*touch.pos):
            return False
        # 全屏动态摇杆：手指落点即摇杆中心
        self._joy_origin = (touch.x, touch.y)
        self._joystick.begin(touch.x, touch.y)
        self._touch_uid = touch.uid
        return True

    def on_touch_move(self, touch) -> bool:
        if touch.uid != self._touch_uid:
            return False
        d = self._joystick.move(touch.x, touch.y)
        if d is not None and self.on_direction is not None:
            self.on_direction(d)
        return True

    def on_touch_up(self, touch) -> bool:
        if touch.uid != self._touch_uid:
            return False
        self._joystick.end()
        self._joy_origin = None
        self._touch_uid = None
        return True

    def on_size(self, *args) -> None:
        """窗口 resize：按格子尺寸比例换算相机，避免画面漂移（KI-005）。

        修复闪退：Widget 没有 on_size，调用 super().on_size() 会 AttributeError；
        极小尺寸直接返回，避免 0 尺寸下建 viewport。
        """
        if self.width < 300 or self.height < 300:
            return
        cam = getattr(self, "camera", None)
        vp = getattr(self, "viewport", None)
        if cam is None or vp is None or self.width <= 0 or self.height <= 0:
            return
        from core.camera import rescale_for_grid

        old = vp.grid_size
        from platform_layer import desktop

        new = fit_grid_size(desktop.get_density() / self.view_zoom, self.width, self.height)
        if new != old:
            rescale_for_grid(cam, old, new)
            self.rebuild()

    def set_view_zoom(self, zoom: float) -> None:
        """广角镜头：zoom 越大格子越小、可见范围越大（1x~4x）。"""
        self.view_zoom = max(1.0, min(4.0, float(zoom)))
        if self.width > 0 and self.height > 0:
            self._apply_metrics()
        self.rebuild()

    # 兼容旧调用
    def set_view_scale(self, scale: float) -> None:
        self.set_view_zoom(scale)

    def set_background(self, mode: str, index: int) -> None:
        """背景选择：solid / gradient，index 0~15（实时重建）。"""
        self.bg_mode = "gradient" if mode == "gradient" else "solid"
        self.bg_index = int(index) % 16
        self._static_dirty = True
        self.rebuild()

    def set_theme(self, name: str) -> None:
        self.colors = palette(name)
        self._static_dirty = True
        self.rebuild()

    def apply_view_options(self, show_grid: bool, head_highlight: bool) -> None:
        self.show_grid = bool(show_grid)
        self.head_highlight = bool(head_highlight)
        self.rebuild()

    def _draw_overlay_text(self) -> None:
        label = CoreLabel(text=self.overlay_text, font_size=40,
                          font_name=font_name() or "Roboto", color=(1, 1, 0.8, 1))
        label.refresh()
        tex = label.texture
        Color(1, 1, 1, 1)
        Rectangle(texture=tex, size=tex.size,
                  pos=(self.center_x - tex.width / 2, self.center_y - tex.height / 2))

    # ---------- 虚拟摇杆（M4/R1） ----------
    def joystick_center(self) -> tuple[float, float]:
        if self._joy_origin is not None:
            return self._joy_origin
        r = self.joy_radius
        return (r + 24.0, r + 24.0)

    def _draw_joystick(self) -> None:
        if not self._joystick.active:
            return   # 松手后摇杆消失
        cx, cy = self.joystick_center()
        r = self.joy_radius
        Color(1, 1, 1, 0.12)
        Line(circle=(cx, cy, r), width=2)
        vx, vy = self._joystick.vector()
        mag = (vx * vx + vy * vy) ** 0.5
        if mag > 1.0:
            vx, vy = vx / mag, vy / mag
        Color(1, 1, 1, 0.28)
        Line(circle=(cx + vx * r * 0.6, cy + vy * r * 0.6, r * 0.35), width=2)
