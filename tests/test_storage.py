"""M4/R1 第二步：config 持久化、主题、字体混排、UI 中文化。"""

import ast
import json
import os

import pytest

from app import strings
from app.theme import palette
from core.layout import content_height
from data.storage import CONFIG_VERSION, ConfigStore, default_config, validate


# ---------- config 持久化 ----------
def test_config_survives_restart(tmp_path):
    path = str(tmp_path / "config.json")
    store = ConfigStore(path)
    cfg = store.load()
    assert cfg == default_config()

    cfg["theme"] = "light"
    cfg["perf_mode"] = "performance"
    cfg["font_size"] = 22.0
    cfg["sound_on"] = False
    store.save(cfg)

    again = ConfigStore(path).load()  # 模拟重启
    assert again["theme"] == "light"
    assert again["perf_mode"] == "performance"
    assert again["font_size"] == 22.0
    assert again["sound_on"] is False


def test_config_corrupt_falls_back_to_defaults(tmp_path):
    path = str(tmp_path / "config.json")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("{not json")
    assert ConfigStore(path).load() == default_config()


def test_config_version_mismatch_falls_back(tmp_path):
    path = str(tmp_path / "config.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"version": 999, "theme": "light"}, fh)
    assert ConfigStore(path).load()["theme"] == "dark"


def test_config_clamps_out_of_range(tmp_path):
    path = str(tmp_path / "config.json")
    store = ConfigStore(path)
    store.save({"version": CONFIG_VERSION, "volume": 5.0, "font_size": 99.0,
                "theme": "neon", "perf_mode": "turbo"})
    cfg = store.load()
    assert cfg["volume"] == 1.0
    assert cfg["font_size"] == 24.0
    assert cfg["theme"] == "dark"
    assert cfg["perf_mode"] == "balanced"


def test_settings_reset_keeps_profile(tmp_path):
    """恢复默认只重置 config，不碰 profile / 历史。"""
    cfg_path = tmp_path / "config.json"
    profile_path = tmp_path / "profile.json"
    profile_path.write_text('{"best_score": 42}', encoding="utf-8")

    store = ConfigStore(str(cfg_path))
    store.save({**default_config(), "theme": "light"})
    store.reset()

    assert ConfigStore(str(cfg_path)).load()["theme"] == "dark"
    assert profile_path.exists(), "profile 不应被删除"
    assert json.loads(profile_path.read_text(encoding="utf-8"))["best_score"] == 42


def test_perf_mode_survives_restart(tmp_path):
    path = str(tmp_path / "config.json")
    store = ConfigStore(path)
    cfg = store.load()
    for mode in ("battery", "performance", "balanced"):
        cfg["perf_mode"] = mode
        store.save(cfg)
        assert ConfigStore(path).load()["perf_mode"] == mode


# ---------- 主题 ----------
def test_theme_dark_light_switch():
    dark, light = palette("dark"), palette("light")
    assert dark["bg"] != light["bg"]
    assert dark["text"] != light["text"]
    assert palette("nope") is dark, "未知主题回落暗色"


# ---------- 设置面板可滚动 ----------
def test_settings_panel_scrollable_at_max_font():
    """12+ 项、字号 24 时，内容高度必须超过 1280×720 下的面板视口。"""
    viewport_h = 720 - 44 - 20   # 减去标题与内边距
    assert content_height(13, 24.0) > viewport_h
    assert content_height(13, 16.0) > viewport_h * 0.8


# ---------- 中文化 ----------
def _iter_src():
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def test_no_hardcoded_cn():
    """除 strings.py 外，源码里不允许出现中文 UI 字面量（docstring 除外）。"""
    offenders = []
    for path in _iter_src():
        if path.endswith(os.path.join("app", "strings.py")):
            continue
        tree = ast.parse(open(path, encoding="utf-8").read())
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                body = getattr(node, "body", [])
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                    if isinstance(body[0].value.value, str):
                        docstrings.add(id(body[0].value))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if id(node) in docstrings:
                    continue
                if _has_cjk(node.value):
                    offenders.append((os.path.basename(path), node.lineno, node.value[:20]))
    assert not offenders, f"发现硬编码中文：{offenders}"


def test_font_mix_render():
    """字体文件存在且混排文案齐全（真实渲染由截图验收）。"""
    from app import fonts

    assert fonts.font_path() is not None
    assert "得分 0" in f"{strings.t('score')} 0"
    assert "%" not in strings.t("volume")
    assert strings.t("volume") and strings.t("fps")
