"""M4/R3：回放 UI 层一致性（人类 / AI / 模式切换）+ 结束文案同帧。"""

from app import constants as C
from core.game import Game
from core.replay import MODE_AI, MODE_HUMAN, Recorder
from core.replay_player import ReplayDriver


def _record(script, seed=7, mode=MODE_HUMAN, switch_at=None):
    game = Game(seed)
    rec = Recorder(seed, mode)
    heads = []
    for i, d in enumerate(script):
        m = mode
        if switch_at is not None and i >= switch_at:
            m = MODE_AI if mode == MODE_HUMAN else MODE_HUMAN
        game.set_direction(d)
        game.update(C.TICK_INTERVAL)
        rec.tick(game.snake.direction, m)
        heads.append(tuple(game.snake.head))
        if game.state != "running":
            break
    payload = rec.to_payload()
    payload["heads"] = [list(h) for h in heads]
    return payload, heads


def _script(n=120):
    return [((1, 0) if (i // 8) % 2 == 0 else (0, 1)) for i in range(n)]


def _replay_heads(payload, ticks):
    game = Game(payload["seed"])
    driver = ReplayDriver(game, payload)
    out = []
    while driver.progress()[0] < min(ticks, payload["ticks"]):
        d = driver.player.direction_at(driver.progress()[0])
        if d is not None:
            game.set_direction(d)
        driver.step(1)
        out.append(tuple(game.snake.head))
    return out


def test_replay_ui_ai_mode():
    payload, heads = _record(_script(), mode=MODE_AI)
    assert len(payload["decisions"]) == len(heads)
    replayed = _replay_heads(payload, 100)
    assert replayed == heads[:100], "AI 录制回放 100 tick 蛇头应一致"


def test_replay_ui_mode_switch():
    payload, heads = _record(_script(), switch_at=50)
    assert any(k == "switch" for _t, k, _v in payload["events"])
    replayed = _replay_heads(payload, 100)
    assert replayed == heads[:100], "中途切换后蛇头仍应逐 tick 一致"


def test_replay_end_text_same_frame():
    payload, _heads = _record(_script(20))
    game = Game(payload["seed"])
    driver = ReplayDriver(game, payload)

    driver.step(payload["ticks"])
    assert driver.finished is True
    assert driver.overlay_text() == driver.end_text(), "结束那一帧文案就应切换"
    assert "回放结束" in driver.overlay_text()
