"""M4/R4：buildozer.spec 与安卓数据目录的测试。"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = open(os.path.join(ROOT, "buildozer.spec"), encoding="utf-8").read()


def _spec(key):
    m = re.search(rf"^{re.escape(key)}\s*=\s*(.+)$", SPEC, re.M)
    return m.group(1).strip() if m else None


def test_android_orientation_landscape():
    assert _spec("orientation") == "landscape"
    assert _spec("fullscreen") == "1"


def test_android_api_and_permissions():
    assert _spec("android.minapi") == "23"
    assert _spec("android.api") == "33"
    assert "VIBRATE" in (_spec("android.permissions") or "")


def test_versions_pinned():
    assert "kivy==2.3.0" in _spec("requirements")
    assert "buildozer==1.5.0" in SPEC, "必须在 spec 注释里锁定 buildozer 版本"


def test_apk_excludes_dev_files():
    excluded = _spec("source.exclude_dirs") or ""
    for name in ("tests", "tools", "docs", ".venv", ".data"):
        assert name in excluded, f"{name} 必须排除"
    patterns = _spec("source.exclude_patterns") or ""
    assert "docs/evidence" in patterns


def test_include_only_needed_exts():
    exts = _spec("source.include_exts") or ""
    assert "otf" in exts, "Noto 字体必须进 APK"
    assert "wav" in exts
    for bad in ("md", "spec"):
        assert bad not in exts.split(",")


def test_home_dir_android_uses_user_data_dir():
    from data.storage import home_dir

    assert home_dir(platform_name="android", user_data_dir="/data/user/0/org.example.snake/files") == \
        "/data/user/0/org.example.snake/files"
    assert home_dir(platform_name="linux", user_data_dir="/tmp/x") == os.path.join(
        os.path.expanduser("~"), ".snake_android"
    )


def test_home_dir_env_override(monkeypatch, tmp_path):
    from data.storage import home_dir

    monkeypatch.setenv("SNAKE_HOME", str(tmp_path))
    assert home_dir() == str(tmp_path)
