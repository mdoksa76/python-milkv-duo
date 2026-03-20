# pyplot/ui/parametric_list.py

import urwid
from pyplot.core.state import state, ParametricEntry

class ParametricList:
    """
    Scrollable list of parametric curves with checkboxes.
    """
    def __init__(self):
        self.walker = urwid.SimpleFocusListWalker([])
        self.listbox = urwid.ListBox(self.walker)

    def add_curve(self, xt_expr, yt_expr, xt_sympy, yt_sympy, marker):
        entry = ParametricEntry(
            xt_expr=xt_expr,
            yt_expr=yt_expr,
            xt_sympy=xt_sympy,
            yt_sympy=yt_sympy,
            marker=marker,
            checked=True
        )
        state.parametric.append(entry)

        label = f"x={xt_expr}, y={yt_expr}  [{marker}]"
        checkbox = urwid.CheckBox(
            label,
            state=entry.checked,
            on_state_change=self._on_checkbox_change,
            user_data=entry
        )
        self.walker.append(checkbox)

    def _on_checkbox_change(self, checkbox, new_state, entry):
        entry.checked = new_state

    def clear(self):
        state.parametric.clear()
        self.walker[:] = []

    def get_widget(self):
        return self.listbox
