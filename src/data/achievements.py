"""5 个成就（M4/R2）：判定 + 进度。"""

from __future__ import annotations

ACHIEVEMENTS = (
    ("score_100", 100),
    ("ai_food_100", 100),
    ("wrap_food_100", 100),
    ("play_1h", 3600),
    ("daily_10", 10),
)


def progress(profile: dict, stats: dict) -> dict[str, tuple[int, int]]:
    """返回 {id: (当前值, 目标值)}；stats 为本局/累计统计。"""
    out = {}
    for key, target in ACHIEVEMENTS:
        current = 0
        if key == "score_100":
            current = stats.get("best_score", profile.get("best_score", 0))
        elif key == "ai_food_100":
            current = stats.get("ai_food_best", 0)
        elif key == "wrap_food_100":
            current = stats.get("wrap_food_best", 0)
        elif key == "play_1h":
            current = stats.get("total_seconds", 0)
        elif key == "daily_10":
            current = stats.get("games_today", 0)
        out[key] = (min(current, target), target)
    return out


def evaluate(profile: dict, stats: dict) -> tuple[dict, list[str]]:
    """更新 profile.achievements，返回 (profile, 新解锁 id 列表)。"""
    prof = dict(profile)
    unlocked = dict(prof.get("achievements", {}))
    newly = []
    for key, (current, target) in progress(profile, stats).items():
        if current >= target and not unlocked.get(key):
            unlocked[key] = True
            newly.append(key)
    prof["achievements"] = unlocked
    return prof, newly


def label(key: str) -> str:
    from app import strings

    return strings.t(f"ach_{key}")
