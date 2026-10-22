"""Kivy 应用入口（R5：M1 验收）。

命令行：
    python main.py                          正常游玩
    python main.py --smoke 12               12 秒后退出并打印诊断（≈120 tick）
    python main.py --smoke 12 --speed 10    10x 高速档
    python main.py --smoke 4 --demo         吃食物 + 死亡叠层截图
    python main.py --smoke 3 --interp       连续 3 帧插值截图
    python main.py --smoke 2 --size 800x480 指定物理分辨率并截一张图
    python main.py --smoke 5 --hyst         死区边界来回 6 帧（滞回证据）
"""

from __future__ import annotations

import os

import kivy
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.metrics import Metrics

from app import constants as C
from core.game import Game
from core.snake import DIR_DOWN, DIR_LEFT, DIR_RIGHT, DIR_UP, Snake
from platform_layer import desktop
from view.game_canvas import GameCanvas

DEFAULT_SEED = 20261022
FRAME_INTERVAL = 1.0 / 60.0
EVIDENCE_DIR = os.path.join("docs", "evidence")

KEYMAP = {
    273: DIR_UP,
    274: DIR_DOWN,
    275: DIR_LEFT,
    276: DIR_RIGHT,
    119: DIR_UP,      # w
    115: DIR_DOWN,    # s
    97: DIR_LEFT,     # a
    100: DIR_RIGHT,   # d
}
KEY_RESTART = 114  # r


