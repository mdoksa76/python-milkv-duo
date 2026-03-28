"""StatusBar — dno ekrana: naziv datoteke, Ln/Col, words, RAM info, dirty flag."""

import urwid
from config import mem_info, APP_NAME


class StatusBar(urwid.Text):

    def __init__(self):
        super().__init__("", wrap="clip")
        self._map = urwid.AttrMap(self, "statusbar")

    def as_widget(self):
        return self._map

    def update(self, filepath=None, line=1, col=1, dirty=False,
               words=0, error=None):
        if error:
            self.set_text(("statusbar_err", f"  \u26a0  {error} "))
            return

        name = filepath or f"[{APP_NAME} \u2014 novi dokument]"
        dirty_mark = " *" if dirty else "  "
        rss, free, total = mem_info()
        ram_str = f"RAM pyword: {rss:.1f} MB  free: {free:.0f} MB"
        text = (f" {name}{dirty_mark}   Ln {line}, Col {col}"
                f"   Words: {words}   {ram_str} ")
        attr = "dirty" if dirty else "statusbar"
        self.set_text((attr, text))
