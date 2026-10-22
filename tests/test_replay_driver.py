"""M4/R3 第二步：回放真实驱动。"""

import json

from app import constants as C
from core.game import Game
from core.replay import Recorder
from core.replay_player import ReplayDriver


def _record(script, seed=42, ticks=None):
    game = Game(seed)
    rec = Recorder(seed, "human")
    heads = []
    for i, d in enumerate(script):
        game.set_direction(d)
        game.update(C.TICK_INTERVAL)
        rec.tick(game.snake.direction)
        heads.append(tuple(game.snake.head))
        if game.state != "running":
            break
    payload = rec.to_payload()
    payload["heads"] = [list(h) for h in heads]
    return payload, heads


def _script(n=140):
    s = []
    for i in range(n):
        s.append((1, 0) if (i // 10) % 2 == 0 else (0, 1))
    return s


def test_replay_ui_advances_snake():
    payload, heads = _record(_script())
    game = Game(payload["seed"])
    driver = ReplayDriver(game, payload)

    played = 0
    while played < 100:
        played += driver.step(10)
    assert played == 100
    assert tuple(game.snake.head) == heads[99], "第 100 tick 蛇头应与录制一致"
    assert driver.progress() == (100, payload["ticks"])


def test_replay_pause_freezes_snake():
    payload, _heads = _record(_script())
    game = Game(payload["seed"])
    driver = ReplayDriver(game, payload)
    driver.step(5)
    before = tuple(game.snake.head)

    driver.toggle_pause()
    assert driver.advance(1.0) == 0
    assert tuple(game.snake.head) == before, "暂停时蛇不动"

    driver.toggle_pause()
    assert driver.advance(0.1) >= 1
    assert tuple(game.snake.head) != before


def test_replay_speed_affects_tick_rate():
    payload, _heads = _record(_script())

    g1 = Game(payload["seed"])
    d1 = ReplayDriver(g1, payload, speed_index=1)   # 1x
    n1 = d1.advance(0.5)

    g4 = Game(payload["seed"])
    d4 = ReplayDriver(g4, payload, speed_index=3)   # 4x
    n4 = d4.advance(0.5)

    assert n4 == n1 * 4, f"4x 应推进 4 倍：{n4} vs {n1}"


def test_replay_end_stops():
    payload, heads = _record(_script(30))
    game = Game(payload["seed"])
    driver = ReplayDriver(game, payload)
    total = payload["ticks"]

    played = driver.step(total + 10)
    assert played == total
    assert driver.finished is True
    assert driver.advance(1.0) == 0, "结束后不再推进"

    tail = tuple(game.snake.head)
    driver.step(5)
    assert tuple(game.snake.head) == tail
    assert driver.controls.tick == total


def test_replay_payload_json_roundtrip():
    payload, _heads = _record(_script(20))
    again = json.loads(json.dumps(payload))
    assert again["ticks"] == payload["ticks"]
