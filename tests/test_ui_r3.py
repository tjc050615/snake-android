"""M4/R3 第一步：回放控件、确认弹窗、常亮持久化、统计/调试面板、音效、主题、无 Switch。"""

import ast
import os

import pytest

from ai.session import AISession
from app.theme import THEMES as THEME_PALETTES, palette
from core.audio import Haptics, SoundManager
from core.confirm import ConfirmState
from core.debug import DebugStats
from core.game import Game
from core.pause import PauseGate
from core.replay_controls import SPEEDS, ReplayControls
from data.storage import ConfigStore, default_config
from data.ai_stats import FIELDS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------- 回放控件 ----------
def test_replay_controls_pause_speed():
    rc = ReplayControls(total_ticks=100)
    assert rc.paused is True
    assert rc.advance(0.1) == 0, "暂停时不推进"

    rc.toggle_pause()
    assert rc.paused is False
    assert rc.advance(0.1) == 1  # 1x：0.1s = 1 tick

    rc.next_speed()
    assert rc.speed == 2.0
    assert rc.advance(0.1) == 2

    for _ in range(2):
        rc.next_speed()
    assert rc.speed == SPEEDS[0] == 0.5

    # 不支持后退
    rc.seek(50)
    assert rc.tick == 50
    rc.seek(10)
    assert rc.tick == 50, "向后拖拽应被忽略"


# ---------- 确认弹窗 ----------
def test_confirm_dialog_blocks_gameplay():
    confirm = ConfirmState()
    assert confirm.blocks_gameplay() is False
    confirm.ask("restart")
    assert confirm.blocks_gameplay() is True
    assert confirm.confirm() == "restart"
    assert confirm.blocks_gameplay() is False

    confirm.ask("quit")
    confirm.cancel()
    assert confirm.confirm() is None


# ---------- 常亮持久化 ----------
def test_screen_awake_setting_persisted(tmp_path):
    path = str(tmp_path / "config.json")
    store = ConfigStore(path)
    cfg = store.load()
    assert cfg["screen_awake"] is True
    cfg["screen_awake"] = False
    store.save(cfg)
    assert ConfigStore(path).load()["screen_awake"] is False


# ---------- 统计面板字段 ----------
def test_stats_panel_fields():
    session = AISession()
    game = Game(3)
    session.tick(game.world, game.snake)
    for key in FIELDS:
        assert key in session.stats, f"AISession.stats 缺 {key}"
    assert "no_decision_reuse" in session.stats


# ---------- 调试面板零开销 ----------
def test_debug_panel_off_cost():
    dbg = DebugStats(enabled=False)
    game = Game(1)
    assert dbg.collect(game) == {}
    assert dbg.last == {}

    dbg.set_enabled(True)
    data = dbg.collect(game)
    assert data and "head" in data


# ---------- 音效缺文件 ----------
def test_sound_missing_file_no_crash(tmp_path):
    sm = SoundManager(str(tmp_path), enabled=True, volume=0.5)
    assert sm.play("eat") is False
    assert sm.play("unknown") is False

    sm.enabled = False
    assert sm.play("eat") is False

    hap = Haptics(enabled=True, strength=0.5)
    assert hap.vibrate("eat") is True
    hap.enabled = False
    assert hap.vibrate("eat") is False


# ---------- 主题扩展 ----------
def test_theme_panel_follows():
    assert set(THEME_PALETTES) == {"dark", "light", "high_contrast"}
    dark, light, hc = palette("dark"), palette("light"), palette("high_contrast")
    assert dark["panel_bg"] != light["panel_bg"]
    assert hc["text"] != dark["text"]
    assert hc["body"] != dark["body"]


# ---------- 无 Switch ----------
def test_no_switch_widget():
    bad = []
    for dirpath, _dirs, files in os.walk(os.path.join(ROOT, "src")):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            src = open(path, encoding="utf-8").read()
            if "Switch(" in src or "uix.switch" in src:
                bad.append(name)
    assert not bad, f"仍在使用 Kivy Switch：{bad}（KI-023 要求换 CheckBox）"


# ---------- 暂停语义（澄清 2） ----------
def test_resume_countdown_starts_on_resume_not_on_pause():
    gate = PauseGate(3.0)
    gate.pause()
    for _ in range(10):
        gate.update(1.0)
    assert gate.active is True, "暂停可以无限久，不应自动恢复"
    assert gate.label_seconds() == 0
    assert gate.accept_input() is False

    gate.request_resume()
    assert gate.counting_down is True
    assert gate.label_seconds() == 3
    gate.update(1.0)
    assert gate.accept_input() is False
    gate.update(2.1)
    assert gate.active is False
    assert gate.accept_input() is True
