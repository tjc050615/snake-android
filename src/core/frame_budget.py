"""帧预算与错峰（R5A，纯函数）。

10x 速度实测：每帧 tick 分布 {1: 201, 2: 399}（600 帧、60fps）——**每帧都有 tick**，
所以「有 tick 就不生成 chunk」会让 AI 模式下 chunk 永久饿死。
因此引入 `max_skip`：最多连续跳过 N 帧，之后强制生成一次。
"""

from __future__ import annotations

TICK_BUDGET_MS = 16.67
MAX_CHUNK_SKIP_SECONDS = 0.1  # 基于时间：与帧率无关（30fps/120fps 都是 ~100ms）


def typical_ms(logic: float, ai: float, chunk: float, inp: float, render: float) -> float:
    return logic + ai + chunk + inp + render


def staggered_worst_ms(logic: float, ai: float, chunk: float, inp: float, render: float) -> float:
    """错峰后最坏帧：AI 与 chunk 不同帧发生，取二者较大值。"""
    return logic + max(ai, chunk) + inp + render


def chunk_slot(had_ai_tick: bool, seconds_since_chunk: float = 0.0,
               max_skip_s: float = MAX_CHUNK_SKIP_SECONDS) -> bool:
    """本帧是否生成 chunk（基于时间，不依赖帧率）。

    - 没有 AI tick 的帧：正常生成
    - 有 AI tick 的帧：跳过；但距上次生成 ≥ max_skip_s 时强制生成一次
    """
    if not had_ai_tick:
        return True
    return seconds_since_chunk >= max_skip_s


def forced_chunk_frame(had_ai_tick: bool, seconds_since_chunk: float,
                       max_skip_s: float = MAX_CHUNK_SKIP_SECONDS) -> bool:
    """强制 chunk 帧：该帧跳过 AI 决策，保证 AI 与 chunk 不同帧。"""
    return had_ai_tick and seconds_since_chunk >= max_skip_s
