"""持久化写入的 debounce（M4/R2）：滑块拖动只在停下后写盘。

纯逻辑，时钟可注入（测试用假时钟）。写盘失败只记 warning，不影响内存态。
"""

from __future__ import annotations

import logging

LOG = logging.getLogger("snake.storage")


class DebouncedSaver:
    def __init__(self, store, delay: float = 0.5) -> None:
        self.store = store
        self.delay = delay
        self._pending: dict | None = None
        self.saves = 0
        self.failures = 0

    def request(self, cfg: dict) -> None:
        """记录待写配置；真正写盘由 flush() 触发（App 用 Clock 延时调用）。"""
        self._pending = dict(cfg)

    @property
    def pending(self) -> bool:
        return self._pending is not None

    def flush(self) -> bool:
        """写盘。成功返回 True；失败捕获异常、保留内存态并返回 False。"""
        if self._pending is None:
            return True
        cfg = self._pending
        self._pending = None
        try:
            self.store.save(cfg)
            self.saves += 1
            return True
        except Exception as exc:  # pragma: no cover - 磁盘异常路径
            self.failures += 1
            LOG.warning("config save failed, keep in-memory state: %s", exc)
            return False
