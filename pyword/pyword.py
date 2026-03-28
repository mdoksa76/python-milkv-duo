#!/usr/bin/env python3
"""
pyword — minimalni TUI editor za Milk-V Duo (64MB RAM)
Podržava čitanje .docx, .odt, .pyword, .txt
Snima u .pyword (prošireni plain text) ili .txt

Upotreba:
  pyword.py                  # novi prazan dokument
  pyword.py dokument.odt     # otvori ODF dokument
  pyword.py izvjestaj.docx   # otvori DOCX dokument
  pyword.py biljeske.pyword  # otvori nativni format
"""

import sys
import os

# Dodaj roditeljski direktorij u path (za import config, core, ui)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import PyWordApp
import urwid


def main():
    filepath = None
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if not os.path.isfile(filepath):
            print(f"pyword: datoteka ne postoji: {filepath}", file=sys.stderr)
            sys.exit(1)

    app = PyWordApp(filepath=filepath)
    try:
        app.run()
    except urwid.ExitMainLoop:
        pass
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
