"""持久化（M4/R1 只做 config；profile/历史/回放在 R2）。

- 私有目录 JSON，schema 带 `version`
- 读坏文件 / 版本不符 / 字段非法 → 一律降级默认，不抛异常
- 写盘用临时文件 + replace，避免半截文件
"""

from __future__ import annotations

import json
import os

CONFIG_VERSION = 1

DEFAULTS: dict = {
    "version": CONFIG_VERSION,
    "sound_on": True,
    "vibrate_on": True,
    "volume": 0.8,
    "vibrate_strength": 0.5,
    "theme": "dark",
    "show_fps": False,
    "perf_mode": "balanced",
    "touch_sensitivity": 1.0,
    "joystick_deadzone": 0.15,
    "head_highlight": True,
    "show_grid": True,
    "font_size": 16.0,
}

THEMES = ("dark", "light", "high_contrast")
PERF_MODES = ("battery", "balanced", "performance")


def default_config() -> dict:
    return dict(DEFAULTS)


def _clamp(value, lo, hi, fallback):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return fallback
    return min(max(v, lo), hi)


def validate(raw: dict) -> dict:
    """把任意字典归一化成合法配置；非法字段回落默认值。"""
    cfg = default_config()
    if not isinstance(raw, dict):
        return cfg

    if raw.get("version") != CONFIG_VERSION:
        return cfg  # 版本不符：直接默认（V1 没有迁移需求）

    for key in ("sound_on", "vibrate_on", "show_fps", "head_highlight", "show_grid"):
        if key in raw:
            cfg[key] = bool(raw[key])

    cfg["volume"] = _clamp(raw.get("volume", cfg["volume"]), 0.0, 1.0, cfg["volume"])
    cfg["vibrate_strength"] = _clamp(
        raw.get("vibrate_strength", cfg["vibrate_strength"]), 0.0, 1.0, cfg["vibrate_strength"]
    )
    cfg["touch_sensitivity"] = _clamp(
        raw.get("touch_sensitivity", cfg["touch_sensitivity"]), 0.5, 2.0, cfg["touch_sensitivity"]
    )
    cfg["joystick_deadzone"] = _clamp(
        raw.get("joystick_deadzone", cfg["joystick_deadzone"]), 0.05, 0.5, cfg["joystick_deadzone"]
    )
    cfg["font_size"] = _clamp(raw.get("font_size", cfg["font_size"]), 12.0, 24.0, cfg["font_size"])

    theme = raw.get("theme", cfg["theme"])
    cfg["theme"] = theme if theme in THEMES else "dark"
    mode = raw.get("perf_mode", cfg["perf_mode"])
    cfg["perf_mode"] = mode if mode in PERF_MODES else "balanced"
    return cfg


def home_dir() -> str:
    """数据目录：优先环境变量 SNAKE_HOME（测试/沙箱），否则用户私有目录。"""
    return os.environ.get("SNAKE_HOME") or os.path.join(os.path.expanduser("~"), ".snake_android")


class ConfigStore:
    """config.json 读写。路径注入便于测试（tmp_path）。"""

    def __init__(self, path: str | None = None) -> None:
        self.path = path or os.path.join(home_dir(), "config.json")

    # ---------- 读 ----------
    def load_with_legacy(self) -> tuple[dict, bool | None]:
        """迁移用：返回 (config, 旧版 config 里的 screen_awake)。

        幂等：迁移后字段被删除，下次返回 None，不再动作。
        """
        try:
            with open(self.path, encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, ValueError):
            return default_config(), None
        legacy = None
        if isinstance(raw, dict) and "screen_awake" in raw:
            legacy = bool(raw.pop("screen_awake"))
            cfg = validate(raw)
            try:
                self.save(cfg)  # 写回即删除旧字段
            except OSError:
                pass
            return cfg, legacy
        return validate(raw), None

    def load(self) -> dict:
        try:
            with open(self.path, encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, ValueError):
            return default_config()
        return validate(raw)

    # ---------- 写 ----------
    def save(self, cfg: dict) -> dict:
        cfg = validate(cfg)
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)
        return cfg

    # ---------- 恢复默认（只动 config，不碰 profile / 历史） ----------
    def reset(self) -> dict:
        cfg = default_config()
        self.save(cfg)
        return cfg
