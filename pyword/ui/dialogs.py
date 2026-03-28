"""
Dijalozi:
  InputDialog   — jedan input field (Open, Save As)
  ConfirmDialog — da/ne pitanje (Exit bez save, itd.)
"""

import urwid


class InputDialog(urwid.WidgetWrap):
    """
    Modalni dijalog s jednim input fieldom.

    on_ok(value)    — poziva se s unesenim tekstom
    on_cancel()     — poziva se na Esc ili Cancel
    """
    def __init__(self, title: str, prompt: str,
                 default: str = "",
                 on_ok=None, on_cancel=None):
        self._on_ok     = on_ok     or (lambda v: None)
        self._on_cancel = on_cancel or (lambda: None)

        self._edit = urwid.Edit(caption="", edit_text=default)
        edit_w = urwid.AttrMap(self._edit, "input", "input_focus")

        ok_btn     = urwid.Button("  OK  ")
        cancel_btn = urwid.Button("Odustani")
        urwid.connect_signal(ok_btn,     "click", lambda _: self._ok())
        urwid.connect_signal(cancel_btn, "click", lambda _: self._cancel())

        buttons = urwid.GridFlow(
            [urwid.AttrMap(ok_btn,     "menu_item", "menu_focus"),
             urwid.AttrMap(cancel_btn, "menu_item", "menu_focus")],
            cell_width=12, h_sep=2, v_sep=0, align="center"
        )

        body = urwid.Pile([
            urwid.Text(prompt),
            urwid.Divider(),
            edit_w,
            urwid.Divider(),
            buttons,
        ])

        frame = urwid.LineBox(
            urwid.Padding(body, left=1, right=1),
            title=title
        )
        super().__init__(urwid.AttrMap(frame, "dialog"))

    def _ok(self):
        self._on_ok(self._edit.edit_text.strip())

    def _cancel(self):
        self._on_cancel()

    def keypress(self, size, key):
        if key == "esc":
            self._cancel()
            return None
        if key == "enter":
            self._ok()
            return None
        return super().keypress(size, key)


class ConfirmDialog(urwid.WidgetWrap):
    """
    Modalni dijalog s da/ne pitanjem.
    on_yes() / on_no()
    """
    def __init__(self, title: str, message: str,
                 on_yes=None, on_no=None):
        self._on_yes = on_yes or (lambda: None)
        self._on_no  = on_no  or (lambda: None)

        yes_btn = urwid.Button("  Da  ")
        no_btn  = urwid.Button("  Ne  ")
        urwid.connect_signal(yes_btn, "click", lambda _: self._on_yes())
        urwid.connect_signal(no_btn,  "click", lambda _: self._on_no())

        buttons = urwid.GridFlow(
            [urwid.AttrMap(yes_btn, "menu_item", "menu_focus"),
             urwid.AttrMap(no_btn,  "menu_item", "menu_focus")],
            cell_width=10, h_sep=2, v_sep=0, align="center"
        )

        body = urwid.Pile([
            urwid.Text(message, align="center"),
            urwid.Divider(),
            buttons,
        ])

        frame = urwid.LineBox(
            urwid.Padding(body, left=1, right=1),
            title=title
        )
        super().__init__(urwid.AttrMap(frame, "dialog"))

    def keypress(self, size, key):
        if key == "esc":
            self._on_no()
            return None
        return super().keypress(size, key)


def overlay(dialog, base_widget, width=60, height=12):
    """Omotava dijalog u urwid.Overlay na sredini ekrana."""
    return urwid.Overlay(
        dialog,
        base_widget,
        align="center",   width=("relative", min(width, 90)),
        valign="middle",  height=height,
    )
