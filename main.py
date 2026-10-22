#!/usr/bin/env python3
"""项目入口：把 src/ 加入 sys.path 后启动 Kivy 应用。

用法：
    python main.py                 # 正常启动（桌面窗口 1280x720）
    python main.py --smoke 2       # 启动后 2 秒自动退出并打印诊断（CI 用）

注意：Kivy 2.3.0 需要 Python 3.8~3.12；本仓库用 .venv（3.11）运行。
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

# 沙箱/无 HOME 环境下 Kivy 会尝试写用户日志并卡死，默认禁用文件日志。
os.environ.setdefault("KIVY_NO_FILELOG", "1")
os.environ.setdefault("KIVY_HOME", os.path.join(ROOT, ".kivyhome"))
# 阻止 Kivy 抢占命令行参数（否则 --smoke 会被 Kivy 当成自己的选项而报 usage 退出）
os.environ.setdefault("KIVY_NO_ARGS", "1")


def _parse_smoke(argv: list[str]) -> float:
    """解析 --smoke [秒]，返回秒数；未指定返回 0。"""
    if "--smoke" not in argv:
        return 0.0
    idx = argv.index("--smoke")
    if idx + 1 < len(argv):
        try:
            return max(0.5, float(argv[idx + 1]))
        except ValueError:
            return 2.0
    return 2.0


def _parse_speed(argv: list[str]) -> float:
    """解析 --speed N（0.5~10），默认 1.0。"""
    if "--speed" not in argv:
        return 1.0
    idx = argv.index("--speed")
    if idx + 1 < len(argv):
        try:
            return min(max(float(argv[idx + 1]), 0.5), 10.0)
        except ValueError:
            return 1.0
    return 1.0


def _parse_size(argv: list[str]) -> tuple[int, int] | None:
    """解析 --size WxH（物理像素），未指定返回 None。"""
    if "--size" not in argv:
        return None
    idx = argv.index("--size")
    if idx + 1 >= len(argv):
        return None
    raw = argv[idx + 1].lower().replace("*", "x")
    try:
        w, h = raw.split("x")
        return (int(w), int(h))
    except (ValueError, TypeError):
        return None


def main() -> int:
    try:
        from app.app import SnakeApp  # noqa: PLC0415
    except ImportError as exc:
        print("[错误] 无法导入 Kivy 或项目模块：", exc)
        print("       请先创建虚拟环境并安装：.venv\\Scripts\\pip install -r requirements.txt")
        print("       Kivy 2.3.0 需要 Python 3.8~3.12。")
        return 1

    app = SnakeApp()
    app.smoke_seconds = _parse_smoke(sys.argv)
    app.demo = "--demo" in sys.argv
    app.interp = "--interp" in sys.argv
    app.hyst = "--hyst" in sys.argv
    app.obstacle_shot = "--obstacles" in sys.argv or "--walls" in sys.argv
    app.wall_shot = "--walls" in sys.argv
    app.wrap = "--wrap" in sys.argv
    app.wrap_scene = app.wrap
    app.spawn_shot = "--spawnshot" in sys.argv
    app.ai = "--ai" in sys.argv
    app.clip_demo = "--clipdemo" in sys.argv
    app.settings_shot = "--settings" in sys.argv
    app.history_shot = "--history" in sys.argv
    for _arg in sys.argv:
        if _arg.startswith("--theme="):
            app.theme_override = _arg.split("=", 1)[1]
        elif _arg.startswith("--font="):
            app.font_override = float(_arg.split("=", 1)[1])
    app.speed = _parse_speed(sys.argv)
    app.window_size = _parse_size(sys.argv)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
