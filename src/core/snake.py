"""蛇模型（R2）。

规则（D-055）：
- 只有一种碰撞判定：**自撞死亡**。M1/R2 无墙无障碍，`World.is_passable` 恒 True。
- 只有一个事件：**吃食物** → 长度 +1、`ate_food = True`。
- 禁止 180° 反向（长度 > 1 时）。
- 蛇身用 deque 存（头在左），另用 set 做 O(1) 占位查询。
- 通行判定只走 `world.is_passable`，禁止直接调 `gen.is_passable`（M2 单点接入）。
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from app import constants as C

DIR_UP = (0, 1)
DIR_RIGHT = (1, 0)
DIR_DOWN = (0, -1)
DIR_LEFT = (-1, 0)
DIRECTIONS = (DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT)  # 上 → 右 → 下 → 左
_OPPOSITE = {DIR_UP: DIR_DOWN, DIR_DOWN: DIR_UP, DIR_LEFT: DIR_RIGHT, DIR_RIGHT: DIR_LEFT}


@dataclass(frozen=True)
class StepResult:
    """一个逻辑 Tick 的结果。"""

    died: bool
    ate: bool
    head: tuple[int, int]
    length: int


class Snake:
    """蛇身状态机。只被 Game 驱动，不感知渲染与时间。"""

    def __init__(self, cells: list[tuple[int, int]], direction: tuple[int, int]) -> None:
        if not cells:
            raise ValueError("snake needs at least one cell")
        self.body: deque[tuple[int, int]] = deque(cells)
        self.occupied: set[tuple[int, int]] = set(cells)
        self.direction = direction
        self.pending = direction
        self.ate_food = False
        # 上一 Tick 的尾巴位置：R4 插值用（没吃食物时尾巴从 prev_tail 滑到 body[-1]）
        self.prev_tail: tuple[int, int] = self.body[-1]

    # ---------- 构造 ----------
    @classmethod
    def spawn(cls) -> "Snake":
        """出生：头 (0,0)、方向 (1,0)、长度 3（D-006）。"""
        hx, hy = C.SPAWN_CELL
        dx, dy = C.SPAWN_DIR
        cells = [(hx - dx * i, hy - dy * i) for i in range(C.SPAWN_LEN)]
        return cls(cells, C.SPAWN_DIR)

    # ---------- 查询 ----------
    @property
    def head(self) -> tuple[int, int]:
        return self.body[0]

    @property
    def tail(self) -> tuple[int, int]:
        return self.body[-1]

    def __len__(self) -> int:
        return len(self.body)

    def __contains__(self, cell: tuple[int, int]) -> bool:
        return cell in self.occupied

    # ---------- 输入 ----------
    def set_direction(self, direction: tuple[int, int]) -> bool:
        """设定下一 Tick 的方向。返回是否被接受。

        反向判定比较的是 **pending** 而不是已提交的 direction：
        否则同一 Tick 内"先上再左"会被误判为相对已提交方向的反向而丢弃。
        """
        if direction not in DIRECTIONS:
            return False
        # 长度 1 时允许掉头；否则禁止 180°
        if len(self.body) > 1 and direction == _OPPOSITE[self.pending]:
            return False
        self.pending = direction
        return True

    # ---------- 步进 ----------
    def step(self, world, ignore_blocked: bool = False) -> StepResult:  # noqa: ANN001
        """推进一格。

        Args:
            world: 提供 `has_food` / `is_passable` / `consume_food`。
            ignore_blocked: 穿墙模式（D-025）→ 忽略地形阻挡，但**自撞仍然死**。
        """
        self.prev_tail = self.body[-1]  # 必须在移动前记录
        self.ate_food = False
        self.direction = self.pending  # 本 Tick 生效（D-019 的同构语义：下一 Tick 才动）

        new_head = (self.head[0] + self.direction[0], self.head[1] + self.direction[1])
        will_eat = world.has_food(new_head)

        # 未吃食物时尾巴会让位，所以可以走进当前尾巴格
        blocking = self.occupied if will_eat else (self.occupied - {self.tail})
        if new_head in blocking:
            return StepResult(True, False, self.head, len(self.body))

        # 唯一通行判定点：蛇身自己查（上面 blocking），地形交给 World
        if not world.is_passable(new_head, ignore_blocked=ignore_blocked):
            return StepResult(True, False, self.head, len(self.body))

        if will_eat:
            self.body.appendleft(new_head)
            self.occupied.add(new_head)
            self.ate_food = True
            world.consume_food(new_head, occupied=frozenset(self.occupied))
        else:
            # 先摘尾巴再登记头：若 new_head 正好是旧尾巴格（紧跟蛇尾走），
            # 直接 discard 会把刚加进来的头从 occupied 里删掉。
            old_tail = self.body.pop()
            if old_tail != new_head:
                self.occupied.discard(old_tail)
            self.body.appendleft(new_head)
            self.occupied.add(new_head)

        return StepResult(False, self.ate_food, new_head, len(self.body))
