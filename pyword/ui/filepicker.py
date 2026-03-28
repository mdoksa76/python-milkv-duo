"""
FilePicker — TUI file browser za pyword.
Prilagođen iz pymail._FilePicker.

Signals:
  pick(path)  — korisnik odabrao datoteku
  cancel      — korisnik odustao

Prikazuje samo podržane ekstenzije + direktorije.
Navigacija: strelice, Enter = otvori dir / odaberi file, Esc/Backspace = gore.
"""

import os
import urwid
from core import SUPPORTED_EXTS


class _SafeListBox(urwid.ListBox):
    def keypress(self, size, key):
        try:
            return super().keypress(size, key)
        except Exception:
            return key


class _Item(urwid.WidgetWrap):
    def __init__(self, name, is_dir):
        self.name   = name
        self.is_dir = is_dir
        icon = "[/] " if is_dir else "    "
        attr = "heading2" if is_dir else "normal"
        text = urwid.Text((attr, f" {icon}{name}"), wrap="clip")
        self._w = urwid.AttrMap(text, attr, focus_map="menu_focus")

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class FilePicker(urwid.WidgetWrap):
    signals = ["pick", "cancel"]

    def __init__(self, start_dir=None):
        self.cwd = os.path.abspath(start_dir or os.path.expanduser("~"))
        self.selected_path = None

        self._walker   = urwid.SimpleFocusListWalker([])
        self._listbox  = _SafeListBox(self._walker)
        self._path_txt = urwid.Text(("menubar", ""), wrap="clip")
        self._info_txt = urwid.Text(("statusbar", ""), wrap="clip")

        self._refresh()

        hint = urwid.AttrMap(urwid.Text(
            " Enter:otvori/odaberi   Backspace/Esc:gore   Esc na root:odustani"
        ), "statusbar")

        pile = urwid.Pile([
            ("pack", urwid.AttrMap(self._path_txt, "menubar")),
            ("pack", urwid.Divider("─")),
            ("weight", 1, self._listbox),
            ("pack", urwid.Divider("─")),
            ("pack", urwid.AttrMap(self._info_txt, "statusbar")),
            ("pack", hint),
        ])

        box = urwid.LineBox(pile, title="Otvori datoteku", title_align="left")
        super().__init__(box)

    def _refresh(self):
        self._path_txt.set_text(("menubar", f" {self.cwd}"))
        self._walker.clear()

        try:
            entries = sorted(os.listdir(self.cwd), key=lambda e: e.lower())
        except PermissionError:
            self._walker.append(urwid.Text(("statusbar_err", " Nema pristupa")))
            return

        # .. uvijek na vrhu
        parent = os.path.dirname(self.cwd)
        if parent != self.cwd:
            self._walker.append(_Item("..", is_dir=True))

        dirs  = [e for e in entries if os.path.isdir(os.path.join(self.cwd, e))]
        files = [e for e in entries
                 if os.path.isfile(os.path.join(self.cwd, e))
                 and os.path.splitext(e)[1].lower() in SUPPORTED_EXTS]

        for d in dirs:
            self._walker.append(_Item(d, is_dir=True))
        for f in files:
            self._walker.append(_Item(f, is_dir=False))

        if not self._walker:
            self._walker.append(urwid.Text(("normal", "  (nema podržanih datoteka)")))

        count = len(files)
        self._info_txt.set_text(("statusbar", f"  {count} datoteka  |  {len(dirs)} mapa"))

        if self._walker:
            self._walker.set_focus(0)

    def _go_up(self):
        parent = os.path.dirname(self.cwd)
        if parent != self.cwd:
            self.cwd = parent
            self._refresh()
            return True
        return False  # već na root

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key == "backspace":
            self._go_up()
            return None

        if key == "esc":
            if not self._go_up():
                urwid.emit_signal(self, "cancel")
            return None

        if key == "enter":
            try:
                widget, _ = self._walker.get_focus()
                if not hasattr(widget, "name"):
                    return None
                if widget.name == "..":
                    self._go_up()
                    return None
                path = os.path.join(self.cwd, widget.name)
                if widget.is_dir:
                    self.cwd = path
                    self._refresh()
                else:
                    self.selected_path = path
                    urwid.emit_signal(self, "pick", path)
            except Exception:
                pass
            return None

        return super().keypress(size, key)
