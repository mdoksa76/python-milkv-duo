"""MenuBar — vrh ekrana s File menijem."""

import urwid


MENU_ITEMS = [
    ("New",     "ctrl n"),
    ("Open",    "ctrl o"),
    ("Save",    "ctrl s"),
    ("Save As", None),
    (None,      None),   # separator
    ("Exit",    "ctrl q"),
]


class MenuItem(urwid.WidgetWrap):
    def __init__(self, label, shortcut, on_select):
        self._on_select = on_select
        if label is None:
            w = urwid.AttrMap(urwid.Divider("─"), "menu_item")
        else:
            sc = f"  {shortcut}" if shortcut else ""
            text = f"  {label:<12}{sc}"
            w = urwid.AttrMap(
                urwid.SelectableIcon(text, cursor_position=0),
                "menu_item", "menu_focus"
            )
        super().__init__(w)

    def selectable(self):
        return self._on_select is not None

    def keypress(self, size, key):
        if key in ("enter", " ") and self._on_select:
            self._on_select()
            return None
        return key


class MenuBar(urwid.WidgetWrap):
    def __init__(self, callbacks: dict):
        """
        callbacks: {"new": fn, "open": fn, "save": fn,
                    "save_as": fn, "exit": fn}
        """
        self._callbacks = callbacks
        self._menu_open = False
        self._menu_overlay = None

        label = urwid.Text(" File  ")
        self._bar = urwid.AttrMap(
            urwid.Columns([
                ("pack", urwid.SelectableIcon(" File ", cursor_position=0)),
                urwid.Text(""),
            ]),
            "menubar"
        )
        super().__init__(self._bar)

    # ------------------------------------------------------------------ #
    def selectable(self):
        return True

    def keypress(self, size, key):
        if key in ("enter", " ", "f10"):
            return "open_menu"
        return key
