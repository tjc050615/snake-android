"""profile.json（M4/R2）：最高分 / 历史 / 成就 / 引导 / 常亮。

与 config 分开存：恢复默认设置不能清掉历史与成就（D-031 / R1 验收）。
"""

from __future__ import annotations

import json
import os

PROFILE_VERSION = 1
HISTORY_SIZE = 20

DEFAULTS: dict = {
    "version": PROFILE_VERSION,
    "best_score": 0,
    "best_score_human": 0,
    "best_score_ai": 0,
    "total_games": 0,
    "achievements": {},
    "onboarding_done": False,
    "screen_awake": True,
    "history": [],
}

HISTORY_FIELDS = ("mode", "duration", "score", "seed", "time", "is_ai", "wrap")


def default_profile() -> dict:
    return json.loads(json.dumps(DEFAULTS))


def _valid_entry(entry) -> bool:
    if not isinstance(entry, dict):
        return False
    return all(k in entry for k in HISTORY_FIELDS)


def validate_profile(raw) -> dict:
    prof = default_profile()
    if not isinstance(raw, dict) or raw.get("version") != PROFILE_VERSION:
        return prof

    try:
        prof["best_score"] = max(0, int(raw.get("best_score", 0)))
        prof["best_score_human"] = max(0, int(raw.get("best_score_human", 0)))
        prof["best_score_ai"] = max(0, int(raw.get("best_score_ai", 0)))
        prof["total_games"] = max(0, int(raw.get("total_games", 0)))
    except (TypeError, ValueError):
        pass

    prof["onboarding_done"] = bool(raw.get("onboarding_done", False))
    prof["screen_awake"] = bool(raw.get("screen_awake", True))

    ach = raw.get("achievements", {})
    prof["achievements"] = {
        str(k): bool(v) for k, v in ach.items()
    } if isinstance(ach, dict) else {}

    hist = raw.get("history", [])
    entries = [e for e in hist if _valid_entry(e)] if isinstance(hist, list) else []
    prof["history"] = entries[-HISTORY_SIZE:]
    return prof


class ProfileStore:
    def __init__(self, path: str | None = None) -> None:
        from data.storage import home_dir

        self.path = path or os.path.join(home_dir(), "profile.json")

    def load(self) -> dict:
        try:
            with open(self.path, encoding="utf-8") as fh:
                return validate_profile(json.load(fh))
        except (OSError, ValueError):
            return default_profile()

    def save(self, profile: dict) -> dict:
        prof = validate_profile(profile)
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(prof, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)
        return prof

    # ---------- 业务 ----------
    def record_game(self, profile: dict, entry: dict) -> dict:
        """记一局：更新历史（超 20 淘汰最旧）、最高分、总局数。"""
        prof = validate_profile(profile)
        entry = {k: entry.get(k) for k in HISTORY_FIELDS}
        prof["history"] = (prof["history"] + [entry])[-HISTORY_SIZE:]
        prof["total_games"] += 1
        try:
            score = int(entry["score"] or 0)
            prof["best_score"] = max(prof["best_score"], score)
            key = "best_score_ai" if entry.get("is_ai") else "best_score_human"
            prof[key] = max(prof[key], score)
        except (TypeError, ValueError):
            pass
        return prof

    def clear_history(self, profile: dict) -> dict:
        prof = validate_profile(profile)
        prof["history"] = []
        return prof
