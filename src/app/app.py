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

from kivy.uix.floatlayout import FloatLayout

from ai.session import AISession

from app import constants as C
from app import strings
from app.theme import palette
from app.fonts import font_name, register_fonts
from core.chunk_manager import ChunkManager
from data.crash import CrashGuard
from data.debounce import DebouncedSaver
from data.profile import ProfileStore
from data.storage import ConfigStore
from core.game import Game
from core.snake import DIR_DOWN, DIR_LEFT, DIR_RIGHT, DIR_UP, Snake
from platform_layer import desktop
from view.game_canvas import GameCanvas
from view.panel import Panel
from core.pause import PauseGate
from data.onboarding import mark_done, should_show
from core.debug import DebugStats
from core.audio import Haptics, SoundManager
from core.confirm import ConfirmState
from core.replay_controls import ReplayControls
from data.achievements import evaluate
from view.confirm_dialog import ConfirmDialog
from view.debug_overlay import DebugOverlay
from view.replay_panel import ReplayPanel
from view.stats_panel import StatsPanel
from view.history_panel import HistoryPanel
from view.info_panel import AchievementPanel, OnboardingPanel
from view.settings_panel import SettingsOverlay

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
    _save_event = None
    demo = False
    interp = False
    hyst = False
    speed = 1.0
    window_size: tuple[int, int] | None = None
    obstacle_shot = False
    wall_shot = False
    wrap = False
    wrap_scene = False
    spawn_shot = False
    ai = False
    clip_demo = False
    settings_shot = False
    history_shot = False
    ach_shot = False
    onboard_shot = False
    pause_shot = False
    replay_shot = False
    stats_shot = False
    debug_shot = False
    replayui_shot = False
    confirm_shot = False
    theme_override: str | None = None
    font_override: float | None = None

    # ---------- 构建 ----------
    def build(self) -> GameCanvas:
        register_fonts()  # Kivy 默认字体不含中文，必须先注册随包字体
        self._apply_window_size()
        self.store = ConfigStore()
        self.cfg = self.store.load()
        self.saver = DebouncedSaver(self.store)
        home = os.path.dirname(self.store.path)
        self.crash = CrashGuard(home)
        self.crashed_last_time = self.crash.previous_crash()
        self.crash.start()
        self.profile_store = ProfileStore(os.path.join(home, "profile.json"))
        self.profile = self.profile_store.load()
        _, legacy_awake = self.store.load_with_legacy()
        if legacy_awake is not None:
            self.profile['screen_awake'] = bool(legacy_awake)
            try:
                self.profile_store.save(self.profile)
            except Exception:
                pass
        self.sound = SoundManager(os.path.join('assets', 'sounds'),
                                  enabled=bool(self.cfg.get('sound_on', True)),
                                  volume=float(self.cfg.get('volume', 0.8)))
        self.haptics = Haptics(enabled=bool(self.cfg.get('vibrate_on', True)),
                               strength=float(self.cfg.get('vibrate_strength', 0.5)))
        self.debug_stats = DebugStats(enabled=False)
        self.confirm_state = ConfirmState()
        self.replay_mode = False
        self._recorded = False
        self.pause_gate = PauseGate()
        self.achievements_overlay = None
        self.onboarding_overlay = None
        if self.theme_override:
            self.cfg["theme"] = self.theme_override
        if self.font_override:
            self.cfg["font_size"] = self.font_override
        self.game = Game(DEFAULT_SEED)
        self.game.clock.set_speed(self.speed)
        self._foods0 = self.game.world.food_count()
        self._rebuilds_after_death = 0
        self._frozen = self.obstacle_shot
        self.chunk_mgr = ChunkManager(self.game.world)
        if self.wrap:
            self.game.set_wrap_mode(True)
        self.session: AISession | None = None
        if self.ai:
            self.session = AISession()
            self.game.tick_listeners.append(self._ai_tick)
        self.canvas_widget = GameCanvas(self.game)
        self.canvas_widget.size_hint = (0.70, 1.0)
        self.canvas_widget.pos_hint = {"x": 0, "y": 0}
        self.canvas_widget.on_direction = self._on_direction

        self.panel = Panel(
            self.game, on_wrap=self._toggle_wrap, on_restart=self._restart,
            on_settings=self._open_settings,
            on_history=self._open_history,
            on_achievements=self._open_achievements,
            on_stats=self._open_stats,
        )
        self.panel.size_hint = (0.30, 1.0)
        self.panel.pos_hint = {"right": 1, "y": 0}

        self.canvas_widget.set_theme(self.cfg.get("theme", "dark"))
        self.canvas_widget.apply_view_options(
            self.cfg.get("show_grid", True), self.cfg.get("head_highlight", True)
        )
        self._apply_theme()
        self.sound.enabled = bool(self.cfg.get("sound_on", True))
        self.sound.volume = float(self.cfg.get("volume", 0.8))
        self.haptics.enabled = bool(self.cfg.get("vibrate_on", True))
        self.haptics.strength = float(self.cfg.get("vibrate_strength", 0.5))

        root = FloatLayout()
        root.add_widget(self.canvas_widget)
        root.add_widget(self.panel)
        self.root_layout = root
        self.debug_overlay = DebugOverlay(pos_hint={'x': 0.30, 'top': 0.98})
        root.add_widget(self.debug_overlay)
        self._apply_theme()
        # 布局完成后再刷一次文案：面板首次创建时宽度为 0，纹理会按 0 宽缓存
        Clock.schedule_once(lambda _dt: self.panel.refresh(), 0.05)

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
            if self.obstacle_shot:
                Clock.schedule_once(self._setup_obstacle_scene, 0.2)
                shot_name = "walls" if self.wall_shot else "obstacles"
                Clock.schedule_once(lambda _dt: self._shot(shot_name), 0.8)
            if self.interp:
                for i in range(3):
                    Clock.schedule_once(
                        lambda _dt, k=i: self._shot(f"interp{k + 1}"),
                        1.0 + i * 2 * FRAME_INTERVAL,
                    )
            if self.spawn_shot:
                Clock.schedule_once(lambda _dt: self._shot("spawn"), 0.8)
            if self.settings_shot:
                Clock.schedule_once(lambda _dt: self._open_settings(), 0.4)
                Clock.schedule_once(lambda _dt: self._shot("settings"), 1.0)
            if self.ach_shot:
                Clock.schedule_once(lambda _dt: self._open_achievements(), 0.4)
                Clock.schedule_once(lambda _dt: self._shot("achievements"), 1.0)
            if self.onboard_shot:
                Clock.schedule_once(lambda _dt: self._open_onboarding(), 0.3)
                Clock.schedule_once(lambda _dt: self._shot("onboarding"), 0.9)
            if self.pause_shot:
                Clock.schedule_once(lambda _dt: self._toggle_pause(), 0.4)
                Clock.schedule_once(lambda _dt: self._shot("pause"), 0.9)
            if self.replay_shot:
                self.canvas_widget.overlay_text = f"{strings.t('replay')} 12/120 1x"
                Clock.schedule_once(lambda _dt: self._shot("replay"), 0.8)
            if self.stats_shot:
                Clock.schedule_once(lambda _dt: self._open_stats(), 0.4)
                Clock.schedule_once(lambda _dt: self._shot("stats"), 1.0)
            if self.debug_shot:
                Clock.schedule_once(lambda _dt: self._toggle_debug(True), 0.3)
                Clock.schedule_once(lambda _dt: self._shot("debug_on"), 1.0)
            if self.replayui_shot:
                Clock.schedule_once(lambda _dt: self._open_replay(), 0.4)
                Clock.schedule_once(lambda _dt: self._shot("replay_ui"), 1.0)
            if self.confirm_shot:
                Clock.schedule_once(lambda _dt: self._ask_confirm("restart"), 0.4)
                Clock.schedule_once(lambda _dt: self._shot("confirm"), 1.0)
            if self.history_shot:
                Clock.schedule_once(self._setup_history_shot, 0.3)
                Clock.schedule_once(lambda _dt: self._shot("history"), 1.0)
            if self.clip_demo:
                Clock.schedule_once(self._setup_clip_scene, 0.2)
                Clock.schedule_once(lambda _dt: self._shot("clip"), 0.8)
            if self.wrap_scene:
                Clock.schedule_once(self._setup_wrap_scene, 0.2)
                Clock.schedule_once(lambda _dt: self._shot("wrap"), 0.9)
            Clock.schedule_once(self._smoke_final, max(0.5, self.smoke_seconds - 0.05))
            Clock.schedule_once(lambda _dt: self.stop(), self.smoke_seconds)
        return root

    # ---------- 设置 ----------
    def _open_settings(self) -> None:
        if getattr(self, "settings_overlay", None) is not None:
            return
        self.settings_overlay = SettingsOverlay(
            self.cfg, on_change=self._on_settings_change, on_close=self._close_settings,
            screen_awake=bool(self.profile.get('screen_awake', True)),
            on_screen_awake=self._on_screen_awake,
        )
        self.settings_overlay.size_hint = (0.30, 1.0)
        self.settings_overlay.pos_hint = {"right": 1, "y": 0}
        self.root_layout.add_widget(self.settings_overlay)
        self.settings_overlay.apply_theme(palette(self.cfg.get("theme", "dark")))
        self.panel.opacity = 0
        self.panel.disabled = True

    def _close_settings(self) -> None:
        overlay = getattr(self, "settings_overlay", None)
        if overlay is not None:
            self.root_layout.remove_widget(overlay)
            self.settings_overlay = None
        self.panel.opacity = 1
        self.panel.disabled = False

    def _on_screen_awake(self, value: bool) -> None:
        self.profile['screen_awake'] = bool(value)
        try:
            self.profile_store.save(self.profile)
        except Exception:
            pass

    def _on_settings_change(self, cfg: dict) -> None:
        self.cfg = dict(cfg)
        self.saver.request(self.cfg)
        if self._save_event is not None:
            self._save_event.cancel()
        self._save_event = Clock.schedule_once(self._flush_save, 0.5)
        self.canvas_widget.set_theme(self.cfg.get("theme", "dark"))
        self.canvas_widget.apply_view_options(
            self.cfg.get("show_grid", True), self.cfg.get("head_highlight", True)
        )

    def _flush_save(self, _dt=None) -> None:
        self._save_event = None
        self.saver.flush()

    def _setup_history_shot(self, _dt: float) -> None:
        """截图用：塞入几条历史样本再打开历史面板。"""
        for mode, score, seed, wrap in (
            ("human", 12, 20261022, False),
            ("ai", 57, 42, False),
            ("ai", 88, 7, True),
        ):
            self.profile = self.profile_store.record_game(self.profile, {
                "mode": mode, "duration": 30, "score": score, "seed": seed,
                "time": 1760000000, "is_ai": mode == "ai", "wrap": wrap,
            })
        self._open_history()

    def on_stop(self) -> None:
        try:
            self.saver.flush_all()   # 退出前强制写盘，避免 debounce 丢最后一次修改
            self.crash.stop()
        except Exception:  # pragma: no cover
            pass

    # ---------- 成就 / 引导 / 暂停 ----------
    def _open_achievements(self) -> None:
        if self.achievements_overlay is not None:
            return
        stats = {"best_score": self.profile.get("best_score", 0),
                 "total_seconds": int(self.profile.get("total_games", 0) * 30)}
        self.achievements_overlay = AchievementPanel(
            self.profile, stats, on_close=self._close_achievements)
        self.achievements_overlay.size_hint = (0.30, 1.0)
        self.achievements_overlay.pos_hint = {"right": 1, "y": 0}
        self.root_layout.add_widget(self.achievements_overlay)
        self.achievements_overlay.apply_theme(palette(self.cfg.get("theme", "dark")))
        self.panel.opacity = 0
        self.panel.disabled = True

    def _close_achievements(self) -> None:
        if self.achievements_overlay is not None:
            self.root_layout.remove_widget(self.achievements_overlay)
            self.achievements_overlay = None
        self.panel.opacity = 1
        self.panel.disabled = False

    def _open_onboarding(self) -> None:
        if self.onboarding_overlay is not None:
            return
        self.onboarding_overlay = OnboardingPanel(on_finish=self._finish_onboarding)
        self.onboarding_overlay.size_hint = (0.34, 0.6)
        self.onboarding_overlay.pos_hint = {"center_x": 0.35, "center_y": 0.5}
        self.root_layout.add_widget(self.onboarding_overlay)
        self.onboarding_overlay.apply_theme(palette(self.cfg.get("theme", "dark")))

    def _finish_onboarding(self) -> None:
        if self.onboarding_overlay is not None:
            self.root_layout.remove_widget(self.onboarding_overlay)
            self.onboarding_overlay = None
        self.profile = mark_done(self.profile)
        try:
            self.profile_store.save(self.profile)
        except Exception:
            pass

    def _toggle_pause(self) -> None:
        if self.replay_mode:
            if getattr(self, "replay_overlay", None) is not None:
                self.replay_overlay.advance(dt)
            self.canvas_widget.rebuild()
            return
        if self.confirm_state.active:
            self.canvas_widget.rebuild()
            return
        if self.pause_gate.active:
            self.pause_gate.finish()
        else:
            self.pause_gate.pause()

    # ---------- 主题 / 统计 / 调试 / 回放 / 确认 ----------
    def _apply_theme(self) -> None:
        colors = palette(self.cfg.get("theme", "dark"))
        self.canvas_widget.set_theme(self.cfg.get("theme", "dark"))
        self.panel.apply_theme(colors)
        for name in ("settings_overlay", "history_overlay", "achievements_overlay",
                     "stats_overlay", "replay_overlay", "confirm_overlay"):
            ov = getattr(self, name, None)
            if ov is not None and hasattr(ov, "apply_theme"):
                ov.apply_theme(colors)
        if getattr(self, "debug_overlay", None) is not None:
            self.debug_overlay.apply_theme(colors)

    def _open_stats(self) -> None:
        if self.session is None or getattr(self, "stats_overlay", None) is not None:
            return
        self.stats_overlay = StatsPanel(self.session, on_close=self._close_stats)
        self.stats_overlay.size_hint = (0.30, 1.0)
        self.stats_overlay.pos_hint = {"right": 1, "y": 0}
        self.root_layout.add_widget(self.stats_overlay)
        self.stats_overlay.apply_theme(palette(self.cfg.get("theme", "dark")))

    def _close_stats(self) -> None:
        if getattr(self, "stats_overlay", None) is not None:
            self.root_layout.remove_widget(self.stats_overlay)
            self.stats_overlay = None

    def _toggle_debug(self, enabled: bool | None = None) -> None:
        target = (not self.debug_stats.enabled) if enabled is None else bool(enabled)
        self.debug_stats.set_enabled(target)
        if not target:
            self.debug_overlay.text = ""

    def _open_replay(self) -> None:
        if getattr(self, "replay_overlay", None) is not None:
            return
        self.replay_mode = True
        self.canvas_widget.on_direction = None  # 回放态：摇杆/滑动 no-op
        self.replay_overlay = ReplayPanel(120, on_close=self._close_replay)
        self.replay_overlay.size_hint = (0.30, None)
        self.replay_overlay.height = 220
        self.replay_overlay.pos_hint = {"right": 1, "top": 0.98}
        self.root_layout.add_widget(self.replay_overlay)
        self.replay_overlay.apply_theme(palette(self.cfg.get("theme", "dark")))

    def _close_replay(self) -> None:
        if getattr(self, "replay_overlay", None) is not None:
            self.root_layout.remove_widget(self.replay_overlay)
            self.replay_overlay = None
        self.replay_mode = False
        self.canvas_widget.on_direction = self._on_direction

    def _ask_confirm(self, action: str) -> None:
        if self.replay_mode:
            return  # 回放态不弹确认
        if getattr(self, "confirm_overlay", None) is not None:
            return
        self.confirm_state.ask(action)
        self.confirm_overlay = ConfirmDialog(action, on_confirm=self._do_confirm,
                                             on_cancel=self._cancel_confirm)
        self.confirm_overlay.size_hint = (0.32, None)
        self.confirm_overlay.height = 170
        self.confirm_overlay.pos_hint = {"center_x": 0.35, "center_y": 0.5}
        self.root_layout.add_widget(self.confirm_overlay)
        self.confirm_overlay.apply_theme(palette(self.cfg.get("theme", "dark")))

    def _do_confirm(self, action: str) -> None:
        self.confirm_state.confirm()
        if getattr(self, "confirm_overlay", None) is not None:
            self.root_layout.remove_widget(self.confirm_overlay)
            self.confirm_overlay = None
        if action == "restart":
            self._restart()

    def _cancel_confirm(self) -> None:
        self.confirm_state.cancel()
        if getattr(self, "confirm_overlay", None) is not None:
            self.root_layout.remove_widget(self.confirm_overlay)
            self.confirm_overlay = None

    # ---------- 历史 / 种子 ----------
    def _open_history(self) -> None:
        if getattr(self, "history_overlay", None) is not None:
            return
        self.history_overlay = HistoryPanel(
            self.profile, self.game.seed,
            on_apply_seed=self._apply_seed,
            on_copy_seed=self._copy_seed,
            on_close=self._close_history,
        )
        self.history_overlay.size_hint = (0.30, 1.0)
        self.history_overlay.pos_hint = {"right": 1, "y": 0}
        self.root_layout.add_widget(self.history_overlay)
        self.history_overlay.apply_theme(palette(self.cfg.get("theme", "dark")))
        self.panel.opacity = 0
        self.panel.disabled = True

    def _close_history(self) -> None:
        overlay = getattr(self, "history_overlay", None)
        if overlay is not None:
            self.root_layout.remove_widget(overlay)
            self.history_overlay = None
        self.panel.opacity = 1
        self.panel.disabled = False

    def _apply_seed(self, seed: int) -> None:
        self.game.reset(seed)
        self.game.clock.set_speed(self.speed)
        self._recorded = False
        self.pause_gate = PauseGate()
        self.achievements_overlay = None
        self.onboarding_overlay = None
        if self.canvas_widget.camera is not None:
            self.canvas_widget.camera.reset(self.game.snake.head)
            self.canvas_widget.viewport = self.canvas_widget.camera.viewport()
        self.canvas_widget.hide_game_over()
        self.canvas_widget.rebuild()
        self._close_history()

    def _copy_seed(self, seed: int) -> None:
        try:
            from kivy.core.clipboard import Clipboard

            Clipboard.copy(str(seed))
        except Exception as exc:  # pragma: no cover
            Logger.warning("clipboard copy failed: %s", exc)

    def _record_game(self) -> None:
        if self._recorded:
            return
        self._recorded = True
        entry = {
            "mode": "ai" if self.session is not None else "human",
            "duration": round(self.game.ticks / max(1, self.game.clock.base_interval), 1),
            "score": self.game.score,
            "seed": self.game.seed,
            "time": int(__import__("time").time()),
            "is_ai": self.session is not None,
            "wrap": self.game.wrap_mode,
        }
        self.profile = self.profile_store.record_game(self.profile, entry)
        stats = {'best_score': self.profile.get('best_score', 0),
                 'ai_food_best': self.game.score if self.session else 0,
                 'wrap_food_best': self.game.score if self.game.wrap_mode else 0,
                 'total_seconds': self.profile.get('total_games', 0) * 30,
                 'games_today': self.profile.get('total_games', 0)}
        self.profile, newly = evaluate(self.profile, stats)
        for _key in newly:
            self.sound.play("achievement")
            self.haptics.vibrate("achievement")
        try:
            self.profile_store.save(self.profile)
        except Exception as exc:  # pragma: no cover
            Logger.warning("profile save failed: %s", exc)

    # ---------- 面板按钮回调 ----------
    def _toggle_wrap(self) -> None:
        self.game.set_wrap_mode(not self.game.wrap_mode)
        self.canvas_widget.rebuild()

    def _on_direction(self, direction) -> None:
        self.game.set_direction(direction)

    def _apply_window_size(self) -> None:
        if desktop.is_android():
            return
        target = self.window_size if self.window_size else (1280, 720)
        density = desktop.get_density() or 1.0
        # Kivy 在 Windows 上会再乘一次 DPI，这里先除回去，保证"物理像素"符合预期
        Window.size = (int(target[0] / density), int(target[1] / density))

    # ---------- 主循环 ----------
    def _frame(self, dt: float) -> None:
        if self._frozen:
            # 截图场景：逻辑冻结，但每帧仍重绘（否则 GL 缓冲可能已被清空）
            self.canvas_widget.advance(dt)
            self._update_chunks()
            self.canvas_widget.rebuild()
            return
        if self.pause_gate.active:
            self.pause_gate.update(dt)
            if self.pause_gate.active:
                self.canvas_widget.overlay_text = str(self.pause_gate.label_seconds())
            else:
                self.canvas_widget.overlay_text = ""
            self.canvas_widget.rebuild()
            return
        summary = self.game.update(dt)
        camera_moved = self.canvas_widget.advance(dt)
        self._update_chunks()
        if summary.ticks or summary.died:
            self.panel.refresh()
        if self.debug_stats.enabled:
            self.debug_overlay.show(self.debug_stats.collect(
                self.game, self.canvas_widget.camera, self.session, self.canvas_widget.viewport))
        else:
            self.debug_overlay.text = ""
        if summary.ate:
            self.sound.play("eat")
            self.haptics.vibrate("eat")
        if summary.died:
            self.sound.play("die")
            self.haptics.vibrate("die")
        if self.session is not None:
            self.canvas_widget.ai_path = self.session.current_path(self.game.ticks)
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
            self._record_game()

    def _ai_tick(self, game) -> None:
        """每个逻辑 tick 开始前调用：AI 方向写入 game（下一 tick 生效）。"""
        if self.session is None:
            return
        d = self.session.tick(game.world, game.snake, game.wrap_mode, speed=self.speed)
        if d is not None:
            game.set_direction(d)

    def _update_chunks(self) -> None:
        vp = self.canvas_widget.viewport
        if vp is not None:
            self.chunk_mgr.update(vp.visible_bounds())

    # ---------- 输入 ----------
    def _on_key_down(self, _window, key, _scancode, _codepoint, _modifiers) -> bool:
        if self.replay_mode or self.confirm_state.active:
            return True  # 回放/确认态屏蔽全部输入
        direction = KEYMAP.get(key)
        if direction is not None:
            return self.game.set_direction(direction)
        if key == KEY_RESTART:
            self._ask_confirm('restart')
            return True
        return False

    def _restart(self) -> None:
        self.game.reset(self.game.seed)
        self.game.clock.set_speed(self.speed)
        self._recorded = False
        self.pause_gate = PauseGate()
        self.achievements_overlay = None
        self.onboarding_overlay = None
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

    # ---------- 演示：路径被视口边缘截断 ----------
    def _setup_clip_scene(self, _dt: float) -> None:
        from ai.controller import AIController
        from core.snake import DIR_RIGHT, Snake
        from core.world import chunk_coord

        world = self.game.world
        for cx in range(0, 4):
            for cy in range(-1, 2):
                world.ensure_chunk(cx, cy)
        world._foods.clear()  # noqa: SLF001
        world._foods_by_chunk.clear()  # noqa: SLF001

        head = (0, 0)
        vp = self.canvas_widget.viewport
        g = vp.grid_size if vp else 34
        half = int(vp.width // g // 2) if vp else 20
        # 放在"搜索半径内、视口外"：路径存在但必须被视口裁掉
        food = (half + 4, 0)
        world._foods.add(food)  # noqa: SLF001
        world._foods_by_chunk.setdefault(chunk_coord(food), set()).add(food)  # noqa: SLF001

        self.game.snake = Snake([head, (-1, 0), (-2, 0)], DIR_RIGHT)
        cam = self.canvas_widget.camera
        if cam is not None:
            cam.reset(head)
            self.canvas_widget.viewport = cam.viewport()

        # 直接构造一条跨越视口右边缘的路径，确定性验证"只画到屏内"
        self.canvas_widget.ai_path = [(i, 0) for i in range(1, 60)]
        self._frozen = True
        self.canvas_widget.rebuild()

    # ---------- 演示：穿墙撞墙不死 ----------
    def _setup_wrap_scene(self, _dt: float) -> None:
        """找一堵"左侧两格可通行"的墙，把蛇放墙左边并开启穿墙 → 撞墙不死。"""
        world = self.game.world
        for cx in range(1, 4):
            for cy in range(0, 4):
                world.ensure_chunk(cx, cy)

        target = None
        for cell in sorted(world.blocked()):
            if world.block_kind(cell) != "wall":
                continue
            left1 = (cell[0] - 1, cell[1])
            left2 = (cell[0] - 2, cell[1])
            if world.is_passable(left1) and world.is_passable(left2):
                target = cell
                break
        if target is None:
            return

        head = (target[0] - 2, target[1])
        self.game.snake = Snake(
            [head, (head[0] - 1, head[1]), (head[0] - 2, head[1])], DIR_RIGHT
        )
        self.game.set_wrap_mode(True)
        cam = self.canvas_widget.camera
        if cam is not None:
            cam.reset(head)
            self.canvas_widget.viewport = cam.viewport()
        self.canvas_widget.rebuild()

    # ---------- 演示：障碍截图（R4 有 ChunkManager 后由它接管） ----------
    def _setup_obstacle_scene(self, _dt: float) -> None:
        """把蛇放到非保护区并预生成周围 chunk，只用于 R2 的障碍截图。"""
        for cx in range(0, 5):
            for cy in range(0, 5):
                self.game.world.ensure_chunk(cx, cy)

        head = (80, 80)
        # 让镜头对准一堵真实的墙，保证四色同屏（障碍/墙/食物/蛇）
        wall = next((c for c in sorted(self.game.world.blocked())
                     if self.game.world.block_kind(c) == "wall"), None)
        if wall is not None:
            hx = wall[0] - 8
            for dx in (8, 7, 6, 5, 9, 10):
                cand = (wall[0] - dx, wall[1])
                if self.game.world.is_passable(cand):
                    hx = cand[0]
                    break
            head = (hx, wall[1])
        else:
            for x in range(70, 95):
                if self.game.world.is_passable((x, 80)):
                    head = (x, 80)
                    break
        self.game.snake = Snake([head, (head[0] - 1, head[1]), (head[0] - 2, head[1])], DIR_RIGHT)
        cam = self.canvas_widget.camera
        if cam is not None:
            cam.reset(head)
            self.canvas_widget.viewport = cam.viewport()
        self.canvas_widget.rebuild()

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
        print("[SMOKE] chunks_loaded =", len(self.game.world.loaded_chunks()))
        try:
            b = self.panel.btn_wrap
            print("[SMOKE] panel_btn     =", f"text={b.text!r} font={b.font_name!r} "
                  f"size={b.size} tex={b.texture_size} font_size={b.font_size}")
        except Exception as exc:  # pragma: no cover
            print("[SMOKE] panel_btn err =", exc)
        if self.session is not None:
            print("[SMOKE] ai_stats      =", self.session.stats)
        print("[SMOKE] dead_rebuilds =", self._rebuilds_after_death)
        if self.canvas_widget._status_text:  # noqa: SLF001
            print("[SMOKE] label         =", repr(self.canvas_widget._status_text.replace("\n", " | ")))  # noqa: SLF001
