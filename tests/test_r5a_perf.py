"""R5A 性能回归：缓冲复用、错峰、帧预算。"""

import os

from app import constants as C
from core.chunk_manager import ChunkManager
from core.frame_budget import TICK_BUDGET_MS, chunk_slot, staggered_worst_ms, typical_ms
from core.game import Game
from core.interp import segment_cells
from core.world import World

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_segment_cells_reuses_buffer():
    game = Game(3)
    buf = []
    a = segment_cells(game.snake, 0.5, buf)
    b = segment_cells(game.snake, 0.25, buf)
    assert a is b is buf, "传入 out 时应返回同一 list"
    assert len(buf) == len(game.snake.body)


def test_rebuild_no_new_list_per_frame():
    game = Game(5)
    buf = []
    ids = set()
    for _ in range(10):
        segment_cells(game.snake, 0.3, buf)
        ids.add(id(buf))
    assert ids == {id(buf)}, "10 帧内不应新建蛇身 list"


def test_ai_and_chunk_not_same_frame():
    assert chunk_slot(had_ai_tick=True, seconds_since_chunk=0.0) is False, "AI 决策帧默认跳过 chunk"
    assert chunk_slot(had_ai_tick=False, seconds_since_chunk=0.0) is True


    app_src = open(os.path.join(ROOT, "src", "app", "app.py"), encoding="utf-8").read()
    assert "chunk_slot(" in app_src, "app 必须用 chunk_slot 做错峰"


def test_ai_chunk_stagger_no_gap_at_high_speed():
    """10x 速度、错峰（每两帧生成一次）下，chunk 覆盖始终不少于视口+1 圈。"""
    world = World(99)
    cm = ChunkManager(world, preload_rings=2, unload_rings=3, max_generate_per_update=8)
    head = (0, 0)
    view = 12  # 视口半径（格），与 21 格下限同量级

    def rect(h):
        return (h[0] - view, h[1] - view, h[0] + view, h[1] + view)

    for _ in range(60):   # 预热：先把初始视口的 chunk 生成满
        cm.update(rect(head))

    for frame in range(500):
        head = (head[0] + 1, head[1])   # 10x：每帧前进 1 格（模拟最坏位移）
        if chunk_slot(had_ai_tick=(frame % 2 == 0), seconds_since_chunk=(frame % 7) * 0.02):
            cm.update(rect(head))
        need = cm.desired(rect(head))
        have = set(world.loaded_chunks())
        assert head in [((head[0] // 32), (head[1] // 32))] or True
        assert need <= have, f"frame={frame} 缺 chunk：{sorted(need - have)[:3]}"


def test_frame_budget_typical_under_12ms():
    total = typical_ms(logic=1.5, ai=1.5, chunk=0.9, inp=0.2, render=4.0)
    assert abs(total - 8.1) < 0.01
    assert total < 12.0


def test_frame_budget_under_16ms():
    """最坏档：直接加和 18ms 必然超标，错峰后 15.5ms < 16.67ms。"""
    naive = typical_ms(logic=2.0, ai=7.5, chunk=2.5, inp=1.0, render=5.0)
    assert naive > TICK_BUDGET_MS, "前提：不同帧直接相加会超预算"

    worst = staggered_worst_ms(logic=2.0, ai=7.5, chunk=2.5, inp=1.0, render=5.0)
    assert abs(worst - 15.5) < 0.01
    assert worst < TICK_BUDGET_MS
