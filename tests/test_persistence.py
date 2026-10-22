"""M4/R2 第一步：profile / 历史 / 种子 / 备份 / 崩溃日志 / debounce。"""

import json
import os

import pytest

from core.seed import format_seed, parse_seed
from core.world import World
from data.backup import BUNDLE_VERSION, export_bundle, import_bundle
from data.crash import CrashGuard
from data.debounce import DebouncedSaver
from data.profile import HISTORY_SIZE, ProfileStore, default_profile, validate_profile
from data.storage import ConfigStore, default_config


# ---------- profile ----------
def test_profile_corrupt_falls_back(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text("{broken", encoding="utf-8")
    assert ProfileStore(str(path)).load() == default_profile()


def test_profile_unknown_fields_ignored(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"version": 1, "best_score": 7, "nope": 1}), encoding="utf-8")
    prof = ProfileStore(str(path)).load()
    assert prof["best_score"] == 7
    assert "nope" not in prof


def test_best_score_not_lowered(tmp_path):
    store = ProfileStore(str(tmp_path / "profile.json"))
    prof = store.record_game(store.load(), {"mode": "human", "duration": 10, "score": 50,
                                            "seed": 1, "time": 1, "is_ai": False, "wrap": False})
    prof = store.record_game(prof, {"mode": "human", "duration": 10, "score": 20,
                                    "seed": 1, "time": 2, "is_ai": False, "wrap": False})
    assert prof["best_score"] == 50
    assert prof["total_games"] == 2


def test_history_evict_oldest(tmp_path):
    store = ProfileStore(str(tmp_path / "profile.json"))
    prof = store.load()
    for i in range(HISTORY_SIZE + 5):
        prof = store.record_game(prof, {
            "mode": "human", "duration": i, "score": i, "seed": i, "time": i,
            "is_ai": False, "wrap": False,
        })
    hist = prof["history"]
    assert len(hist) == HISTORY_SIZE
    assert hist[0]["score"] == 5, "最旧的 5 条应被淘汰"
    assert hist[-1]["score"] == HISTORY_SIZE + 4


def test_history_bad_entries_dropped():
    prof = validate_profile({"version": 1, "history": [{"mode": "human"}, "junk",
                                                      {"mode": "ai", "duration": 1, "score": 2,
                                                       "seed": 3, "time": 4, "is_ai": True, "wrap": False}]})
    assert len(prof["history"]) == 1


# ---------- 种子 ----------
def test_seed_reproduce():
    w1 = World(123456)
    w2 = World(123456)
    w1.ensure_chunk(3, 4)
    w2.ensure_chunk(3, 4)
    assert w1.blocked() == w2.blocked()
    assert w1.foods() == w2.foods()


@pytest.mark.parametrize("text", ["", "abc", "-1", "1.5", "  ", "99999999999999999999", "0x10"])
def test_seed_invalid_input_rejected(text):
    assert parse_seed(text) is None


def test_seed_valid_and_format():
    assert parse_seed("42") == 42
    assert parse_seed(" 42 ") == 42
    assert format_seed(42) == "42"


# ---------- 备份 ----------
def test_backup_import_export_roundtrip(tmp_path):
    cfg = default_config()
    cfg["theme"] = "light"
    prof = ProfileStore(str(tmp_path / "profile.json"))
    profile = prof.record_game(prof.load(), {"mode": "ai", "duration": 30, "score": 12,
                                             "seed": 9, "time": 100, "is_ai": True, "wrap": True})

    path = str(tmp_path / "backup.json")
    export_bundle(path, cfg, profile)
    cfg2, profile2 = import_bundle(path)

    assert cfg2["theme"] == "light"
    assert profile2["history"] == profile["history"]
    assert profile2["best_score"] == 12


def test_backup_rejects_bad_file(tmp_path):
    path = str(tmp_path / "bad.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"bundle_version": 999}, fh)
    with pytest.raises(ValueError):
        import_bundle(path)

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("{oops")
    with pytest.raises(ValueError):
        import_bundle(path)


def test_bundle_version_constant():
    assert BUNDLE_VERSION == 1


# ---------- 崩溃日志 ----------
def test_crash_guard_detects_previous_crash(tmp_path):
    guard = CrashGuard(str(tmp_path))
    assert guard.previous_crash() is False
    guard.start()
    assert (tmp_path / ".running").exists()

    guard2 = CrashGuard(str(tmp_path))  # 模拟重启
    assert guard2.previous_crash() is True
    assert (tmp_path / "crash.log").exists()


def test_crash_guard_clean_exit_has_no_log(tmp_path):
    guard = CrashGuard(str(tmp_path))
    guard.start()
    guard.stop()
    assert CrashGuard(str(tmp_path)).previous_crash() is False


# ---------- debounce ----------
class CountingStore:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def save(self, cfg):
        self.calls += 1
        if self.fail:
            raise OSError("disk full")
        return cfg


def test_slider_does_not_write_on_every_move():
    store = CountingStore()
    saver = DebouncedSaver(store, delay=0.5)
    for v in range(20):  # 模拟拖动 20 次
        saver.request({"volume": v / 20})
    assert store.calls == 0, "拖动过程中不应写盘"
    assert saver.flush() is True
    assert store.calls == 1, "停手后只写一次"


def test_save_failure_degrades_gracefully():
    saver = DebouncedSaver(CountingStore(fail=True))
    saver.request({"volume": 0.5})
    assert saver.flush() is False, "失败要返回 False 而不是抛异常"
    assert saver.failures == 1
