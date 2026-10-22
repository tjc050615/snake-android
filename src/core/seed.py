"""种子解析（M4/R2）：显示 / 复制 / 输入复现。

规则：仅接受十进制非负整数，范围 [0, 2^31-1]；其它一律返回 None 并给出提示文案 key。
"""

from __future__ import annotations

MAX_SEED = 2**31 - 1


def parse_seed(text: str) -> int | None:
    if text is None:
        return None
    s = str(text).strip()
    if not s or not s.isdigit():
        return None
    try:
        value = int(s)
    except ValueError:
        return None
    if value < 0 or value > MAX_SEED:
        return None
    return value


def format_seed(seed: int) -> str:
    return str(int(seed))
