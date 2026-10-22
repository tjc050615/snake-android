"""确定性随机（D-029）。

约束：
- 同 seed + 同坐标 → 同结果，且**跨进程一致**（所以不能用内置 hash()）。
- 禁止使用全局 random 状态：所有随机都必须由坐标派生。

实现：splitmix64 + 坐标/种子混合。纯函数，无状态。
"""

MASK64 = (1 << 64) - 1
_GOLDEN = 0x9E3779B97F4A7C15
_M1 = 0xBF58476D1CE4E5B9
_M2 = 0x94D049BB133111EB


def splitmix64(x: int) -> int:
    """splitmix64 终混函数，输入输出均为 64 位无符号整数。"""
    z = (x + _GOLDEN) & MASK64
    z = ((z ^ (z >> 30)) * _M1) & MASK64
    z = ((z ^ (z >> 27)) * _M2) & MASK64
    return (z ^ (z >> 31)) & MASK64


def _cell_bits(x: int, y: int) -> int:
    """把有符号格坐标压成 64 位，保证负坐标也有稳定位模式。"""
    return (x & 0xFFFFFFFF) | ((y & 0xFFFFFFFF) << 32)


def cell_hash(seed: int, x: int, y: int, salt: int = 0) -> int:
    """(seed, x, y, salt) → 64 位哈希。salt 用于同一格派生多个独立随机值。"""
    mixed = (_cell_bits(x, y) ^ splitmix64((seed ^ (salt * 0xD1B54A32D192ED03)) & MASK64)) & MASK64
    return splitmix64(mixed)


def cell_unit(seed: int, x: int, y: int, salt: int = 0) -> float:
    """均匀分布在 [0, 1) 的确定性浮点。"""
    return cell_hash(seed, x, y, salt) / 18446744073709551616.0


def cell_int(seed: int, x: int, y: int, mod: int, salt: int = 0) -> int:
    """[0, mod) 的确定性整数；mod 必须 > 0。"""
    if mod <= 0:
        raise ValueError("mod must be positive")
    return cell_hash(seed, x, y, salt) % mod


def chunk_hash(seed: int, cx: int, cy: int, salt: int = 0) -> int:
    """chunk 级哈希：用 chunk 原点格代表整个 chunk。"""
    return cell_hash(seed, cx, cy, salt)
