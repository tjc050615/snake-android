"""新手引导（M4/R2）：全局只显示一次，完成状态存 profile。"""

from __future__ import annotations

STEPS = 3


def should_show(profile: dict) -> bool:
    return not bool(profile.get("onboarding_done", False))


def mark_done(profile: dict) -> dict:
    prof = dict(profile)
    prof["onboarding_done"] = True
    return prof
