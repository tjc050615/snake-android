"""局部 A*（M3/R1）。

- 4 邻域、曼哈顿启发
- 堆优化开放列表，平局键 `(f, h, x, y)`
- 节点来自对象池，搜索结束全部归还（不泄漏）
- 视野外的格子视为未知/不可通行
"""

from __future__ import annotations

import heapq
import time
from dataclasses import dataclass, field


class NodePool:
    """极简节点池：复用 Node 对象，避免每次搜索产生大量临时对象。"""

    def __init__(self) -> None:
        self._free: list["Node"] = []
        self.created = 0
        self.in_use = 0

    def acquire(self, cell, g: int, f: int, parent: "Node | None") -> "Node":
        node = self._free.pop() if self._free else self._new()
        node.cell = cell
        node.g = g
        node.f = f
        node.parent = parent
        self.in_use += 1
        return node

    def release(self, node: "Node") -> None:
        node.parent = None
        self._free.append(node)
        self.in_use -= 1

    def reset(self) -> None:
        self._free.clear()
        self.created = 0
        self.in_use = 0

    def _new(self) -> "Node":
        self.created += 1
        return Node()


@dataclass
class Node:
    cell: tuple[int, int] = (0, 0)
    g: int = 0
    f: int = 0
    parent: "Node | None" = field(default=None, repr=False)


NEIGHBORS = ((1, 0), (0, 1), (-1, 0), (0, -1))  # 右、上、左、下（与平局键配合）


def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar(
    start: tuple[int, int],
    goal: tuple[int, int],
    passable,
    rect: tuple[int, int, int, int],
    pool: NodePool | None = None,
    max_nodes: int = 4000,
    deadline: float | None = None,
    check_every: int = 100,
) -> list[tuple[int, int]]:
    """返回从 start 的下一步到 goal 的路径（含 goal，不含 start）。

    - 找不到路径返回 []
    - `deadline`（time.perf_counter 时间戳）到期时中断：
      已找到目标则返回该路径；否则返回"当前最优节点"的路径（部分路径），
      由调用方再做 O(1) 安全校验与降级。
    """
    if start == goal:
        return []

    x0, y0, x1, y1 = rect
    pool = pool or NodePool()

    def in_rect(c: tuple[int, int]) -> bool:
        return x0 <= c[0] <= x1 and y0 <= c[1] <= y1

    open_heap: list[tuple[int, int, int, int, int]] = []
    nodes: dict[tuple[int, int], Node] = {}

    start_node = pool.acquire(start, 0, manhattan(start, goal), None)
    nodes[start] = start_node
    heapq.heappush(open_heap, (start_node.f, manhattan(start, goal), start[0], start[1], 0))

    closed: set[tuple[int, int]] = set()
    counter = 1
    expanded = 0
    found: Node | None = None
    best_node: Node = start_node
    best_h = manhattan(start, goal)
    timed_out = False

    while open_heap:
        if deadline is not None and expanded % check_every == 0 and time.perf_counter() > deadline:
            timed_out = True
            break

        _f, _h, _x, _y, _seq = heapq.heappop(open_heap)
        cell = (_x, _y)
        if cell in closed:
            continue
        closed.add(cell)
        expanded += 1
        if expanded > max_nodes:
            break

        h_cell = manhattan(cell, goal)
        if h_cell < best_h:
            best_h = h_cell
            best_node = nodes[cell]

        if cell == goal:
            found = nodes[cell]
            break

        node = nodes[cell]
        for dx, dy in NEIGHBORS:
            nxt = (cell[0] + dx, cell[1] + dy)
            if not in_rect(nxt) or nxt in closed:
                continue
            if not passable(nxt):
                continue
            tentative_g = node.g + 1
            prev = nodes.get(nxt)
            if prev is not None and prev.g <= tentative_g:
                continue
            h = manhattan(nxt, goal)
            if prev is None:
                child = pool.acquire(nxt, tentative_g, tentative_g + h, node)
                nodes[nxt] = child
            else:
                prev.g = tentative_g
                prev.f = tentative_g + h
                prev.parent = node
                child = prev
            heapq.heappush(open_heap, (child.f, h, nxt[0], nxt[1], counter))
            counter += 1

    path: list[tuple[int, int]] = []
    if found is None and timed_out and best_node is not start_node:
        found = best_node  # 超时：返回"当前最优"的部分路径

    if found is not None:
        cur = found
        while cur is not None and cur.parent is not None:
            path.append(cur.cell)
            cur = cur.parent
        path.reverse()

    for node in nodes.values():
        pool.release(node)
    return path
