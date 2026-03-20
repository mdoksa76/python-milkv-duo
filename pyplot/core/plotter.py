# pyplot/core/plotter.py

import re
import plotext as plt
from pyplot.core.state import state

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[mABCDEFGHJKLMST]|\x1b\(B|\x1b=|\x1b>')

_BOX = str.maketrans({
    '│': '|', '┃': '|',
    '─': '-', '━': '-',
    '┌': '+', '┐': '+', '└': '+', '┘': '+',
    '├': '+', '┤': '+', '┬': '+', '┴': '+', '┼': '+',
    '┏': '+', '┓': '+', '┗': '+', '┛': '+',
    '┣': '+', '┫': '+', '┳': '+', '┻': '+', '╋': '+',
    '▄': '*', '▀': '*', '■': '*', '□': '.',
    '◆': '*', '◇': '.', '○': 'o', '●': '*',
})

def strip_ansi(text):
    return _ANSI_RE.sub('', text)

def generate_plot(functions, marker, x_min, x_max, y_min, y_max,
                  plot_title, x_label, y_label, plot_width=76, plot_height=24):

    plt.clear_figure()

    # Eksplicitne dimenzije - plotext mora znati koliko prostora ima
    plt.plotsize(plot_width, plot_height)

    try:
        plt.unicode_lines(False)
    except Exception:
        pass

    try:
        plt.unicode_chars(False)
    except Exception:
        pass

    try:
        plt.theme('ascii')
    except Exception:
        pass

    try:
        plt.colored(False)
    except Exception:
        pass

    # Sanitiziraj marker - zamijeni Unicode znakove ASCII ekvivalentima
    _MARKER_MAP = {'°': 'o', '×': 'x', '•': '*', '·': '.', '★': '*', '◉': 'o'}
    safe_marker = _MARKER_MAP.get(marker, marker)
    try:
        safe_marker.encode('ascii')
    except (UnicodeEncodeError, AttributeError):
        safe_marker = '.'

    step = (x_max - x_min) / plot_width
    xs = [x_min + i * step for i in range(plot_width + 1)]

    plotted = False
    for f in functions:
        if not f.checked:
            continue

        ys = []
        for x in xs:
            try:
                y = float(f.sympy_expr.subs("x", x))
                if abs(y) > 1e10:
                    y = None
            except Exception:
                y = None
            ys.append(y)

        plt.plot(xs, ys, marker=f.marker)
        plotted = True

    if not plotted:
        return "No functions to plot."

    if y_min is not None and y_max is not None:
        try:
            plt.ylim(y_min, y_max)
        except Exception:
            return "Invalid Y range."

    # X limiti — uvijek postavljeni jer generiramo xs od x_min do x_max
    try:
        plt.xlim(x_min, x_max)
    except Exception:
        pass

    plt.title("")
    plt.xlabel("")
    plt.ylabel("")
    plt.frame(True)
    plt.grid(False)

    try:
        raw = plt.build()
    except Exception:
        return generate_ascii_fallback(functions, x_min, x_max, y_min, y_max, marker,
                                       plot_width, plot_height)

    clean = strip_ansi(raw)

    lines = []
    for line in clean.split('\n'):
        line = line.translate(_BOX)
        line = line.encode('ascii', errors='replace').decode('ascii')
        line = line.replace('?', ' ')
        lines.append(line.rstrip())

    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        return generate_ascii_fallback(functions, x_min, x_max, y_min, y_max, marker,
                                       plot_width, plot_height)

    # Dodaj naslov i labele ručno (plotext ih ispisuje u boji pa filter briše)
    result = []
    if plot_title:
        result.append(plot_title.center(plot_width))
    if y_label:
        # Y label uz svaki red je kompleksno - ispiši ga iznad grafa
        result.append(f"y: {y_label}")
    result.extend(lines)
    if x_label:
        result.append(f"x: {x_label}".center(plot_width))

    return '\n'.join(result)


def generate_ascii_fallback(functions, x_min, x_max, y_min, y_max, marker,
                             width=60, height=20):
    if not functions:
        return "No functions to plot"

    xs = [x_min + (x_max - x_min) * i / (width - 1) for i in range(width)]

    all_ys = []
    for f in functions:
        if not f.checked:
            continue
        ys = []
        for x in xs:
            try:
                y = float(f.sympy_expr.subs("x", x))
                ys.append(y)
            except Exception:
                ys.append(None)
        all_ys.append(ys)

    if not all_ys:
        return "No checked functions"

    valid_ys = [y for ys in all_ys for y in ys if y is not None]
    if not valid_ys:
        return "No valid Y values"

    if y_min is None:
        y_min = min(valid_ys)
    if y_max is None:
        y_max = max(valid_ys)

    if y_min == y_max:
        y_max = y_min + 1

    grid = [[' ' for _ in range(width)] for _ in range(height)]

    for ys in all_ys:
        for i, y in enumerate(ys):
            if y is not None:
                row = int((y_max - y) / (y_max - y_min) * (height - 1))
                row = max(0, min(height - 1, row))
                grid[row][i] = marker if marker else '.'

    for i in range(width):
        zero_row = int((y_max - 0) / (y_max - y_min) * (height - 1))
        if 0 <= zero_row < height:
            if grid[zero_row][i] == ' ':
                grid[zero_row][i] = '-'

    return '\n'.join(''.join(row) for row in grid)
