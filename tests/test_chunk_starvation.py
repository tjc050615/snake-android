"""R5A 收尾：10x 下 chunk 饿死回归测试。"""

import collections

from app import constants as C
from core.frame_budget import MAX_CHUNK_SKIP_FRAMES, chunk_slot
from core.game import Game


def test_10x_ticks_every_frame():
    """前提确认：10x、60fps 下每帧都有 tick（所以不能只看 had_ai_tick）。"""
    game = Game(1)
    game.clock.set_speed(10.0)
    dist = collections.Counter()
    for _ in range(600):
        dist[game.update(1 / 60.0).ticks] += 1
    assert 0 not in dist, f"10x 下不应出现无 tick 帧：{dict(dist)}"
    assert dist[1] + dist[2] == 600


def test_chunk_starvation_at_10x():
    """AI 模式 + 10x：500 帧内至少要生成 80 次 chunk（不能被 AI tick 饿死）。"""
    game = Game(2)
    game.clock.set_speed(10.0)
    frames = 500
    since = 0
    updates = 0

    for _ in range(frames):
        summary = game.update(1 / 60.0)
        had_ai_tick = summary.ticks > 0          # AI 模式：每帧都有决策
        since += 1
        if chunk_slot(had_ai_tick=had_ai_tick, frames_since_chunk=since):
            since = 0
            updates += 1

    assert updates >= 80, f"chunk 更新只有 {updates} 次，存在饿死"
    assert updates <= frames / MAX_CHUNK_SKIP_FRAMES + 10, "也不应每帧都生成"


def test_chunk_slot_human_mode_never_starves():
    since = 0
    updates = 0
    for _ in range(200):
        since += 1
        if chunk_slot(had_ai_tick=False, frames_since_chunk=since):
            since = 0
            updates += 1
    assert updates == 200, "人类模式没有 AI tick，应每帧都生成"
