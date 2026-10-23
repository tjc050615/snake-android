"""M4/R2 第二步：回放确定性、容量上限、成就、引导、暂停倒计时、退出写盘。"""

import pytest

from app import constants as C
from core.game import Game
from core.pause import PauseGate
from core.replay import (
    MAX_REPLAY_BYTES,
    MAX_REPLAY_TICKS,
    MODE_AI,
    MODE_HUMAN,
    Player,
    Recorder,
)
from data.achievements import ACHIEVEMENTS, evaluate, progress
from data.debounce import DebouncedSaver
from data.onboarding import mark_done, should_show


# ---------- 退出写盘 ----------
class _Store:
    def __init__(self):
        self.calls = 0

    def save(self, cfg):
        self.calls += 1
        return cfg


def test_pending_save_flushed_on_app_stop():
    store = _Store()
    saver = DebouncedSaver(store)
    saver.request({"volume": 0.3})
    assert store.calls == 0
    assert saver.flush_all() is True
    assert store.calls == 1


# ---------- 回放确定性 ----------
def _play(script, seed=42, mode=MODE_HUMAN, mode_script=None):
    game = Game(seed, deterministic_food=True)
    rec = Recorder(seed, mode)
    snaps = []
    for i, d in enumerate(script):
        m = mode_script[i] if mode_script else mode
        game.set_direction(d)
        game.update(C.TICK_INTERVAL)
        rec.tick(game.snake.direction, m)
        snaps.append(tuple(game.snake.body))
        if game.state != "running":
            break
    return game, rec, snaps


def _replay(payload, ticks):
    game = Game(payload["seed"], deterministic_food=True)
    player = Player(payload)
    snaps = []
    for tick in range(ticks):
        d = player.direction_at(tick)
        if d is not None:
            game.set_direction(d)
        game.update(C.TICK_INTERVAL)
        snaps.append(tuple(game.snake.body))
        if game.state != "running":
            break
    return snaps


def test_replay_deterministic_human():
    script = [(1, 0)] * 12 + [(0, 1)] * 6 + [(1, 0)] * 12
    _, rec, snaps = _play(script)
    assert len(snaps) > 10
    assert _replay(rec.to_payload(), len(snaps)) == snaps


def test_replay_deterministic_ai():
    script = [(1, 0)] * 15 + [(0, 1)] * 8
    _, rec, snaps = _play(script, mode=MODE_AI)
    payload = rec.to_payload()
    assert len(payload["decisions"]) == len(snaps)
    assert _replay(payload, len(snaps)) == snaps


def test_replay_mode_switch_midgame():
    script = [(1, 0)] * 20
    modes = [MODE_HUMAN] * 8 + [MODE_AI] * 12
    _, rec, snaps = _play(script, mode_script=modes)
    payload = rec.to_payload()
    player = Player(payload)
    assert player.mode_at(0) == MODE_HUMAN
    assert player.mode_at(19) == MODE_AI
    assert _replay(payload, len(snaps)) == snaps


def test_replay_file_size_under_100kb():
    rec = Recorder(1, MODE_AI)
    for _ in range(MAX_REPLAY_TICKS):
        rec.tick((1, 0))
    assert rec.stopped is False
    assert rec.payload_size() < MAX_REPLAY_BYTES, rec.payload_size()


def test_ai_replay_stops_at_tick_cap():
    rec = Recorder(1, MODE_AI)
    for _ in range(MAX_REPLAY_TICKS + 5):
        rec.tick((1, 0))
    assert rec.capped is True
    assert rec.stopped is True
    assert len(rec.decisions) == MAX_REPLAY_TICKS


def test_ai_replay_cap_does_not_block_gameplay():
    game = Game(7)
    rec = Recorder(7, MODE_AI)
    for i in range(MAX_REPLAY_TICKS + 3):
        game.set_direction((1, 0))
        game.update(C.TICK_INTERVAL)
        rec.tick((1, 0))
    before = game.ticks
    game.set_direction((1, 0))
    game.update(C.TICK_INTERVAL)
    assert game.ticks == before + 1, "录制封顶后游戏仍要能继续跑"


# ---------- 成就 ----------
def test_achievements_unlock():
    profile = {"achievements": {}}
    stats = {"best_score": 120, "ai_food_best": 3, "wrap_food_best": 0,
             "total_seconds": 100, "games_today": 2}
    prof, newly = evaluate(profile, stats)
    assert "score_100" in newly
    assert prof["achievements"]["score_100"] is True

    prof2, newly2 = evaluate(prof, stats)
    assert newly2 == [], "已解锁不重复触发"


def test_achievement_progress_values():
    prog = progress({}, {"best_score": 40, "total_seconds": 1800})
    assert prog["score_100"] == (40, 100)
    assert prog["play_1h"] == (1800, 3600)
    assert len(ACHIEVEMENTS) == 5


# ---------- 新手引导 ----------
def test_onboarding_shows_once_ever():
    prof = {}
    assert should_show(prof) is True
    prof = mark_done(prof)
    assert should_show(prof) is False
    assert should_show(mark_done(prof)) is False


# ---------- 暂停倒计时 ----------
def test_pause_countdown_blocks_input():
    """R3 语义：暂停不限时；点继续才开始 3-2-1，期间仍屏蔽输入。"""
    gate = PauseGate(3.0)
    gate.pause()
    gate.update(5.0)
    assert gate.accept_input() is False, "暂停期间不接受输入"

    gate.request_resume()
    assert gate.label_seconds() == 3
    gate.update(1.0)
    assert gate.accept_input() is False
    assert gate.label_seconds() == 2

    gate.update(2.1)
    assert gate.accept_input() is True, "倒计时结束才恢复输入"
