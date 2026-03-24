#!/usr/bin/env python3

import os
import time
import urwid

# -----------------------------
# Panel widget
# -----------------------------
class Panel:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.widget = None
        self.sort_by = 'name'
        self.refresh()

    def list_dir(self):
        try:
            entries = os.listdir(self.path)
            if self.sort_by == 'size':
                # Direktoriji na vrhu abecedno, datoteke silazno po veličini
                dirs  = sorted([x for x in entries if os.path.isdir(os.path.join(self.path, x))])
                files = sorted([x for x in entries if not os.path.isdir(os.path.join(self.path, x))],
                               key=lambda x: os.path.getsize(os.path.join(self.path, x)),
                               reverse=True)
                entries = dirs + files
            elif self.sort_by == 'date':
                # Sve zajedno, najnovije prvo
                entries.sort(key=lambda x: os.path.getmtime(os.path.join(self.path, x)),
                             reverse=True)
            else:
                # name: direktoriji prvo, abecedno
                dirs  = sorted([x for x in entries if os.path.isdir(os.path.join(self.path, x))])
                files = sorted([x for x in entries if not os.path.isdir(os.path.join(self.path, x))])
                entries = dirs + files
            items = ['.', '..'] + entries
        except PermissionError:
            items = ['.', '..']
        return items

    def format_size(self, size):
        for unit in ('B', 'K', 'M', 'G'):
            if size < 1024:
                return f"{size:.0f}{unit}"
            size /= 1024
        return f"{size:.0f}T"

    def format_date(self, mtime):
        return time.strftime('%Y-%m-%d %H:%M', time.localtime(mtime))

    def refresh(self):
        self._items = self.list_dir()
        widgets = []
        for item in self._items:
            if item in ('.', '..'):
                label = item
            else:
                full = os.path.join(self.path, item)
                try:
                    mtime = os.path.getmtime(full)
                    date  = self.format_date(mtime)
                    if os.path.isdir(full):
                        label = f"[DIR] {item:<34} {date}"
                    else:
                        size  = self.format_size(os.path.getsize(full))
                        label = f"      {item:<30} {size:>6}  {date}"
                except OSError:
                    label = f"      {item}"
            widgets.append(urwid.SelectableIcon(label, 0))
        self.listbox = urwid.ListBox(urwid.SimpleFocusListWalker(widgets))
        self.widget  = urwid.LineBox(self.listbox, title=self.path)

    def enter(self):
        selected = self._items[self.listbox.focus_position]
        if selected == '.':
            return
        if selected == '..':
            new_path = os.path.dirname(self.path)
        else:
            new_path = os.path.join(self.path, selected)
        if os.path.isdir(new_path):
            self.path = new_path
            self.refresh()

    def selected_item(self):
        return self._items[self.listbox.focus_position]

    def selected_path(self):
        return os.path.join(self.path, self.selected_item())

    def sort_label(self):
        return self.sort_by


