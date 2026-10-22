"""地形/食物生成（纯函数，D-029 / D-026 / D-027 / D-028）。

范围：
- 食物：每 chunk 3~5 个
- 障碍（R2）：≈5%，只取内部格，因此 chunk 边界整行/整列天然无障碍
- 墙壁（R3）：0~2 条、3~8 格、横/竖/拐角，不贴边界、与障碍/其它墙留 1 格通道，
  生成后用**真正的洪水填充**校验连通；3 次不通过则降级（只留障碍）

性能：连通校验与孤立格修复都在 32×32 的扁平数组上做（索引 = lx + 32*ly），
避免 Python 元组集合的开销；单 chunk 生成 p95 目标 ≤3ms。
"""

from __future__ import annotations

from app import constants as C
from core import rng

N = C.CHUNK_SIZE
N2 = N * N

OBSTACLE_SALT_BASE = 0x2000
WALL_SALT_BASE = 0x5000
INTERIOR_LO = 1
INTERIOR_HI = N - 1

WALL_MAX_COUNT = 2
WALL_MIN_LEN = 3
WALL_MAX_LEN = 8
WALL_ATTEMPTS = 3


# ============================== 坐标工具 ==============================

def _local_index(lx: int, ly: int) -> int:
    return lx + N * ly


def _to_local(cx: int, cy: int, cell: tuple[int, int]) -> tuple[int, int]:
    return (cell[0] - cx * N, cell[1] - cy * N)


# ============================== 食物 ==============================

def chunk_food_count(seed: int, cx: int, cy: int) -> int:
    """每 chunk 食物数量：3~5（D-030），由 chunk 哈希决定，稳定可复现。"""
    span = C.FOOD_PER_CHUNK_MAX - C.FOOD_PER_CHUNK_MIN + 1
    return C.FOOD_PER_CHUNK_MIN + rng.chunk_hash(seed, cx, cy, salt=0x1) % span


def candidate_cell(seed: int, cx: int, cy: int, salt: int) -> tuple[int, int]:
    """第 salt 个候选格：落在该 chunk 内（含边界）。"""
    h = rng.chunk_hash(seed, cx, cy, salt=salt)
    x = cx * N + (h % N)
    y = cy * N + ((h >> 32) % N)
    return (x, y)


def interior_cell(seed: int, cx: int, cy: int, salt: int) -> tuple[int, int]:
    """第 salt 个"内部格"候选：局部坐标 ∈ [1, 30]，天然避开 chunk 边界。"""
    h = rng.chunk_hash(seed, cx, cy, salt=salt)
    span = INTERIOR_HI - INTERIOR_LO
    x = cx * N + INTERIOR_LO + (h % span)
    y = cy * N + INTERIOR_LO + ((h >> 32) % span)
    return (x, y)


def chunk_food_cells(
    seed: int,
    cx: int,
    cy: int,
    count: int | None = None,
    salt_start: int = 1,
) -> list[tuple[int, int]]:
    """该 chunk 的初始食物格（去重、排序）。"""
    need = chunk_food_count(seed, cx, cy) if count is None else count
    cells: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    salt = salt_start
    while len(cells) < need and salt < salt_start + 4096:
        cell = candidate_cell(seed, cx, cy, salt)
        salt += 1
        if cell in seen:
            continue
        seen.add(cell)
        cells.append(cell)
    cells.sort()
    return cells


# ============================== 出生保护 ==============================

def in_spawn_protection(cx: int, cy: int) -> bool:
    """出生保护：cx ∈ [-1,1] × cy ∈ [-1,1]，共 9 个 chunk（D-007）。"""
    r = C.SPAWN_PROTECT_CHUNKS
    return -r <= cx <= r and -r <= cy <= r


# ============================== 障碍 ==============================

def chunk_obstacle_count(seed: int, cx: int, cy: int) -> int:
    if in_spawn_protection(cx, cy):
        return 0
    return round(C.OBSTACLE_DENSITY * N2)


