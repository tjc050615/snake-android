"""M4/R3 收尾：'?' 占位语义 + 含模式切换的完整文件大小。"""

import json

from app import constants as C
from core.game import Game
from core.replay import MAX_REPLAY_TICKS, MODE_AI, Player, Recorder


def test_recorder_pads_with_placeholder_on_switch():
    rec = Recorder(11, "human")
    game = Game(11)
    for _ in range(5):
        game.set_direction((1, 0))
        game.update(C.TICK_INTERVAL)
        rec.tick((1, 0), "human")
    for _ in range(3):
        game.set_direction((0, 1))
        game.update(C.TICK_INTERVAL)
        rec.tick((0, 1), "ai")

    payload = rec.to_payload()
    assert payload["decisions"][:5] == "?????", "切换前的 tick 用占位符对齐"
    assert set(payload["decisions"][5:]) <= set("ABCD")


def test_placeholder_direction_is_none_keeps_last():
    """'?' 在没有有效决策时返回 None：调用方沿用上一方向（与录制时 reuse 语义一致）。"""
    payload = {
        "version": 1, "seed": 1, "mode": MODE_AI, "ticks": 4,
        "capped": False, "stopped": False, "events": [],
        "decisions": "??AB",
    }
    player = Player(payload)
    assert player.direction_at(0) is None
    assert player.direction_at(1) is None
    assert player.direction_at(2) == (0, 1)   # A
    assert player.direction_at(3) == (1, 0)   # B


def test_replay_full_file_size_under_100kb_at_cap_with_switch(tmp_path):
    rec = Recorder(20261022, "human")
    for i in range(MAX_REPLAY_TICKS):
        if i in (100, 5000, 60000):
            rec.tick((1, 0), "ai" if i != 60000 else "human")
        rec.tick((1, 0))

    path = tmp_path / "replay_switch.json"
    path.write_text(json.dumps(rec.to_payload(), ensure_ascii=False), encoding="utf-8")
    assert path.stat().st_size < 100 * 1024
    assert any(k == "switch" for _t, k, _v in rec.to_payload()["events"])
