"""帧预算与错峰（R5A，纯函数）。"""

from __future__ import annotations

TICK_BUDGET_MS = 16.67


def typical_ms(logic: float, ai: float, chunk: float, inp: float, render: float) -> float:
    return logic + ai + chunk + inp + render


def staggered_worst_ms(logic: float, ai: float, chunk: float, inp: float, render: float) -> float:
    """错峰后最坏帧：AI 与 chunk 不同帧发生，取二者较大值。

    注意：`logic + inp + render` 每帧都存在，只有 ai/chunk 互斥。
    """
    return logic + max(ai, chunk) + inp + render


def chunk_slot(had_ai_tick: bool) -> bool:
    """AI 决策帧不生成 chunk（错峰）；其余帧正常生成。"""
    return not had_ai_tick
