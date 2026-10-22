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
from app.fonts import font_name
from core.camera import Camera
from core.game import Game
from core.interp import segment_cells, to_pixel
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
        self.wrap_rect = (0.0, 0.0, 0.0, 0.0)  # HUD 穿墙开关的可点击矩形
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
            self._apply_metrics()
            self.rebuild()

    # ---------- 计算 ----------
    def _apply_metrics(self) -> None:
        density = desktop.get_density()
        try:
            self.grid_size = fit_grid_size(density, self.width, self.height)
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
    def rebuild(self) -> None:
        self.canvas.clear()
        vp = self.viewport
        if vp is None:
            return

        g = vp.grid_size
        with self.canvas:
            Color(*BG_COLOR)
            Rectangle(pos=self.pos, size=self.size)

            Color(*GRID_COLOR)
            x0, y0, x1, y1 = vp.visible_bounds()
            for gx in range(x0, x1 + 1):
                sx = gx * g - vp.origin_x
                Line(points=[sx, 0, sx, self.height], width=1)
            for gy in range(y0, y1 + 1):
                sy = gy * g - vp.origin_y
                Line(points=[0, sy, self.width, sy], width=1)

            Color(*FOOD_COLOR)
            food = g * 0.5
            pad = (g - food) / 2.0
            for cell in vp.iter_visible_cells():
                if self.game.world.has_food(cell):
                    rx, ry, _w, _h = vp.cell_rect(cell)
                    Ellipse(pos=(rx + pad, ry + pad), size=(food, food))

            # 障碍与墙壁（R3）：只画视口内；墙壁用暖色 + 内缩边框区分
            from core.world import BLOCK_WALL

            Color(*OBSTACLE_COLOR)
            for cell in vp.iter_visible_cells():
                if self.game.world.is_blocked(cell) and self.game.world.block_kind(cell) != BLOCK_WALL:
                    rx, ry, w, h = vp.cell_rect(cell)
                    Rectangle(pos=(rx + 2, ry + 2), size=(w - 4, h - 4))

            Color(*WALL_COLOR)
            for cell in vp.iter_visible_cells():
                if self.game.world.block_kind(cell) == BLOCK_WALL:
                    rx, ry, w, h = vp.cell_rect(cell)
                    Rectangle(pos=(rx + 1, ry + 1), size=(w - 2, h - 2))

            # 蛇身：浮点格坐标 → 像素，矩形以格中心为锚点
            cells = segment_cells(self.game.snake, self.game.tick_progress)
            pad_snake = 1.0

            Color(*BODY_COLOR)
            for cell in cells[1:]:
                px, py = to_pixel(cell, g, vp.origin_x, vp.origin_y)
                if -g <= px <= self.width + g and -g <= py <= self.height + g:
                    Rectangle(
                        pos=(px - g / 2 + pad_snake, py - g / 2 + pad_snake),
                        size=(g - 2 * pad_snake, g - 2 * pad_snake),
                    )

            Color(*HEAD_COLOR)
            hx, hy = to_pixel(cells[0], g, vp.origin_x, vp.origin_y)
            Rectangle(
                pos=(hx - g / 2 + pad_snake, hy - g / 2 + pad_snake),
                size=(g - 2 * pad_snake, g - 2 * pad_snake),
            )

            if self.game.state == "dead":
                Color(*DEAD_TINT)
                Rectangle(pos=self.pos, size=self.size)

            if self._status_text:
                self._draw_status_text()

            self._draw_hud()

    def _draw_hud(self) -> None:
        """左上角穿墙开关：CoreLabel 纹理绘制（Button 的中文渲染不出字形）。"""
        text = strings.t("wrap_on" if self.game.wrap_mode else "wrap_off")
        label = CoreLabel(
            text=text,
            font_size=22,
            font_name=font_name() or "Roboto",
            color=(1, 1, 1, 1),
        )
        label.refresh()
        tex = label.texture
        pad = 8
        w, h = tex.width + pad * 2, tex.height + pad * 2
        x, y = 12.0, self.height - h - 12.0
        self.wrap_rect = (x, y, w, h)
        Color(0.20, 0.22, 0.26, 1)
        Rectangle(pos=(x, y), size=(w, h))
        Color(1, 1, 1, 1)
        Rectangle(texture=tex, size=tex.size, pos=(x + pad, y + pad))
