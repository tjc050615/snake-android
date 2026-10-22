"""UI 文案（中英双份，默认中文）。所有 UI 文本必须走这里（test_no_hardcoded_cn 守门）。"""

from __future__ import annotations

DEFAULT_LANG = "zh"

ZH = {
    "game_over": "游戏结束",
    "score": "得分",
    "restart_hint": "按 R 重新开始",
    "paused": "已暂停",
    "restart_confirm": "确定要重新开始吗？",
    "restart": "重新开始",
    "wrap_on": "穿墙: 开",
    "wrap_off": "穿墙: 关",
    "safety_l2_note": "连通面积校验为启发式加强，非严格保证",
    "settings": "设置",
    "close": "关闭",
    "on": "开",
    "off": "关",
    "sound": "音效",
    "vibrate": "震动",
    "volume": "音量",
    "vibrate_strength": "震动强度",
    "theme": "主题",
    "theme_dark": "暗色",
    "theme_light": "亮色",
    "theme_high_contrast": "高对比（R3 开放）",
    "show_fps": "帧率显示",
    "perf_mode": "性能模式",
    "perf_battery": "省电",
    "perf_balanced": "均衡",
    "perf_performance": "高性能",
    "touch_sensitivity": "触控灵敏度",
    "joystick_deadzone": "摇杆死区",
    "head_highlight": "蛇头高亮",
    "show_grid": "格子网格",
    "font_size": "字体大小",
    "reset_defaults": "恢复默认",
    "reset_done": "已恢复默认设置",
    "fps": "帧率",
    "history": "历史",
    "seed": "种子",
    "apply_seed": "应用",
    "copy_seed": "复制",
    "seed_copied": "已复制种子",
    "seed_invalid": "种子无效（仅 0~2147483647）",
    "no_history": "还没有对局记录",
    "mode_ai": "AI",
    "mode_human": "人类",
}

EN = {
    "game_over": "GAME OVER",
    "score": "Score",
    "restart_hint": "Press R to restart",
    "paused": "Paused",
    "restart_confirm": "Restart this run?",
    "restart": "Restart",
    "wrap_on": "Wrap: ON",
    "wrap_off": "Wrap: OFF",
    "safety_l2_note": "Connectivity check is a heuristic, not a proof",
    "settings": "Settings",
    "close": "Close",
    "on": "On",
    "off": "Off",
    "sound": "Sound",
    "vibrate": "Vibration",
    "volume": "Volume",
    "vibrate_strength": "Vibration strength",
    "theme": "Theme",
    "theme_dark": "Dark",
    "theme_light": "Light",
    "theme_high_contrast": "High contrast (R3)",
    "show_fps": "Show FPS",
    "perf_mode": "Performance mode",
    "perf_battery": "Battery",
    "perf_balanced": "Balanced",
    "perf_performance": "Performance",
    "touch_sensitivity": "Touch sensitivity",
    "joystick_deadzone": "Joystick deadzone",
    "head_highlight": "Head highlight",
    "show_grid": "Grid",
    "font_size": "Font size",
    "reset_defaults": "Reset to defaults",
    "reset_done": "Settings restored",
    "fps": "FPS",
    "history": "History",
    "seed": "Seed",
    "apply_seed": "Apply",
    "copy_seed": "Copy",
    "seed_copied": "Seed copied",
    "seed_invalid": "Invalid seed (0~2147483647)",
    "no_history": "No games yet",
    "mode_ai": "AI",
    "mode_human": "Human",
}

STRINGS: dict[str, dict[str, str]] = {"zh": ZH, "en": EN}

REQUIRED_KEYS = (
    "game_over", "score", "restart_hint", "paused", "restart_confirm", "restart",
    "wrap_on", "wrap_off", "settings", "close", "sound", "vibrate", "volume",
    "theme", "show_fps", "perf_mode", "font_size", "reset_defaults",
    "history", "seed", "apply_seed", "copy_seed",
)


def t(key: str, lang: str | None = None) -> str:
    """取文案；语言缺省用 DEFAULT_LANG，key 缺失直接抛错（早暴露）。"""
    table = STRINGS.get(lang or DEFAULT_LANG, STRINGS[DEFAULT_LANG])
    if key not in table:
        raise KeyError(f"missing string key: {key}")
    return table[key]
