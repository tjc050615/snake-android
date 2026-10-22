"""二次确认（M4/R3）：退出/重开前弹确认，确认期间游戏被冻结。"""

from __future__ import annotations


class ConfirmState:
    def __init__(self) -> None:
        self.pending_action: str | None = None

    def ask(self, action: str) -> None:
        self.pending_action = action

    @property
    def active(self) -> bool:
        return self.pending_action is not None

    def blocks_gameplay(self) -> bool:
        return self.active

    def confirm(self) -> str | None:
        action = self.pending_action
        self.pending_action = None
        return action

    def cancel(self) -> None:
        self.pending_action = None
