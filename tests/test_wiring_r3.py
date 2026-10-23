"""M4/R3 第一步续：接线相关测试（主题、统计、调试、回放闸门、常亮迁移、音效事件）。"""

import ast
import json
import os

from app.theme import THEMES as THEME_PALETTES, palette
from core.audio import Haptics, SoundManager
from core.debug import DebugStats
from core.game import Game
from core.replay import MAX_REPLAY_TICKS, Recorder
from core.replay_controls import blocks_input
from data.ai_stats import FIELDS
from data.profile import ProfileStore, default_profile
from data.storage import ConfigStore, default_config

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")


def _read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8").read()


# ---------- 常亮：profile 而非 config ----------
def test_screen_awake_in_profile_not_config(tmp_path):
    assert "screen_awake" not in default_config()

    cfg_path = str(tmp_path / "config.json")
    prof_path = str(tmp_path / "profile.json")
    store = ConfigStore(cfg_path)
    store.save({**store.load(), "screen_awake": True})  # 非法字段会被丢弃
    assert "screen_awake" not in ConfigStore(cfg_path).load()

    prof = default_profile()
    prof["screen_awake"] = False
    ProfileStore(prof_path).save(prof)
    assert ProfileStore(prof_path).load()["screen_awake"] is False


def test_screen_awake_migration_idempotent(tmp_path):
    cfg_path = str(tmp_path / "config.json")
    with open(cfg_path, "w", encoding="utf-8") as fh:
        json.dump({"version": 1, "theme": "light", "screen_awake": False}, fh)

    store = ConfigStore(cfg_path)
    cfg, legacy = store.load_with_legacy()
    assert legacy is False
    assert cfg["theme"] == "light"
    with open(cfg_path, encoding="utf-8") as fh:
        assert "screen_awake" not in json.load(fh), "迁移后应删除旧字段"

    cfg2, legacy2 = store.load_with_legacy()   # 第二次启动
    assert legacy2 is None, "幂等：不再迁移"
    assert "screen_awake" not in cfg2


# ---------- 回放完整文件大小 ----------
def test_replay_full_file_size_under_100kb_at_cap(tmp_path):
    rec = Recorder(20261022, "ai")
    for i in range(MAX_REPLAY_TICKS):
        if i in (10, 500, 4000):
            rec.events.append((i, "switch", "human"))
        rec.tick((1, 0))
    rec.events.append((MAX_REPLAY_TICKS, "speed", 2.0))

    path = tmp_path / "replay.json"
    path.write_text(json.dumps(rec.to_payload(), ensure_ascii=False), encoding="utf-8")
    size = path.stat().st_size
    assert size < 100 * 1024, f"完整回放文件 {size} 字节超过 100KB"


# ---------- 主题：面板跟随 ----------
def test_panel_follows_theme():
    assert set(THEME_PALETTES) == {"dark", "light", "high_contrast"}
    for name in THEME_PALETTES:
        colors = palette(name)
        for key in ("panel_bg", "text", "button_bg", "button_text", "accent"):
            assert key in colors, f"{name} 缺 {key}"
    assert palette("dark")["panel_bg"] != palette("light")["panel_bg"]
    assert palette("dark")["panel_bg"] != palette("high_contrast")["panel_bg"]

    for rel in ("view/panel.py", "view/settings_panel.py", "view/history_panel.py",
                "view/info_panel.py", "view/stats_panel.py"):
        src = _read(rel)
        assert "ThemedMixin" in src and "apply_theme" in src, f"{rel} 未接入主题"


# ---------- 统计面板挂载 ----------
def test_stats_panel_mounted_in_ai_mode():
    app_src = _read("app/app.py")
    assert "_open_stats" in app_src
    assert "on_stats=self._open_stats" in app_src
    assert "if self.session is None" in app_src
    assert "StatsPanel(self.session" in app_src
    assert len(FIELDS) == 10


# ---------- 调试面板 ----------
def test_debug_panel_renders_when_on():
    dbg = DebugStats(enabled=True)
    game = Game(5)
    data = dbg.collect(game)
    assert data is dbg.last, "collect 应复用同一个 dict"
    for key in ("head", "fps", "camera", "camera_target", "chunk_border", "ai_path_nodes"):
        assert key in data
    assert _read("view/debug_overlay.py").count("strings.t") >= 1


def test_debug_fps_no_collect_when_off():
    dbg = DebugStats(enabled=False)
    for _ in range(5):
        dbg.collect(Game(1))
    assert dbg.collect_calls == 0, "关闭时不应采样"
    assert len(dbg.frame_times) == 0, "关闭时不应记录帧时间"


# ---------- 回放闸门 ----------
def test_replay_blocks_keyboard_joystick_swipe():
    assert blocks_input(replay_mode=True, confirm_active=False) is True
    assert blocks_input(replay_mode=False, confirm_active=True) is True
    assert blocks_input(replay_mode=False, confirm_active=False) is False

    app_src = _read("app/app.py")
    assert "self.canvas_widget.on_direction = None" in app_src, "回放要屏蔽摇杆/滑动"
    assert "if self.replay_mode or self.confirm_state.active" in app_src, "回放要屏蔽键盘"


# ---------- 音效/震动事件 ----------
def test_sound_haptics_triggered_on_events(tmp_path):
    app_src = _read("app/app.py")
    for ms in ("vibrate_ms(50)", "vibrate_ms(300)", "vibrate_ms(20)"):
        assert ms in app_src, f"缺震动：{ms}"
    assert "sound.play" not in app_src, "音效逻辑应已移除（只保留震动）"

    sm = SoundManager(str(tmp_path))
    assert sm.play("eat") is False  # 缺文件静默
    hap = Haptics()
    assert hap.vibrate("eat") is True and hap.calls == ["eat"]
