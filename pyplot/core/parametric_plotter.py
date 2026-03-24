# pyplot/core/parametric_plotter.py

import re
import plotext as plt
from sympy import Symbol

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

t_sym = Symbol('t')

def strip_ansi(text):
    return _ANSI_RE.sub('', text)

def generate_parametric_plot(curves, t_min, t_max, t_step,
                              plot_title, x_label, y_label,
                              x_min=None, x_max=None,
                              y_min=None, y_max=None,
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

    steps = int((t_max - t_min) / t_step)
    ts = [t_min + i * t_step for i in range(steps + 1)]

    plotted = False
    for curve in curves:
        if not curve.checked:
            continue

        xs = []
        ys = []
        for t in ts:
            try:
                x = float(curve.xt_sympy.subs(t_sym, t))
                y = float(curve.yt_sympy.subs(t_sym, t))
                if abs(x) <= 1e10 and abs(y) <= 1e10:
                    xs.append(x)
                    ys.append(y)
            except Exception:
                pass

        if xs and ys:
            plt.scatter(xs, ys, marker=curve.marker)
            plotted = True

    if not plotted:
        return "No curves to plot."

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
