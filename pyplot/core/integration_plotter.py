# pyplot/core/integration_plotter.py

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

def generate_integration_plot(sympy_expr, x_min, x_max, y_min, y_max,
                               a, b, plot_title, x_label, y_label,
                               plot_width=80, plot_height=24):
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

    # Cijela funkcija
    ys = []
    for x in xs:
        try:
            y = float(sympy_expr.subs("x", x))
            ys.append(y if abs(y) <= 1e10 else None)
        except Exception:
            ys.append(None)

    plt.plot(xs, ys, marker='.')

    # Punjenje površine između a i b — vertikalne linije od 0 do f(x)
    fill_xs = []
    fill_ys = []
    steps_ab = max(20, int((b - a) / step))
    for i in range(steps_ab + 1):
        x = a + (b - a) * i / steps_ab
        try:
            y = float(sympy_expr.subs("x", x))
            if abs(y) <= 1e10:
                # Generiraj točke od 0 do y (ili od y do 0 ako je negativno)
                y0 = 0.0
                y1 = y
                if y1 < y0:
                    y0, y1 = y1, y0
                # ~5 točaka po vertikali — dovoljno za vizualni efekt
                n_fill = max(2, int(abs(y) * plot_height / max(1, (y_max or 10) - (y_min or -10)) * 0.5))
                n_fill = min(n_fill, 10)
                for j in range(n_fill + 1):
                    fy = y0 + (y1 - y0) * j / n_fill
                    fill_xs.append(x)
                    fill_ys.append(fy)
        except Exception:
            pass

    if fill_xs:
        plt.scatter(fill_xs, fill_ys, marker='|')

    if x_min is not None and x_max is not None:
        try:
            plt.xlim(x_min, x_max)
        except Exception:
            pass

    if y_min is not None and y_max is not None:
        try:
            plt.ylim(y_min, y_max)
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
