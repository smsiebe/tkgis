"""Undo/redo history for the workflow builder."""
from __future__ import annotations

import copy
from typing import Any


class WorkflowHistory:
    """Stack-based undo/redo for workflow graph snapshots.

    Each snapshot is a serializable dict representing the full graph state.
    """

    def __init__(self, max_history: int = 100) -> None:
        self._max_history = max_history
        self._undo_stack: list[dict[str, Any]] = []
        self._redo_stack: list[dict[str, Any]] = []

    def push(self, state: dict[str, Any]) -> None:
        """Record a snapshot before a mutation.

        Clears the redo stack since a new branch of history starts.
        """
        self._undo_stack.append(copy.deepcopy(state))
        if len(self._undo_stack) > self._max_history:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self) -> dict[str, Any] | None:
        """Pop the most recent snapshot and move it to the redo stack.

        Returns the previous state dict, or ``None`` if nothing to undo.
        """
        if not self._undo_stack:
            return None
        state = self._undo_stack.pop()
        self._redo_stack.append(copy.deepcopy(state))
        return state

    def redo(self) -> dict[str, Any] | None:
        """Pop the most recent redo snapshot and move it back to undo.

        Returns the restored state dict, or ``None`` if nothing to redo.
        """
        if not self._redo_stack:
            return None
        state = self._redo_stack.pop()
        self._undo_stack.append(copy.deepcopy(state))
        return state

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def clear(self) -> None:
        """Reset both stacks."""
        self._undo_stack.clear()
        self._redo_stack.clear()
