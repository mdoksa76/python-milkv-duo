"""
PyWordApp — glavni urwid loop, event dispatch, meni, dijalozi.
"""

import os
import urwid

from config import PALETTE, KEY_SAVE, KEY_OPEN, KEY_NEW, KEY_QUIT
from core import open_file, save
from core.doc import Document
from ui.editor    import EditorPane
from ui.statusbar import StatusBar
from ui.findbar   import FindBar
from ui.dialogs   import InputDialog, ConfirmDialog, overlay
from ui.filepicker import FilePicker


FILE_MENU = [
    ("New",     "ctrl n", "action_new"),
    ("Open",    "ctrl o", "action_open"),
    ("Save",    "ctrl s", "action_save"),
    ("Save As", None,     "action_save_as"),
    None,
    ("Exit",    "ctrl q", "action_exit"),
]

EDIT_MENU = [
    ("Undo",  None, "action_undo"),
    ("Redo",  None, "action_redo"),
    None,
    ("Find",  None, "action_find"),
]


class PyWordApp:
    def __init__(self, filepath: str = None):
        self._doc        = Document.new()
        self._overlay    = None
        self._find_open  = False
        self._last_query = ""

        self._status  = StatusBar()
        self._editor  = EditorPane(on_cursor_move=self._on_cursor_move)
        self._findbar = FindBar(on_find=self._do_find, on_close=self._close_find)

        self._header = urwid.AttrMap(
            urwid.Text(" [F2] File   [F3] Edit ", align="left"),
            "menubar"
        )

        self._frame = urwid.Frame(
            body=self._editor,
            header=self._header,
            footer=self._status.as_widget(),
        )

        self._loop = urwid.MainLoop(
            self._frame,
            palette=PALETTE,
            unhandled_input=self._unhandled_input,
        )

        if filepath:
            self._load_file(filepath)
        else:
            self._editor.load_document(self._doc, dirty_callback=self._mark_dirty)
            self._refresh_status()

    def run(self):
        self._loop.run()

    # ------------------------------------------------------------------ #
    #  Input
    # ------------------------------------------------------------------ #

    def _unhandled_input(self, key):
        if key == "f2":
            self._open_popup("File", FILE_MENU)
        elif key == "f3":
            self._open_popup("Edit", EDIT_MENU)
        elif key == KEY_NEW:
            self.action_new()
        elif key == KEY_OPEN:
            self.action_open()
        elif key == KEY_SAVE:
            self.action_save()
        elif key == KEY_QUIT:
            self.action_exit()
        elif key == "esc" and self._find_open:
            self._close_find()

    # ------------------------------------------------------------------ #
    #  Popup meni
    # ------------------------------------------------------------------ #

    def _open_popup(self, title: str, entries: list):
        items = []
        for entry in entries:
            if entry is None:
                items.append(urwid.AttrMap(urwid.Divider("─"), "menu_item"))
                continue
            label, shortcut, action_name = entry
            sc   = f"  {shortcut}" if shortcut else ""
            text = f"  {label:<12}{sc}"
            icon = urwid.SelectableIcon(text, cursor_position=0)
            wrapped = _MenuEntry(icon, lambda a=action_name: self._menu_select(a))
            items.append(urwid.AttrMap(wrapped, "menu_item", "menu_focus"))

        height = len(items) + 2
        left   = 1 if title == "File" else 17

        menu_box = urwid.LineBox(
            urwid.ListBox(urwid.SimpleFocusListWalker(items)),
            title=title
        )
        self._overlay = urwid.Overlay(
            menu_box,
            self._frame,
            align="left",  width=30,
            valign="top",  height=height,
            left=left, top=1,
        )
        self._loop.widget = self._overlay

    def _close_menu(self):
        self._overlay = None
        self._loop.widget = self._frame

    def _menu_select(self, action_name: str):
        self._close_menu()
        getattr(self, action_name)()

    # ------------------------------------------------------------------ #
    #  File akcije
    # ------------------------------------------------------------------ #

    def action_new(self):
        if self._doc.dirty:
            self._confirm_discard(self._do_new)
        else:
            self._do_new()

    def _do_new(self):
        self._doc = Document.new()
        self._editor.load_document(self._doc, dirty_callback=self._mark_dirty)
        self._refresh_status()

    def action_open(self):
        start = os.path.dirname(self._doc.filepath or os.path.expanduser("~"))
        picker = FilePicker(start_dir=start)
        urwid.connect_signal(picker, "pick",   self._do_open_pick)
        urwid.connect_signal(picker, "cancel", self._close_dialog)
        self._overlay = urwid.Overlay(
            picker,
            self._frame,
            align="center", width=("relative", 80),
            valign="middle", height=("relative", 80),
        )
        self._loop.widget = self._overlay

    def _do_open_pick(self, path: str):
        self._close_dialog()
        if not path or not os.path.isfile(path):
            return
        try:
            self._doc = open_file(path)
            self._editor.load_document(self._doc, dirty_callback=self._mark_dirty)
            self._refresh_status()
        except Exception as e:
            self._status.update(error=str(e))

    def _load_file(self, path: str):
        try:
            self._doc = open_file(path)
            self._editor.load_document(self._doc, dirty_callback=self._mark_dirty)
            self._refresh_status()
        except Exception as e:
            self._editor.load_document(self._doc, dirty_callback=self._mark_dirty)
            self._status.update(error=str(e))

    def action_save(self):
        if not self._doc.filepath:
            self.action_save_as()
            return
        try:
            save(self._doc)
            self._refresh_status()
        except Exception as e:
            self._status.update(error=str(e))

    def action_save_as(self):
        default = self._doc.filepath or ""
        dlg = InputDialog(
            title="Spremi kao",
            prompt="Unesite putanju (.pyword ili .txt):",
            default=default,
            on_ok=self._do_save_as,
            on_cancel=self._close_dialog,
        )
        self._show_dialog(dlg, height=10)

    def _do_save_as(self, path: str):
        self._close_dialog()
        if not path:
            return
        try:
            save(self._doc, path)
            self._refresh_status()
        except Exception as e:
            self._status.update(error=str(e))

    def action_exit(self):
        if self._doc.dirty:
            self._confirm_discard(self._do_exit)
        else:
            self._do_exit()

    def _do_exit(self):
        raise urwid.ExitMainLoop()

    # ------------------------------------------------------------------ #
    #  Edit akcije
    # ------------------------------------------------------------------ #

    def action_undo(self):
        self._editor.undo()

    def action_redo(self):
        self._editor.redo()

    def action_find(self):
        self._open_find()

    # ------------------------------------------------------------------ #
    #  Find
    # ------------------------------------------------------------------ #

    def _open_find(self):
        self._find_open = True
        self._findbar.reset(self._last_query)
        body = urwid.Pile([
            ("weight", 1, self._editor),
            ("pack",      self._findbar),
        ])
        self._frame.body = body
        self._frame.body.focus_position = 1

    def _close_find(self):
        self._find_open = False
        self._frame.body = self._editor
        self._frame.focus_position = "body"

    def _do_find(self, query: str):
        if not query:
            return
        self._last_query = query
        found = self._editor.find_next(query)
        if not found:
            self._close_find()
            self._status.update(
                filepath=self._doc.filepath,
                line=1, col=1,
                dirty=self._doc.dirty,
                words=self._editor.word_count(),
                error=f'Nije pronađeno: "{query}"',
            )

    # ------------------------------------------------------------------ #
    #  Dijalozi
    # ------------------------------------------------------------------ #

    def _show_dialog(self, dlg, height=10):
        self._overlay = overlay(dlg, self._frame, width=60, height=height)
        self._loop.widget = self._overlay

    def _close_dialog(self):
        self._overlay = None
        self._loop.widget = self._frame

    def _confirm_discard(self, on_yes):
        dlg = ConfirmDialog(
            title="Nespremljene promjene",
            message="Dokument ima nespremljene promjene.\nNastaviti bez snimanja?",
            on_yes=lambda: (self._close_dialog(), on_yes()),
            on_no=self._close_dialog,
        )
        self._show_dialog(dlg, height=9)

    # ------------------------------------------------------------------ #
    #  Status
    # ------------------------------------------------------------------ #

    def _mark_dirty(self):
        self._doc.dirty = True
        ln, col = self._editor.get_cursor_line_col()
        self._status.update(
            filepath=self._doc.filepath,
            line=ln, col=col, dirty=True,
            words=self._editor.word_count(),
        )

    def _on_cursor_move(self, ln, col, words):
        self._status.update(
            filepath=self._doc.filepath,
            line=ln, col=col,
            dirty=self._doc.dirty,
            words=words,
        )

    def _refresh_status(self):
        ln, col = self._editor.get_cursor_line_col()
        self._status.update(
            filepath=self._doc.filepath,
            line=ln, col=col,
            dirty=self._doc.dirty,
            words=self._editor.word_count(),
        )


class _MenuEntry(urwid.WidgetWrap):
    def __init__(self, icon, on_select):
        self._on_select = on_select
        super().__init__(icon)

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key in ("enter", " "):
            self._on_select()
            return None
        return self._w.keypress(size, key)
