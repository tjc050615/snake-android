"""崩溃日志（M4/R2）：启动时检查上次是否异常退出。

做法：启动写 `.running` 标记，正常退出删除；下次启动若标记还在 → 上次崩了，
追加一条到 crash.log 并清标记。所有异常都吞掉，绝不影响启动。
"""

from __future__ import annotations

import logging
import os
import time

LOG = logging.getLogger("snake.crash")


class CrashGuard:
    def __init__(self, directory: str) -> None:
        self.dir = directory
        self.marker = os.path.join(directory, ".running")
        self.log_path = os.path.join(directory, "crash.log")

    def previous_crash(self) -> bool:
        """检查并清理上次的标记；返回上次是否异常退出。"""
        try:
            if not os.path.exists(self.marker):
                return False
            with open(self.log_path, "a", encoding="utf-8") as fh:
                fh.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] previous run ended abnormally\n")
            os.remove(self.marker)
            return True
        except OSError as exc:  # pragma: no cover
            LOG.warning("crash guard check failed: %s", exc)
            return False

    def start(self) -> None:
        try:
            os.makedirs(self.dir, exist_ok=True)
            with open(self.marker, "w", encoding="utf-8") as fh:
                fh.write(str(os.getpid()))
        except OSError as exc:  # pragma: no cover
            LOG.warning("crash guard start failed: %s", exc)

    def stop(self) -> None:
        try:
            if os.path.exists(self.marker):
                os.remove(self.marker)
        except OSError as exc:  # pragma: no cover
            LOG.warning("crash guard stop failed: %s", exc)
