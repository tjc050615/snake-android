"""R5B 数据校验与分级判定（M5）。

用法：
    python tools/check_r5b.py --check-only   # 只查 7 项必采 + 5 图 + 热稳定表齐全
    python tools/check_r5b.py                # 再按四级判定输出结论

退出码：0 = 目标/及格/底线；1 = 不及格或缺数据。
"""

from __future__ import annotations

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "docs", "evidence", "r4-device.md")
EVIDENCE = os.path.join(ROOT, "docs", "evidence")

SHOTS = ("r4-home.png", "r4-game.png", "r4-ai-stats.png", "r4-settings.png", "r4-replay.png")

TIERS = (
    ("目标", 90.0, 11.1),
    ("及格", 60.0, 16.67),
    ("底线", 55.0, 20.0),
)


def grade(fps: float, p99: float) -> str:
    """FPS 与 p99 必须同时满足某级；取更严的一级。"""
    def fps_level(v: float, idx: int) -> int:
        return 2 if v < TIERS[2][1] else (1 if v < TIERS[1][1] else (0 if v < TIERS[0][1] else 0))

    def p99_level(v: float, _idx: int) -> int:
        return 2 if v > TIERS[2][2] else (1 if v > TIERS[1][2] else (0 if v > TIERS[0][2] else 0))

    def level_index(value: float, kind: str) -> int:
        for i, (_name, t_fps, t_p99) in enumerate(TIERS):
            if kind == "fps" and value >= t_fps:
                return i
            if kind == "p99" and value <= t_p99:
                return i
        return len(TIERS)

    idx = max(level_index(fps, "fps"), level_index(p99, "p99"))
    if idx >= len(TIERS):
        return "不及格"
    return TIERS[idx][0]


def _rows(text: str) -> list[list[str]]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("|") and line.count("|") >= 3:
            cells = [c.strip() for c in line.strip("|").split("|")]
            out.append(cells)
    return out


def parse_report(text: str) -> dict:
    rows = _rows(text)
    b_rows, c_rows = [], []
    checklist = 0
    for cells in rows:
        if len(cells) >= 5 and re.match(r"^\d+\s*min", cells[0]):
            try:
                fps = float(cells[1])
                p99 = float(cells[4])
            except ValueError:
                continue
            b_rows.append({"time": cells[0], "fps": fps, "p99": p99})
        elif len(cells) == 3 and re.match(r"^\d+\s*min", cells[0]):
            try:
                mem = float(cells[1])
            except ValueError:
                mem = None
            c_rows.append({"time": cells[0], "mem": mem, "temp": cells[2]})
        elif "☑" in cells:
            checklist += 1

    apk_mb = None
    m = re.search(r"大小\s*([\d.]+)\s*MB", text)
    if m:
        apk_mb = float(m.group(1))

    return {"b": b_rows, "c": c_rows, "checklist": checklist, "apk_mb": apk_mb}


def missing_items(report: dict) -> list[str]:
    miss = []
    if len(report["b"]) < 4:
        miss.append(f"§B 帧时间表不足 4 行（当前 {len(report['b'])}）")
    if len(report["c"]) < 4:
        miss.append(f"§C 内存/温度表不足 4 行（当前 {len(report['c'])}）")
    if report["apk_mb"] is None:
        miss.append("§A 缺 APK 体积（格式：大小 XX.X MB）")
    if report["checklist"] < 20:
        miss.append(f"§D 勾选项不足 20（当前 {report['checklist']}）")
    for shot in SHOTS:
        if not os.path.exists(os.path.join(EVIDENCE, shot)):
            miss.append(f"缺截图 docs/evidence/{shot}")
    return miss


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(REPORT):
        print(f"未找到 {os.path.relpath(REPORT, ROOT)}，请按 docs/R5B-DATA-GUIDE.md 回填")
        return 1

    text = open(REPORT, encoding="utf-8").read()
    report = parse_report(text)
    missing = missing_items(report)

    if missing:
        print("缺项：")
        for item in missing:
            print(" -", item)
        return 1
    print("数据齐全：4 行帧时间 + 4 行内存/温度 + APK 体积 + 20 项清单 + 5 张截图")

    if args.check_only:
        return 0

    final = report["b"][-1]
    verdict = grade(final["fps"], final["p99"])
    print(f"判定（{final['time']}）：{final['fps']:.1f} fps / p99 {final['p99']:.2f} ms → {verdict}")
    worst = max(report["c"], key=lambda r: r["mem"] or 0)
    print(f"内存峰值：{worst['mem']} MB @ {worst['time']}；APK：{report['apk_mb']} MB")

    if verdict == "不及格":
        print("建议降载：AI 7.0→6.0ms、render 批处理、FBO 缓存，再复测")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
