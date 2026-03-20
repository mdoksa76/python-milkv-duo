# pyplot/ui/function_list.py

import urwid
from pyplot.core.state import state, FunctionEntry

class FunctionList:
    """
    Scrollable list of functions with checkboxes and Del buttons.
    """
    def __init__(self):
        self.walker = urwid.SimpleFocusListWalker([])
        self.listbox = urwid.ListBox(self.walker)
        self.entry_map = {}  # id(row) -> entry

    def add_function(self, expr, sympy_expr, marker):
        entry = FunctionEntry(expr=expr, sympy_expr=sympy_expr, marker=marker, checked=True)
        state.functions.append(entry)
        row = self._build_row(entry)
        self.entry_map[id(row)] = entry
        self.walker.append(row)

    def _build_row(self, entry):
        checkbox = urwid.CheckBox(
            f"{entry.expr}  [{entry.marker}]",
            state=entry.checked,
            on_state_change=self._on_checkbox_change,
            user_data=entry
        )
        del_btn = urwid.Button("Del")
        row = urwid.Columns([
            checkbox,
            ('fixed', 7, del_btn),
        ])
        urwid.connect_signal(del_btn, 'click', self._on_delete, row)
        return row

    def _on_checkbox_change(self, checkbox, new_state, entry):
        entry.checked = new_state

    def _on_delete(self, button, row):
        entry = self.entry_map.get(id(row))
        if entry and entry in state.functions:
            state.functions.remove(entry)
        for i, w in enumerate(self.walker):
            if w is row:
                del self.walker[i]
                break
        self.entry_map.pop(id(row), None)

    def get_widget(self):
        return self.listbox
