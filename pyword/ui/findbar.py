"""
FindBar — traka za pretraživanje na dnu ekrana (ispod editora).
Ponaša se kao nano search: upiši, Enter = sljedeće, Esc = zatvori.
"""

import urwid


class FindBar(urwid.WidgetWrap):
    """
    Prikazuje se između editora i statusbara kad je aktivan.
    on_find(query)  — poziva se na Enter
    on_close()      — poziva se na Esc
    """

    def __init__(self, on_find=None, on_close=None):
        self._on_find  = on_find  or (lambda q: None)
        self._on_close = on_close or (lambda: None)

        self._edit = urwid.Edit(caption=" Find: ")
        bar = urwid.AttrMap(self._edit, "input_focus")
        super().__init__(bar)

    def reset(self, query=""):
        self._edit.set_edit_text(query)
        self._edit.set_edit_pos(len(query))

    def get_query(self):
        return self._edit.edit_text

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key == "esc":
            self._on_close()
            return None
        if key == "enter":
            self._on_find(self._edit.edit_text)
            return None
        return self._w.keypress(size, key)
