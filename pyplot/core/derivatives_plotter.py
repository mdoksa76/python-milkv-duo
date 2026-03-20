# pyplot/core/derivatives_plotter.py

import re
import plotext as plt

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

def generate_derivatives_plot(entries, x_min, x_max, y_min, y_max,
                               plot_title, x_label, y_label,
                               plot_width=76, plot_height=24):
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

    step = (x_max - x_min) / plot_width
    xs = [x_min + i * step for i in range(plot_width + 1)]

    plotted = False
    for entry in entries:
        if not entry.checked:
            continue

        ys = []
        for x in xs:
            try:
                y = float(entry.sympy_expr.subs("x", x))
                if abs(y) > 1e10:
                    y = None
            except Exception:
                y = None
            ys.append(y)

        plt.plot(xs, ys, marker=entry.marker)
        plotted = True

    if not plotted:
        return "No functions to plot."

    if y_min is not None and y_max is not None:
        try:
            plt.ylim(y_min, y_max)
        except Exception:
            return "Invalid Y range."

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