# -----------------------------
# Main UI
# -----------------------------
class PyMC:
    def __init__(self):
        start = os.getcwd()
        self.left  = Panel(start)
        self.right = Panel(start)
        self.active = 'left'

        self.columns = urwid.Columns([
            ('weight', 1, self.left.widget),
            ('weight', 1, self.right.widget)
        ])

        self.footer = urwid.Text(
            " F3 View  F4 Edit  F5 Copy  F6 Move  F7 Mkdir  F8 Delete  F9 Menu  F10 Exit ",
            align='center'
        )
        self.status  = urwid.Text("", align='left')
        self.cmdline = urwid.Edit(" $ ")
        footer_pile  = urwid.Pile([self.cmdline, self.status, self.footer])

        self.header = urwid.Text("", align='left')
        self.frame  = urwid.Frame(self.columns, header=self.header, footer=footer_pile)

        self.loop = urwid.MainLoop(
            self.frame,
            unhandled_input=self.handle_input,
            input_filter=self.input_filter
        )

        self.update_status()
        self.update_header()

    # ------------------------------------------------------------------
    # Header — aktivni panel u uglatim zagradama + sort mode
    # ------------------------------------------------------------------
    def update_header(self):
        ls = self.left.sort_label()
        rs = self.right.sort_label()
        if self.active == 'left':
            text = f" [LEFT ↑{ls}]   Right ↑{rs} "
        else:
            text = f"  Left ↑{ls}   [RIGHT ↑{rs}] "
        self.header.set_text(text)

    # ------------------------------------------------------------------
    # Input filter
    # ------------------------------------------------------------------
    def input_filter(self, keys, raw):
        result = []
        for key in keys:
            if key == 'tab':
                self.switch_panel()
            elif key == 'f9':
                self.show_menu()
            elif key in ('f10', 'meta x'):
                raise urwid.ExitMainLoop()
            elif key == 'f3':
                self.view_file()
            elif key == 'f4':
                self.edit_file()
            elif key == 'f6':
                self.move_file()
            elif key == 'f7':
                self.mkdir_dialog()
            elif key == 'f8':
                self.delete_dialog()
            else:
                result.append(key)
        return result

    # ------------------------------------------------------------------
    # Panel switching
    # ------------------------------------------------------------------
    def switch_panel(self):
        self.active = 'right' if self.active == 'left' else 'left'
        self.columns.focus_position = 0 if self.active == 'left' else 1
        self.update_status()
        self.update_header()

    def active_panel(self):
        return self.left if self.active == 'left' else self.right

    def other_panel(self):
        return self.right if self.active == 'left' else self.left

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------
    def update_status(self):
        panel = self.active_panel()
        item  = panel.selected_item()
        full  = os.path.join(panel.path, item)
        try:
            st   = os.stat(full)
            size = panel.format_size(st.st_size)
            date = panel.format_date(st.st_mtime)
            info = f" {item}  |  {size}  |  {date}  |  {panel.path}"
        except Exception:
            info = f" {item}  |  {panel.path}"
        self.status.set_text(info)

    # ------------------------------------------------------------------
    # Columns refresh helper
    # ------------------------------------------------------------------
    def refresh_columns(self):
        self.columns.contents = [
            (self.left.widget,  self.columns.options()),
            (self.right.widget, self.columns.options())
        ]
        self.update_status()
        self.update_header()

    # ------------------------------------------------------------------
    # Handle input
    # ------------------------------------------------------------------
    def handle_input(self, key):
        if key == 'enter':
            if self.cmdline.edit_text.strip():
                self.run_command()
                return True
            panel = self.active_panel()
            panel.enter()
            self.refresh_columns()
            return True

        if key == 'f5':
            self.copy_file()
            return True

        self.update_status()
        return False

    # ------------------------------------------------------------------
    # F5 Copy
    # ------------------------------------------------------------------
    def copy_file(self):
        import shutil
        src_panel = self.active_panel()
        dst_panel = self.other_panel()
        item = src_panel.selected_item()
        if item in ('.', '..'):
            return
        src = os.path.join(src_panel.path, item)
        dst = os.path.join(dst_panel.path, item)
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            dst_panel.refresh()
            self.refresh_columns()
            self.status.set_text(f" Copied: {src} → {dst}")
        except Exception as e:
            self.status.set_text(f" ERROR: {e}")

    # ------------------------------------------------------------------
    # F6 Move / Rename dialog
    # ------------------------------------------------------------------
    def move_file(self):
        import shutil
        panel = self.active_panel()
        item  = panel.selected_item()
        if item in ('.', '..'):
            return
        src = os.path.join(panel.path, item)

        edit       = urwid.Edit("Move/Rename to: ",
                                edit_text=os.path.join(self.other_panel().path, item))
        ok_btn     = urwid.Button("OK")
        cancel_btn = urwid.Button("Cancel")

        pile    = urwid.Pile([edit, urwid.Divider(), urwid.Columns([ok_btn, cancel_btn])])
        box     = urwid.LineBox(urwid.Filler(pile), title=f" F6 Move/Rename: {item}")
        overlay = urwid.Overlay(box, self.frame,
                                align='center', width=('relative', 80),
                                valign='middle', height=8)

        def on_ok(btn):
            target = edit.edit_text.strip()
            if not target or target == src:
                self.loop.widget = self.frame
                return
            if os.path.sep in target or '/' in target:
                dst = target if os.path.isabs(target) else os.path.join(panel.path, target)
            else:
                dst = os.path.join(panel.path, target)
            try:
                shutil.move(src, dst)
                panel.refresh()
                self.other_panel().refresh()
                self.status.set_text(f" Moved: {src} → {dst}")
            except Exception as e:
                self.status.set_text(f" ERROR: {e}")
            self.loop.widget = self.frame
            self.refresh_columns()

        def on_cancel(btn):
            self.loop.widget = self.frame

        urwid.connect_signal(ok_btn,     'click', on_ok)
        urwid.connect_signal(cancel_btn, 'click', on_cancel)
        self.loop.widget = overlay

    # ------------------------------------------------------------------
    # F9 Menu
    # ------------------------------------------------------------------
    def show_menu(self):
        panel_name = "Left" if self.active == 'left' else "Right"

        items = [
            ("Sort by name",          lambda: self.sort_panel('name')),
            ("Sort by size",          lambda: self.sort_panel('size')),
            ("Sort by date",          lambda: self.sort_panel('date')),
            ("─────────────────",    None),
            ("Go to directory...",   self.goto_dialog),
            ("Copy path to cmdline", self.path_to_cmdline),
            ("─────────────────",    None),
            ("Close menu",           self.close_menu),
        ]

        buttons = []
        for label, action in items:
            if action is None:
                buttons.append(urwid.Text(label))
            else:
                btn = urwid.Button(label)
                urwid.connect_signal(btn, 'click',
                                     lambda b, a=action: (self.close_menu(), a()))
                buttons.append(btn)

        listbox = urwid.ListBox(urwid.SimpleFocusListWalker(buttons))
        box     = urwid.LineBox(listbox, title=f" {panel_name} Panel ")
        overlay = urwid.Overlay(box, self.frame,
                                align='left', width=28,
                                valign='top', height=len(items) + 2)

        def menu_input(keys, raw):
            result = []
            for key in keys:
                if key in ('esc', 'f9'):
                    self.close_menu()
                else:
                    result.append(key)
            return result

        self.loop.input_filter = menu_input
        self.loop.widget = overlay

    def close_menu(self):
        self.loop.widget = self.frame
        self.loop.input_filter = self.input_filter

    def sort_panel(self, by):
        panel = self.active_panel()
        panel.sort_by = by
        panel.refresh()
        self.refresh_columns()
        self.status.set_text(f" Sorted by: {by}")

    def goto_dialog(self):
        edit       = urwid.Edit("Go to: ", edit_text=self.active_panel().path)
        ok_btn     = urwid.Button("OK")
        cancel_btn = urwid.Button("Cancel")
        pile    = urwid.Pile([edit, urwid.Divider(), urwid.Columns([ok_btn, cancel_btn])])
        box     = urwid.LineBox(urwid.Filler(pile), title=" Go to directory")
        overlay = urwid.Overlay(box, self.frame,
                                align='center', width=60,
                                valign='middle', height=8)

        def on_ok(btn):
            path = edit.edit_text.strip()
            if os.path.isdir(path):
                self.active_panel().path = os.path.abspath(path)
                self.active_panel().refresh()
                self.refresh_columns()
                self.status.set_text(f" → {path}")
            else:
                self.status.set_text(f" ERROR: '{path}' is not a directory")
            self.loop.widget = self.frame
            self.loop.input_filter = self.input_filter

        def on_cancel(btn):
            self.loop.widget = self.frame
            self.loop.input_filter = self.input_filter

        urwid.connect_signal(ok_btn,     'click', on_ok)
        urwid.connect_signal(cancel_btn, 'click', on_cancel)
        self.loop.widget = overlay

    def path_to_cmdline(self):
        self.cmdline.set_edit_text(self.active_panel().path + "/")
        self.status.set_text(" Path copied to cmdline")

    # ------------------------------------------------------------------
    # Command line execute
    # ------------------------------------------------------------------
    def run_command(self):
        import subprocess
        cmd = self.cmdline.edit_text.strip()
        if not cmd:
            return
        self.cmdline.set_edit_text("")

        INTERACTIVE = ('ssh', 'scp', 'sftp', 'ftp', 'telnet',
                       'vi', 'vim', 'nano', 'less', 'more',
                       'top', 'htop', 'python', 'bash', 'sh')
        first_word = cmd.split()[0].lower()
        if first_word in INTERACTIVE:
            self.loop.stop()
            subprocess.call(cmd, shell=True, cwd=self.active_panel().path)
            self.loop.start()
            self.left.refresh()
            self.right.refresh()
            self.refresh_columns()
            return

        try:
            result = subprocess.run(
                cmd, shell=True,
                cwd=self.active_panel().path,
                capture_output=True, text=True,
                timeout=30
            )
            output = result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            output = "ERROR: command exceeded 30s timeout"
        except Exception as e:
            output = str(e)

        if not output:
            output = "(no output)"

        self.left.refresh()
        self.right.refresh()
        self.refresh_columns()

        lines   = output.splitlines()
        widgets = [urwid.Text(line) for line in lines] if lines else [urwid.Text("(no output)")]
        listbox = urwid.ListBox(urwid.SimpleFocusListWalker(widgets))
        box     = urwid.LineBox(listbox, title=f" {cmd} — Q to close")
        overlay = urwid.Overlay(box, self.frame,
                                align='center', width=('relative', 90),
                                valign='middle', height=('relative', 90))

        old_widget = self.loop.widget

        def viewer_input(keys, raw):
            result = []
            for key in keys:
                if key in ('q', 'Q', 'esc'):
                    self.loop.widget = old_widget
                    self.loop.input_filter = self.input_filter
                else:
                    result.append(key)
            return result

        self.loop.input_filter = viewer_input
        self.loop.widget = overlay

    # ------------------------------------------------------------------
    # F4 Edit (nano)
    # ------------------------------------------------------------------
    def edit_file(self):
        import subprocess
        panel = self.active_panel()
        item  = panel.selected_item()
        if item in ('.', '..'):
            return
        full = os.path.join(panel.path, item)
        if os.path.isdir(full):
            self.status.set_text(f" F4: '{item}' is a directory")
            return
        self.loop.stop()
        subprocess.call(['nano', full])
        self.loop.start()
        panel.refresh()
        self.refresh_columns()
        self.status.set_text(f" Edited: {item}")

    # ------------------------------------------------------------------
    # F3 View
    # ------------------------------------------------------------------
    def view_file(self):
        panel = self.active_panel()
        item  = panel.selected_item()
        if item in ('.', '..'):
            return
        full = os.path.join(panel.path, item)
        if os.path.isdir(full):
            self.status.set_text(f" F3: '{item}' is a directory")
            return
        try:
            with open(full, 'r', errors='replace') as f:
                lines = f.readlines()
        except Exception as e:
            self.status.set_text(f" ERROR: {e}")
            return

        widgets = [urwid.Text(line.rstrip('\n')) for line in lines]
        if not widgets:
            widgets = [urwid.Text("(empty file)")]

        listbox = urwid.ListBox(urwid.SimpleFocusListWalker(widgets))
        box     = urwid.LineBox(listbox, title=f" {item} — Q to close")
        overlay = urwid.Overlay(box, self.frame,
                                align='center', width=('relative', 90),
                                valign='middle', height=('relative', 90))

        old_widget = self.loop.widget

        def viewer_input(keys, raw):
            result = []
            for key in keys:
                if key in ('q', 'Q', 'f3', 'esc'):
                    self.loop.widget = old_widget
                    self.loop.input_filter = self.input_filter
                else:
                    result.append(key)
            return result

        self.loop.input_filter = viewer_input
        self.loop.widget = overlay

    # ------------------------------------------------------------------
    # F7 Mkdir dialog
    # ------------------------------------------------------------------
    def mkdir_dialog(self):
        edit       = urwid.Edit("Directory name: ")
        ok_btn     = urwid.Button("OK")
        cancel_btn = urwid.Button("Cancel")

        pile    = urwid.Pile([edit, urwid.Columns([ok_btn, cancel_btn])])
        box     = urwid.LineBox(urwid.Filler(pile), title=" F7 New directory")
        overlay = urwid.Overlay(box, self.frame,
                                align='center', width=50,
                                valign='middle', height=6)

        def on_ok(btn):
            name = edit.edit_text.strip()
            if name:
                new_dir = os.path.join(self.active_panel().path, name)
                try:
                    os.makedirs(new_dir, exist_ok=True)
                    self.active_panel().refresh()
                    self.status.set_text(f" Created: {new_dir}")
                except Exception as e:
                    self.status.set_text(f" ERROR: {e}")
            self.loop.widget = self.frame
            self.refresh_columns()

        def on_cancel(btn):
            self.loop.widget = self.frame

        urwid.connect_signal(ok_btn,     'click', on_ok)
        urwid.connect_signal(cancel_btn, 'click', on_cancel)
        self.loop.widget = overlay

    # ------------------------------------------------------------------
    # F8 Delete dialog
    # ------------------------------------------------------------------
    def delete_dialog(self):
        import shutil
        panel = self.active_panel()
        item  = panel.selected_item()
        if item in ('.', '..'):
            return

        yes_btn = urwid.Button("Yes, delete")
        no_btn  = urwid.Button("No")

        msg     = urwid.Text(f"Delete '{item}'?", align='center')
        pile    = urwid.Pile([msg, urwid.Divider(), urwid.Columns([yes_btn, no_btn])])
        box     = urwid.LineBox(urwid.Filler(pile), title=" F8 Delete")
        overlay = urwid.Overlay(box, self.frame,
                                align='center', width=50,
                                valign='middle', height=7)

        def on_yes(btn):
            full = os.path.join(panel.path, item)
            try:
                if os.path.isdir(full):
                    shutil.rmtree(full)
                else:
                    os.remove(full)
                panel.refresh()
                self.status.set_text(f" Deleted: {full}")
            except Exception as e:
                self.status.set_text(f" ERROR: {e}")
            self.loop.widget = self.frame
            self.refresh_columns()

        def on_no(btn):
            self.loop.widget = self.frame

        urwid.connect_signal(yes_btn, 'click', on_yes)
        urwid.connect_signal(no_btn,  'click', on_no)
        self.loop.widget = overlay

    # ------------------------------------------------------------------
    def run(self):
        self.loop.run()


# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    PyMC().run()