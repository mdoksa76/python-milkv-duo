"""
History — undo/redo stack za pyword.

Snapshot = lista tekstova paragrafa + indeks fokusiranog paragrafa.
Čuva maksimalno MAX_HISTORY snapshotova da ne pojede RAM.
"""

from typing import Optional

MAX_HISTORY = 50


class Snapshot:
    __slots__ = ("texts", "focus_idx")

    def __init__(self, texts: list, focus_idx: int = 0):
        self.texts     = list(texts)
        self.focus_idx = focus_idx


class History:
    def __init__(self):
        self._undo_stack: list[Snapshot] = []
        self._redo_stack: list[Snapshot] = []

    def push(self, texts: list, focus_idx: int = 0):
        """Spremi snapshot trenutnog stanja. Briše redo stack."""
        self._undo_stack.append(Snapshot(texts, focus_idx))
        if len(self._undo_stack) > MAX_HISTORY:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self, current_texts: list, current_focus: int) -> Optional[Snapshot]:
        """
        Vrati prethodni snapshot.
        Trenutno stanje sprema na redo stack.
        """
        if not self._undo_stack:
            return None
        self._redo_stack.append(Snapshot(current_texts, current_focus))
        return self._undo_stack.pop()

    def redo(self, current_texts: list, current_focus: int) -> Optional[Snapshot]:
        """
        Ponovi zadnji undo.
        Trenutno stanje sprema na undo stack.
        """
        if not self._redo_stack:
            return None
        self._undo_stack.append(Snapshot(current_texts, current_focus))
        return self._redo_stack.pop()

    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def clear(self):
        self._undo_stack.clear()
        self._redo_stack.clear()
