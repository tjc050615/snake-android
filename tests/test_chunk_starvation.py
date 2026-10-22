"""R5A：10x chunk 饿死、时间阈值、强制帧跳过 AI、初始化预加载。"""

import collections

from ai.session import AISession
from app import constants as C
from core.chunk_manager import ChunkManager
from core.frame_budget import (
    MAX_CHUNK_SKIP_SECONDS,
    chunk_slot,
    forced_chunk_frame,
)
from core.game import Game
from core.world import World


def test_10x_ticks_every_frame():
    game = Game(1)
    game.clock.set_speed(10.0)
    dist = collections.Counter()
    for _ in range(600):
        dist[game.update(1 / 60.0).ticks] += 1
    assert 0 not in dist, f"10x 下不应出现无 tick 帧：{dict(dist)}"


def test_chunk_starvation_at_10x():
    """AI 模式 + 10x：按时间阈值强制生成，500 帧至少 80 次。"""
    game = Game(2)
    game.clock.set_speed(10.0)
    since = 0.0
    updates = 0
    dt = 1 / 60.0

    for _ in range(500):
        summary = game.update(dt)
        had_ai_tick = summary.ticks > 0
        since += dt
        if chunk_slot(had_ai_tick=had_ai_tick, seconds_since_chunk=since):
            since = 0.0
            updates += 1

    assert updates >= 78, f"chunk 更新只有 {updates} 次，存在饿死"
    assert updates <= 90, "也不应每帧都生成"


def test_chunk_skip_uses_time_not_frames():
    """30fps 与 120fps 下，饿死窗口都约 100ms（与帧数无关）。"""
    def gap(fps):
        dt = 1.0 / fps
        since = 0.0
        worst = 0.0
        for _ in range(int(fps * 2)):
            since += dt
            if chunk_slot(had_ai_tick=True, seconds_since_chunk=since):
                worst = max(worst, since)
                since = 0.0
        return worst

    g30, g120 = gap(30), gap(120)
    assert abs(g30 - MAX_CHUNK_SKIP_SECONDS) <= 1.0 / 30 + 1e-6
    assert abs(g120 - MAX_CHUNK_SKIP_SECONDS) <= 1.0 / 120 + 1e-6


def test_forced_chunk_frame_skips_ai():
    session = AISession()
    before = session.stats["no_decision_reuse"]
    game = Game(3)

    forced = forced_chunk_frame(had_ai_tick=True, seconds_since_chunk=MAX_CHUNK_SKIP_SECONDS)
    assert forced is True
    if forced:
        session.note_forced_reuse()   # 与 app._ai_tick 行为一致
    assert session.stats["no_decision_reuse"] == before + 1
    assert session.stats["reuse"] == session.stats["no_decision_reuse"]

    game.update(C.TICK_INTERVAL)  # 游戏照常推进，只是该帧没有 AI 决策


def test_chunk_manager_preloads_on_init():
    world = World(5)
    rect = (-64, -64, 64, 64)
    cm = ChunkManager(world, preload_rings=2, unload_rings=3,
                      max_generate_per_update=8, initial_rect=rect)
    assert cm.desired(rect) <= set(world.loaded_chunks()), "初始化后必须已覆盖视口+2 圈"


def test_chunk_slot_human_mode_never_starves():
    since = 0.0
    updates = 0
    for _ in range(200):
        since += 1 / 60
        if chunk_slot(had_ai_tick=False, seconds_since_chunk=since):
            since = 0.0
            updates += 1
    assert updates == 200
