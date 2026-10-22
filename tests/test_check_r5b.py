"""R5B 判定器单测：分级与取更严规则。"""

import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("check_r5b", os.path.join(ROOT, "tools", "check_r5b.py"))
check = importlib.util.module_from_spec(spec)
sys.modules["check_r5b"] = check
spec.loader.exec_module(check)


def test_grade_tiers():
    assert check.grade(95, 10.0) == "目标"
    assert check.grade(92, 15.0) == "及格", "p99 只够及格，取更严"
    assert check.grade(62, 18.0) == "底线", "FPS 及格 + p99 底线 → 底线"
    assert check.grade(56, 19.5) == "底线"
    assert check.grade(50, 25.0) == "不及格"
    assert check.grade(120, 21.0) == "不及格", "p99 超标一票否决"


def test_parse_rows_and_missing():
    text = """
| 时间 | FPS | p50 | p95 | p99 |
|---|---|---|---|---|
| 0 min | 90.0 | 8 | 9 | 10.0 |
| 10 min | 88.0 | 9 | 10 | 11.0 |
大小 24.5 MB
| ☑ | 横屏 | 通过 |
"""
    report = check.parse_report(text)
    assert len(report["b"]) == 2
    assert report["b"][-1]["fps"] == 88.0
    assert report["apk_mb"] == 24.5
    miss = check.missing_items(report)
    assert any("§C" in m for m in miss)
    assert any("截图" in m for m in miss)
