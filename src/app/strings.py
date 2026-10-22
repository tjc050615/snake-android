"""UI 文案（中英双份，默认中文）。

M1~M2 的 GAME OVER 是写死英文；R3 起统一走这里，方便 M4 做多语言与设置项。
"""

from __future__ import annotations

DEFAULT_LANG = "zh"

STRINGS: dict[str, dict[str, str]] = {
    "zh": {
        "game_over": "游戏结束",
        "score": "得分",
        "restart_hint": "按 R 重新开始",
        "paused": "已暂停",
        "restart_confirm": "确定要重新开始吗？",
        "wrap_on": "穿墙: 开",
        "wrap_off": "穿墙: 关",
    },
    "en": {
        "game_over": "GAME OVER",
        "score": "Score",
        "restart_hint": "Press R to restart",
        "paused": "Paused",
        "restart_confirm": "Restart this run?",
        "wrap_on": "Wrap: ON",
        "wrap_off": "Wrap: OFF",
    },
}

REQUIRED_KEYS = ("game_over", "score", "restart_hint", "paused", "restart_confirm")


def t(key: str, lang: str | None = None) -> str:
    """取文案；语言缺省用 DEFAULT_LANG，key 缺失直接抛错（早暴露）。"""
    table = STRINGS.get(lang or DEFAULT_LANG, STRINGS[DEFAULT_LANG])
    if key not in table:
        raise KeyError(f"missing string key: {key}")
    return table[key]
