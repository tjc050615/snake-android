"""音效 / 震动（M4/R3）：缺文件静默、桌面震动 no-op、安卓 M5 接 pyjnius。"""

from __future__ import annotations

import logging
import os

LOG = logging.getLogger("snake.audio")

SOUND_FILES = {
    "eat": "eat.wav",
    "die": "die.wav",
    "achievement": "achievement.wav",
}


class SoundManager:
    def __init__(self, directory: str, enabled: bool = True, volume: float = 0.8) -> None:
        self.dir = directory
        self.enabled = enabled
        self.volume = max(0.0, min(1.0, volume))
        self.played: list[str] = []

    def available(self, name: str) -> bool:
        return os.path.exists(os.path.join(self.dir, SOUND_FILES.get(name, "")))

    def play(self, name: str) -> bool:
        """缺文件 / 关闭音效 / 加载失败 → 返回 False，不抛异常。"""
        if not self.enabled:
            return False
        path = os.path.join(self.dir, SOUND_FILES.get(name, ""))
        if not os.path.exists(path):
            return False
        try:
            from kivy.core.audio import SoundLoader  # noqa: PLC0415

            sound = SoundLoader.load(path)
            if sound is None:
                return False
            sound.volume = self.volume
            sound.play()
            self.played.append(name)
            return True
        except Exception as exc:  # pragma: no cover
            LOG.warning("sound play failed: %s", exc)
            return False


class Haptics:
    """桌面 no-op；安卓 M5 用 pyjnius 调 Vibrator。"""

    def __init__(self, enabled: bool = True, strength: float = 0.5) -> None:
        self.enabled = enabled
        self.strength = max(0.0, min(1.0, strength))
        self.calls: list[str] = []

    def vibrate_ms(self, ms: int) -> bool:
        if not self.enabled:
            return False
        self.calls.append(f"{int(ms)}ms")
        return True

    def vibrate(self, name: str) -> bool:
        if not self.enabled:
            return False
        self.calls.append(name)  # 桌面只记录
        return True