def _isolated_fix(grid: bytearray) -> None:
    """把被 4 个阻挡格围死的空格救出来（确定性、有上限）。"""
    for _ in range(64):
        target: int | None = None
        for ly in range(N):
            base = N * ly
            for lx in range(N):
                i = base + lx
                if grid[i]:
                    continue
                free = (
                    (lx > 0 and not grid[i - 1])
                    + (lx < N - 1 and not grid[i + 1])
                    + (ly > 0 and not grid[i - N])
                    + (ly < N - 1 and not grid[i + N])
                )
                if free == 0:
                    target = i
                    break
            if target is not None:
                break
        if target is None:
            return

        lx, ly = target % N, target // N
        cands = []
        if lx > 0 and grid[target - 1]:
            cands.append(target - 1)
        if lx < N - 1 and grid[target + 1]:
            cands.append(target + 1)
        if ly > 0 and grid[target - N]:
            cands.append(target - N)
        if ly < N - 1 and grid[target + N]:
            cands.append(target + N)
        if not cands:
            return
        cands.sort(key=lambda k: (k % N, k // N))
        grid[cands[0]] = 0


def chunk_obstacle_cells(seed: int, cx: int, cy: int) -> list[tuple[int, int]]:
    """生成障碍格（确定性、去重、排序、修复孤立格）。"""
    need = chunk_obstacle_count(seed, cx, cy)
    if need <= 0:
        return []

    grid = bytearray(N2)
    placed = 0
    salt = OBSTACLE_SALT_BASE
    limit = salt + 8192
    while placed < need and salt < limit:
        lx = INTERIOR_LO + (rng.chunk_hash(seed, cx, cy, salt) % (N - 2))
        ly = INTERIOR_LO + ((rng.chunk_hash(seed, cx, cy, salt) >> 32) % (N - 2))
        salt += 1
        i = _local_index(lx, ly)
        if grid[i]:
            continue
        grid[i] = 1
        placed += 1

    _isolated_fix(grid)

    x0, y0 = cx * N, cy * N
    return [
        (x0 + (i % N), y0 + (i // N))
        for i in range(N2)
        if grid[i]
    ]


# ============================== 墙壁 ==============================

def _wall_spans(length: int, kind: int) -> tuple[int, int]:
    if kind == 0:
        return (length, 1)
    if kind == 1:
        return (1, length)
    a = max(2, length // 2)
    b = length - a + 1
    return (a, b)


def _wall_offsets(length: int, kind: int) -> list[tuple[int, int]]:
    """局部坐标偏移：0=横 1=竖 2=拐角（先横后竖，共享拐点）。"""
    if kind == 0:
        return [(i, 0) for i in range(length)]
    if kind == 1:
        return [(0, i) for i in range(length)]
    a = max(2, length // 2)
    b = length - a + 1
    return [(i, 0) for i in range(a)] + [(a - 1, j) for j in range(1, b)]


def chunk_wall_plan(seed: int, cx: int, cy: int, attempt: int) -> list[list[tuple[int, int]]]:
    """第 attempt 次尝试的墙（世界坐标，分条返回）；出生保护返回空。"""
    if in_spawn_protection(cx, cy):
        return []

    h = rng.chunk_hash(seed, cx, cy, salt=WALL_SALT_BASE + attempt * 31)
    count = h % (WALL_MAX_COUNT + 1)
    if count == 0:
        return []

    x0, y0 = cx * N, cy * N
    walls: list[list[tuple[int, int]]] = []
    for i in range(count):
        hh = rng.chunk_hash(seed, cx, cy, salt=WALL_SALT_BASE + attempt * 31 + i * 7 + 1)
        length = WALL_MIN_LEN + (hh % (WALL_MAX_LEN - WALL_MIN_LEN + 1))
        kind = (hh >> 8) % 3
        span_x, span_y = _wall_spans(length, kind)

        lx = INTERIOR_LO + (hh >> 16) % (N - 1 - span_x)
        ly = INTERIOR_LO + (hh >> 24) % (N - 1 - span_y)
        walls.append([(x0 + lx + dx, y0 + ly + dy) for dx, dy in _wall_offsets(length, kind)])
    return walls


def _touches_any(cells: list[tuple[int, int]], blocked: set[tuple[int, int]]) -> bool:
    for x, y in cells:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if (x + dx, y + dy) in blocked:
                    return True
    return False


def _connected_local(grid: bytearray) -> bool:
    """32×32 网格上从 (0,0) 洪水填充，必须覆盖所有非阻挡格。"""
    if grid[0]:
        return False
    seen = bytearray(N2)
    seen[0] = 1
    stack = [0]
    visited = 1
    while stack:
        i = stack.pop()
        lx = i % N
        ly = i // N
        if lx > 0:
            j = i - 1
            if not grid[j] and not seen[j]:
                seen[j] = 1
                visited += 1
                stack.append(j)
        if lx < N - 1:
            j = i + 1
            if not grid[j] and not seen[j]:
                seen[j] = 1
                visited += 1
                stack.append(j)
        if ly > 0:
            j = i - N
            if not grid[j] and not seen[j]:
                seen[j] = 1
                visited += 1
                stack.append(j)
        if ly < N - 1:
            j = i + N
            if not grid[j] and not seen[j]:
                seen[j] = 1
                visited += 1
                stack.append(j)
    return visited == N2 - sum(grid)


def chunk_wall_cells(
    seed: int,
    cx: int,
    cy: int,
    obstacles: set[tuple[int, int]],
) -> tuple[list[tuple[int, int]], bool]:
    """生成墙壁并做连通性校验，返回 (walls, degraded)。"""
    if in_spawn_protection(cx, cy):
        return [], False

    for attempt in range(WALL_ATTEMPTS):
        walls = chunk_wall_plan(seed, cx, cy, attempt)
        if not walls:
            return [], False

        flat = [cell for wall in walls for cell in wall]
        flat_set = set(flat)

        if _touches_any(flat, obstacles):
            continue
        conflict = False
        for i in range(len(walls)):
            for j in range(i + 1, len(walls)):
                if _touches_any(walls[i], set(walls[j])):
                    conflict = True
                    break
            if conflict:
                break
        if conflict:
            continue

        grid = bytearray(N2)
        for cell in obstacles:
            lx, ly = _to_local(cx, cy, cell)
            if 0 <= lx < N and 0 <= ly < N:
                grid[_local_index(lx, ly)] = 1
        for cell in flat_set:
            lx, ly = _to_local(cx, cy, cell)
            if 0 <= lx < N and 0 <= ly < N:
                grid[_local_index(lx, ly)] = 1

        if _connected_local(grid):
            return sorted(flat_set), False

    return [], True
