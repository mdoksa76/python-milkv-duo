"""
EditorPane — srce editora.
"""

import urwid
from core.doc import Document, Paragraph
from core.history import History


def _attr_for(text: str) -> str:
    if text.startswith("### "):
        return "heading3"
    if text.startswith("## "):
        return "heading2"
    if text.startswith("# "):
        return "heading1"
    if text.startswith("  - "):
        return "list_item"
    return "normal"


def _count_words(walker) -> int:
    total = 0
    for w in walker:
        total += len(w.text.split())
    return total


class ParagraphEdit(urwid.WidgetWrap):
    def __init__(self, text: str, on_change=None, on_enter=None,
                 on_backspace_at_start=None, on_snapshot=None):
        self._on_change             = on_change             or (lambda w, t: None)
        self._on_enter              = on_enter              or (lambda w: None)
        self._on_backspace_at_start = on_backspace_at_start or (lambda w: None)
        self._on_snapshot           = on_snapshot           or (lambda: None)

        self._edit = urwid.Edit(edit_text=text, multiline=False)
        urwid.connect_signal(self._edit, "postchange", self._changed)

        self._attr = urwid.AttrMap(self._edit, _attr_for(text))
        super().__init__(self._attr)

    def _changed(self, widget, old_text):
        new_attr = _attr_for(self._edit.edit_text)
        self._attr.set_attr_map({None: new_attr})
        self._on_change(self, self._edit.edit_text)

    @property
    def text(self):
        return self._edit.edit_text

    @text.setter
    def text(self, value):
        self._edit.set_edit_text(value)
        self._edit.set_edit_pos(len(value))

    @property
    def cursor_col(self):
        return self._edit.edit_pos

    def set_cursor_pos(self, pos):
        self._edit.set_edit_pos(pos)

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key == "enter":
            self._on_enter(self)
            return None
        if key == "backspace" and self._edit.edit_pos == 0:
            self._on_backspace_at_start(self)
            return None
        if key == " ":
            self._on_snapshot()
        return self._attr.keypress(size, key)


class EditorPane(urwid.WidgetWrap):
    _sizing = frozenset([urwid.BOX])

    def __init__(self, on_cursor_move=None):
        self._on_cursor_move = on_cursor_move or (lambda ln, col, words: None)
        self._walker   = urwid.SimpleFocusListWalker([])
        self._listbox  = urwid.ListBox(self._walker)
        self._dirty_cb = None
        self._history  = History()
        self._doc      = None
        super().__init__(self._listbox)

    def load_document(self, doc: Document, dirty_callback=None):
        self._doc      = doc
        self._dirty_cb = dirty_callback
        self._history.clear()
        widgets = [self._make_widget(p.text) for p in doc.paragraphs]
        self._walker[:] = widgets
        if widgets:
            self._listbox.set_focus(0)
        self._notify_cursor()

    def _make_widget(self, text: str) -> ParagraphEdit:
        return ParagraphEdit(
            text,
            on_change=self._on_change,
            on_enter=self._on_enter,
            on_backspace_at_start=self._on_backspace_at_start,
            on_snapshot=self._snapshot,
        )

    def _on_change(self, widget, text):
        self._sync_doc()
        if self._dirty_cb:
            self._dirty_cb()

    def _on_enter(self, widget):
        self._snapshot()
        idx  = self._widget_index(widget)
        pos  = widget.cursor_col
        text = widget.text
        widget.text = text[:pos]
        new_w = self._make_widget(text[pos:])
        self._walker.insert(idx + 1, new_w)
        self._listbox.set_focus(idx + 1)
        new_w.set_cursor_pos(0)
        self._sync_doc()
        if self._dirty_cb:
            self._dirty_cb()
        self._notify_cursor()

    def _on_backspace_at_start(self, widget):
        idx = self._widget_index(widget)
        if idx == 0:
            return
        self._snapshot()
        prev_w   = self._walker[idx - 1]
        join_pos = len(prev_w.text)
        prev_w.text = prev_w.text + widget.text
        del self._walker[idx]
        self._listbox.set_focus(idx - 1)
        prev_w.set_cursor_pos(join_pos)
        self._sync_doc()
        if self._dirty_cb:
            self._dirty_cb()
        self._notify_cursor()

    # ------------------------------------------------------------------ #
    #  Undo / Redo
    # ------------------------------------------------------------------ #

    def _snapshot(self):
        _, focus_pos = self._walker.get_focus()
        self._history.push([w.text for w in self._walker], focus_pos or 0)

    def undo(self):
        _, focus_pos = self._walker.get_focus()
        snap = self._history.undo([w.text for w in self._walker], focus_pos or 0)
        if snap:
            self._restore(snap)

    def redo(self):
        _, focus_pos = self._walker.get_focus()
        snap = self._history.redo([w.text for w in self._walker], focus_pos or 0)
        if snap:
            self._restore(snap)

    def _restore(self, snap):
        widgets = [self._make_widget(t) for t in snap.texts]
        self._walker[:] = widgets
        focus = min(snap.focus_idx, len(widgets) - 1)
        self._listbox.set_focus(focus)
        self._sync_doc()
        if self._dirty_cb:
            self._dirty_cb()
        self._notify_cursor()

    def can_undo(self):
        return self._history.can_undo()

    def can_redo(self):
        return self._history.can_redo()

    # ------------------------------------------------------------------ #
    #  Find
    # ------------------------------------------------------------------ #

    def find_next(self, query: str) -> bool:
        if not query:
            return False
        query_lower = query.lower()
        _, focus_pos = self._walker.get_focus()
        focus_pos = focus_pos or 0
        total = len(self._walker)

        for offset in range(total):
            idx  = (focus_pos + offset) % total
            text = self._walker[idx].text.lower()
            # u trenutnom paragrafu traži od kursora nadalje
            start = self._walker[idx].cursor_col if offset == 0 else 0
            col   = text.find(query_lower, start)
            if col != -1:
                self._listbox.set_focus(idx)
                self._walker[idx].set_cursor_pos(col)
                self._notify_cursor()
                return True
        return False

    # ------------------------------------------------------------------ #
    #  Word count
    # ------------------------------------------------------------------ #

    def word_count(self) -> int:
        return _count_words(self._walker)

    # ------------------------------------------------------------------ #
    #  Sync / helpers
    # ------------------------------------------------------------------ #

    def _sync_doc(self):
        if self._doc:
            self._doc.set_paragraphs([w.text for w in self._walker])
            self._doc.dirty = True

    def _widget_index(self, widget) -> int:
        for i, w in enumerate(self._walker):
            if w is widget:
                return i
        return 0

    def _notify_cursor(self):
        focus_w, focus_pos = self._walker.get_focus()
        if focus_w is None:
            return
        self._on_cursor_move(
            (focus_pos or 0) + 1,
            focus_w.cursor_col + 1,
            _count_words(self._walker),
        )

    def keypress(self, size, key):
        result = super().keypress(size, key)
        self._notify_cursor()
        return result

    def get_cursor_line_col(self):
        w, pos = self._walker.get_focus()
        return (pos or 0) + 1, (w.cursor_col + 1 if w else 1)

    def focus_first(self):
        if self._walker:
            self._listbox.set_focus(0)