class SnakeApp(App):
    title = "Snake — M1/R5"
    smoke_seconds = 0.0
    demo = False
    interp = False
    hyst = False
    speed = 1.0
    window_size: tuple[int, int] | None = None

    # ---------- 构建 ----------
    def build(self) -> GameCanvas:
        self._apply_window_size()
        self.game = Game(DEFAULT_SEED)
        self.game.clock.set_speed(self.speed)
        self._foods0 = self.game.world.food_count()
        self._rebuilds_after_death = 0
        self.canvas_widget = GameCanvas(self.game)

        Window.bind(on_key_down=self._on_key_down)
        Clock.schedule_interval(self._frame, FRAME_INTERVAL)

        if self.smoke_seconds > 0:
            self._t0 = Clock.get_time()
            Clock.schedule_once(self._smoke_report, 0.3)
            for idx, frac in enumerate((0.25, 0.5, 0.75), start=1):
                if self.demo or self.hyst:
                    break
                delay = max(0.8, self.smoke_seconds * frac)
                Clock.schedule_once(lambda _dt, i=idx: self._shot(f"follow{i}"), delay)
            if self.window_size is not None:
                w, h = self.window_size
                Clock.schedule_once(lambda _dt: self._shot(f"res{w}x{h}"), 1.0)
            if self.demo:
                self._schedule_demo()
            if self.hyst:
                self._schedule_hyst()
            if self.interp:
                for i in range(3):
                    Clock.schedule_once(
                        lambda _dt, k=i: self._shot(f"interp{k + 1}"),
                        1.0 + i * 2 * FRAME_INTERVAL,
                    )
            Clock.schedule_once(self._smoke_final, max(0.5, self.smoke_seconds - 0.05))
            Clock.schedule_once(lambda _dt: self.stop(), self.smoke_seconds)
        return self.canvas_widget

    def _apply_window_size(self) -> None:
        if desktop.is_android():
            return
        target = self.window_size if self.window_size else (1280, 720)
        density = desktop.get_density() or 1.0
        # Kivy 在 Windows 上会再乘一次 DPI，这里先除回去，保证"物理像素"符合预期
        Window.size = (int(target[0] / density), int(target[1] / density))

    # ---------- 主循环 ----------
    def _frame(self, dt: float) -> None:
        summary = self.game.update(dt)
        camera_moved = self.canvas_widget.advance(dt)
        if (
            self.game.state == "running"
            or summary.ticks
            or summary.died
            or camera_moved     # 死亡后相机仍在滑动时也必须重绘
        ):
            self.canvas_widget.rebuild()
            if self.game.state == "dead":
                self._rebuilds_after_death += 1
        if summary.died:
            self.canvas_widget.show_game_over(self.game.score)

    # ---------- 输入 ----------
    def _on_key_down(self, _window, key, _scancode, _codepoint, _modifiers) -> bool:
        direction = KEYMAP.get(key)
        if direction is not None:
            return self.game.set_direction(direction)
        if key == KEY_RESTART:
            self._restart()
            return True
        return False

    def _restart(self) -> None:
        self.game.reset(self.game.seed)
        self.game.clock.set_speed(self.speed)
        if self.canvas_widget.camera is not None:
            self.canvas_widget.camera.reset(self.game.snake.head)
            self.canvas_widget.viewport = self.canvas_widget.camera.viewport()
        self.canvas_widget.hide_game_over()
        self.canvas_widget.rebuild()

    # ---------- 演示：吃食物 / 死亡 ----------
    def _schedule_demo(self) -> None:
        Clock.schedule_once(self._demo_feed, 0.6)
        Clock.schedule_once(lambda _dt: self._shot("eat"), 1.4)
        Clock.schedule_once(self._demo_die, 2.0)
        Clock.schedule_once(self._demo_nudge_head, 2.3)
        Clock.schedule_once(lambda _dt: self._shot("dead"), 2.6)

    def _demo_feed(self, _dt: float) -> None:
        head = self.game.snake.head
        d = self.game.snake.direction
        self.game.world._foods.add((head[0] + d[0], head[1] + d[1]))  # noqa: SLF001

    def _demo_die(self, _dt: float) -> None:
        self.game.snake = Snake([(0, 0), (1, 0), (1, -1), (0, -1), (-1, -1)], DIR_DOWN)
        if self.canvas_widget.camera is not None:
            self.canvas_widget.camera.reset((0, 0))

    def _demo_nudge_head(self, _dt: float) -> None:
        """死亡后把蛇头挪远：相机会继续滑动，用于验证"死亡后仍重绘"。"""
        head = self.game.snake.head
        self.game.snake.body[0] = (head[0] - 25, head[1])

    # ---------- 演示：滞回边界来回 ----------
    def _schedule_hyst(self) -> None:
        """真实走位（不瞬移）：右 → 上 → 左（退到 >12 解除）→ 下 → 右（回到 ≤10 重新进入）。

        转向之间至少留 7 个 Tick，避免"同一 Tick 内连续按键后者覆盖前者"导致
        从左转直接掉头撞自己（D-058 的已知语义）。
        """
        turns = ((0.5, DIR_UP), (1.2, DIR_LEFT), (3.2, DIR_DOWN), (3.6, DIR_RIGHT))
        for at, direction in turns:
            Clock.schedule_once(lambda _dt, d=direction: self.game.set_direction(d), at)
        for i in range(6):
            Clock.schedule_once(lambda _dt, k=i: self._hyst_log(k), 0.8 + i * 0.8)

    def _hyst_log(self, step: int) -> None:
        cam = self.canvas_widget.camera
        g = cam.grid_size
        head = self.game.snake.head[0] * g + g / 2.0
        d_left = (head - (cam.current_x - cam.view_width / 2.0)) / g
        d_right = ((cam.current_x + cam.view_width / 2.0) - head) / g
        print(
            f"[HYST] step={step} dir={self.game.snake.direction} d_left={d_left:.2f} d_right={d_right:.2f} "
            f"armed_x={cam.armed_x} cur_x={cam.current_x:.1f} target_x={cam.target_x:.1f}"
        )
        self._shot(f"hyst{step + 1}")

    # ---------- 截图 ----------
    def _shot(self, name: str) -> None:
        os.makedirs(EVIDENCE_DIR, exist_ok=True)
        if not name.endswith(".png"):
            name += ".png"
        try:
            path = Window.screenshot(name=os.path.join(EVIDENCE_DIR, name))
            print(f"[SMOKE] shot         = {os.path.basename(str(path))} (t~{Clock.get_time() - self._t0:.2f}s)")
            self._log_interp()
        except Exception as exc:  # pragma: no cover
            Logger.warning("Snake: screenshot failed: %s", exc)

    def _log_interp(self) -> None:
        from core.interp import segment_cells  # noqa: PLC0415

        cells = segment_cells(self.game.snake, self.game.tick_progress)
        head = cells[0]
        print(
            "[SMOKE] progress     = "
            f"{self.game.tick_progress:.3f} head_cell=({head[0]:.3f}, {head[1]:.3f})"
        )

    # ---------- 诊断 ----------
    def _smoke_report(self, _dt: float) -> None:
        m = self.canvas_widget.metrics()
        print("[SMOKE] kivy          =", kivy.__version__)
        print("[SMOKE] window        =", f"{Window.width:.0f}x{Window.height:.0f}", "px")
        print("[SMOKE] density       =", Metrics.density)
        print("[SMOKE] grid_size     =", m["grid_size"])
        print("[SMOKE] viewport cells=", f"{m['cols']}x{m['rows']}", "(>=21:", not m["too_small"], ")")
        print("[SMOKE] too_small     =", m["too_small"])
        print("[SMOKE] speed         =", f"{self.speed}x (interval {self.game.clock.interval*1000:.1f}ms)")
        print("[SMOKE] chunks        =", len(self.game.world._chunks))  # noqa: SLF001
        print("[SMOKE] foods         =", f"{self._foods0} -> {self.game.world.food_count()}",
              "eaten=", self.game.score)
        print("[SMOKE] snake         =", f"len={len(self.game.snake)} head={self.game.snake.head} dir={self.game.snake.direction}")
        print("[SMOKE] state/ticks   =", self.game.state, "ticks=", self.game.ticks)
        print("[SMOKE] camera        =", f"cur={m['cam_current']} tgt={m['cam_target']} armed={m['cam_armed']}")
        print("[SMOKE] head_screen   =", f"{tuple(round(v, 1) for v in m['head_screen'])} inside={m['head_inside']}")
        print("[SMOKE] seed          =", self.game.seed)
        print("[SMOKE] exit scheduled=", self.smoke_seconds, "s")

    def _smoke_final(self, _dt: float) -> None:
        m = self.canvas_widget.metrics()
        print("[SMOKE] ---- final ----")
        print("[SMOKE] ticks         =", self.game.ticks)
        print("[SMOKE] state         =", self.game.state)
        print("[SMOKE] speed         =", self.speed)
        print("[SMOKE] eaten(foods)  =", f"{self._foods0} -> {self.game.world.food_count()}, eaten={self.game.score}")
        print("[SMOKE] snake         =", f"len={len(self.game.snake)} head={self.game.snake.head}")
        print("[SMOKE] camera        =", f"cur={m['cam_current']} tgt={m['cam_target']} armed={m['cam_armed']}")
        print("[SMOKE] head_screen   =", f"{tuple(round(v, 1) for v in m['head_screen'])} inside={m['head_inside']}")
        print("[SMOKE] progress      =", f"{m['progress']:.3f}")
        print("[SMOKE] dead_rebuilds =", self._rebuilds_after_death)
        if self.canvas_widget._status_text:  # noqa: SLF001
            print("[SMOKE] label         =", repr(self.canvas_widget._status_text.replace("\n", " | ")))  # noqa: SLF001
