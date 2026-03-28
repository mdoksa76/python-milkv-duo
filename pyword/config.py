"""Konstante, keybindingsi i helper za RAM."""

import resource

APP_NAME    = "pyword"
APP_VERSION = "0.1.0"
NATIVE_EXT  = ".pyword"

# Keybindingsi
KEY_MENU    = "f2"
KEY_SAVE    = "ctrl s"
KEY_OPEN    = "ctrl o"
KEY_NEW     = "ctrl n"
KEY_QUIT    = "ctrl q"

# Palete boja
PALETTE = [
    # (ime,          fg,           bg)
    ("normal",       "default",    "default"),
    ("heading1",     "yellow,bold","default"),
    ("heading2",     "light cyan,bold", "default"),
    ("heading3",     "light green,bold","default"),
    ("list_item",    "light gray", "default"),
    ("statusbar",    "white",      "dark blue"),
    ("statusbar_err","white",      "dark red"),
    ("menubar",      "white",      "dark blue"),
    ("menu_item",    "black",      "light gray"),
    ("menu_focus",   "white",      "dark blue"),
    ("dialog",       "black",      "light gray"),
    ("dialog_focus", "white",      "dark blue"),
    ("dirty",        "yellow",     "dark blue"),
    ("input",        "default",    "default"),
    ("input_focus",  "white",      "dark blue"),
]


def mem_info() -> tuple:
    """Vraća (pyword_rss_mb, free_mb, total_mb)."""
    try:
        import sys
        kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        rss = kb / (1024 * 1024) if sys.platform == "darwin" else kb / 1024

        with open("/proc/meminfo") as f:
            info = {}
            for line in f:
                k, v = line.split(":")
                info[k.strip()] = int(v.strip().split()[0])
        total = info.get("MemTotal", 0) / 1024
        free  = info.get("MemAvailable", 0) / 1024
        return rss, free, total
    except Exception:
        return 0.0, 0.0, 0.0
