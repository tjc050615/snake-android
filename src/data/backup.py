"""设置与历史导入导出（M4/R2）：一个 JSON 文件同时装 config + profile。

导入时校验 schema 版本与结构，非法文件抛 ValueError（调用方提示，不崩）。
"""

from __future__ import annotations

import json

from data.profile import validate_profile
from data.storage import validate as validate_config

BUNDLE_VERSION = 1


def make_bundle(config: dict, profile: dict) -> dict:
    return {
        "bundle_version": BUNDLE_VERSION,
        "config": dict(config),
        "profile": dict(profile),
    }


def export_bundle(path: str, config: dict, profile: dict) -> str:
    bundle = make_bundle(config, profile)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, ensure_ascii=False, indent=2)
    return path


def import_bundle(path: str) -> tuple[dict, dict]:
    """返回 (config, profile)；文件坏 / 版本不符 / 结构不对 → ValueError。"""
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ValueError(f"invalid backup file: {exc}") from exc

    if not isinstance(raw, dict) or raw.get("bundle_version") != BUNDLE_VERSION:
        raise ValueError("unsupported backup version")
    if not isinstance(raw.get("config"), dict) or not isinstance(raw.get("profile"), dict):
        raise ValueError("backup missing config/profile")

    return validate_config(raw["config"]), validate_profile(raw["profile"])
