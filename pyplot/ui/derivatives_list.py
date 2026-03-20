# pyplot/ui/derivatives_list.py

import urwid
from pyplot.core.state import state, FunctionEntry

class DerivativesList:
    """
    Scrollable list of original function + its derivatives.
    """
    def __init__(self):
        self.walker = urwid.SimpleFocusListWalker([])
        self.listbox = urwid.ListBox(self.walker)

    def add_entry(self, label, sympy_expr, marker, order=0):
        """
        Dodaj originalnu funkciju (order=0) ili derivaciju (order>0).
        """
        entry = FunctionEntry(expr=label, sympy_expr=sympy_expr, marker=marker, checked=True)
        state.derivatives.append(entry)

        if order == 0:
            prefix = "f:  "
        elif order == 1:
            prefix = "f': "
        elif order == 2:
            prefix = "f'':"
        else:
            prefix = f"f{order}:"

        checkbox = urwid.CheckBox(
            f"{prefix} {label}  [{marker}]",
            state=entry.checked,
            on_state_change=self._on_checkbox_change,
            user_data=entry
        )
        self.walker.append(checkbox)

    def _on_checkbox_change(self, checkbox, new_state, entry):
        entry.checked = new_state

    def clear(self):
        state.derivatives.clear()
        self.walker[:] = []

    def get_widget(self):
        return self.listbox
