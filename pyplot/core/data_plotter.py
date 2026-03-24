# pyplot/core/data_plotter.py

import re
import plotext as plt
from pyplot.core.fit import FIT_TYPES

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

# Markeri za fit krivulje — različiti od scatter markera
FIT_MARKERS = ['.', 'o', 'x', '*']

def strip_ansi(text):
    return _ANSI_RE.sub('', text)

def generate_data_plot(points, marker, plot_title, x_label, y_label,
                       x_min=None, x_max=None, y_min=None, y_max=None,
                       plot_width=76, plot_height=24, fit_curves=None):
    if not points:
        return "No data points to plot."

    plt.clear_figure()
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

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    plt.scatter(xs, ys, marker=marker)

    # Crtaj fit krivulje
    if fit_curves:
        for i, (key, (fxs, fys)) in enumerate(fit_curves.items()):
            fit_marker = FIT_MARKERS[i % len(FIT_MARKERS)]
            plt.plot(fxs, fys, marker=fit_marker)

    if x_min is not None and x_max is not None:
        try:
            plt.xlim(x_min, x_max)
        except Exception:
            return "Invalid X range."

    if y_min is not None and y_max is not None:
        try:
            plt.ylim(y_min, y_max)
        except Exception:
            return "Invalid Y range."

    plt.title("")
    plt.xlabel("")
    plt.ylabel("")
    plt.frame(True)
    plt.grid(False)

    try:
        raw = plt.build()
    except Exception:
        return "Plot error."

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
        return "Plot error."

    result = []
    if plot_title:
        result.append(plot_title.center(plot_width))
    if y_label:
        result.append(f"y: {y_label}")
    result.extend(lines)
    if x_label:
        result.append(f"x: {x_label}".center(plot_width))

    return '\n'.join(result)
