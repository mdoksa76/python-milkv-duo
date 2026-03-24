# pyplot/core/fit.py

"""
Implementacije osnovnih fitova bez eksternih dependencija.
Sve koristi čisti Python math modul.
"""

import math

# ------------------------------------------------------------------
# Pomoćne funkcije
# ------------------------------------------------------------------

def _mean(values):
    return sum(values) / len(values)

def _r_squared(ys, ys_fit):
    """Koeficijent determinacije R²."""
    y_mean = _mean(ys)
    ss_tot = sum((y - y_mean) ** 2 for y in ys)
    ss_res = sum((y - yf) ** 2 for y, yf in zip(ys, ys_fit))
    if ss_tot == 0:
        return 1.0
    return 1.0 - ss_res / ss_tot

def _rmse(ys, ys_fit):
    """Root mean square error."""
    n = len(ys)
    return math.sqrt(sum((y - yf) ** 2 for y, yf in zip(ys, ys_fit)) / n)

# ------------------------------------------------------------------
# Linearni fit: y = ax + b
# ------------------------------------------------------------------

def linear_fit(points):
    """
    Linearni fit y = ax + b metodom najmanjih kvadrata.
    Vraća (a, b, r2, rmse, formula_str) ili None ako nije moguće.
    """
    n = len(points)
    if n < 2:
        return None

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xx = sum(x * x for x in xs)
    sum_xy = sum(x * y for x, y in zip(xs, ys))

    denom = n * sum_xx - sum_x ** 2
    if abs(denom) < 1e-12:
        return None

    a = (n * sum_xy - sum_x * sum_y) / denom
    b = (sum_y - a * sum_x) / n

    ys_fit = [a * x + b for x in xs]
    r2 = _r_squared(ys, ys_fit)
    rmse_val = _rmse(ys, ys_fit)

    sign = '+' if b >= 0 else '-'
    formula = f"y = {a:.4f}x {sign} {abs(b):.4f}"

    return {
        'a': a, 'b': b,
        'r2': r2, 'rmse': rmse_val,
        'formula': formula,
        'fn': lambda x: a * x + b,
    }

# ------------------------------------------------------------------
# Eksponencijalni fit: y = a * e^(bx)
# ------------------------------------------------------------------

def exponential_fit(points):
    """
    Eksponencijalni fit y = a * e^(bx).
    Linearizacija: ln(y) = ln(a) + bx
    Radi samo za y > 0.
    Vraća dict s koeficijentima ili None.
    """
    # Filtriraj točke s y > 0
    valid = [(x, y) for x, y in points if y > 0]
    if len(valid) < 2:
        return None

    # Linearni fit na (x, ln(y))
    log_points = [(x, math.log(y)) for x, y in valid]
    result = linear_fit(log_points)
    if result is None:
        return None

    b = result['a']
    a = math.exp(result['b'])

    xs = [p[0] for p in valid]
    ys = [p[1] for p in valid]
    ys_fit = [a * math.exp(b * x) for x in xs]
    r2 = _r_squared(ys, ys_fit)
    rmse_val = _rmse(ys, ys_fit)

    sign = '+' if b >= 0 else ''
    formula = f"y = {a:.4f} * e^({b:.4f}x)"

    return {
        'a': a, 'b': b,
        'r2': r2, 'rmse': rmse_val,
        'formula': formula,
        'fn': lambda x, a=a, b=b: a * math.exp(b * x),
    }

# ------------------------------------------------------------------
# Logaritamski fit: y = a * ln(x) + b
# ------------------------------------------------------------------

def logarithmic_fit(points):
    """
    Logaritamski fit y = a * ln(x) + b.
    Radi samo za x > 0.
    Vraća dict s koeficijentima ili None.
    """
    valid = [(x, y) for x, y in points if x > 0]
    if len(valid) < 2:
        return None

    # Linearni fit na (ln(x), y)
    log_points = [(math.log(x), y) for x, y in valid]
    result = linear_fit(log_points)
    if result is None:
        return None

    a = result['a']
    b = result['b']

    xs = [p[0] for p in valid]
    ys = [p[1] for p in valid]
    ys_fit = [a * math.log(x) + b for x in xs]
    r2 = _r_squared(ys, ys_fit)
    rmse_val = _rmse(ys, ys_fit)

    sign = '+' if b >= 0 else '-'
    formula = f"y = {a:.4f} * ln(x) {sign} {abs(b):.4f}"

    return {
        'a': a, 'b': b,
        'r2': r2, 'rmse': rmse_val,
        'formula': formula,
        'fn': lambda x, a=a, b=b: a * math.log(x) + b if x > 0 else None,
    }

# ------------------------------------------------------------------
# Polinomijalni fit 2. reda: y = ax² + bx + c
# ------------------------------------------------------------------

def _solve_3x3(A, rhs):
    """
    Gauss-Jordan eliminacija za 3x3 sustav Ax = rhs.
    Vraća [x0, x1, x2] ili None ako je singularan.
    """
    # Kopiraj da ne mijenjamo original
    M = [list(A[i]) + [rhs[i]] for i in range(3)]

    for col in range(3):
        # Pivoting
        max_row = max(range(col, 3), key=lambda r: abs(M[r][col]))
        M[col], M[max_row] = M[max_row], M[col]

        if abs(M[col][col]) < 1e-12:
            return None

        for row in range(3):
            if row == col:
                continue
            factor = M[row][col] / M[col][col]
            for k in range(col, 4):
                M[row][k] -= factor * M[col][k]

    return [M[i][3] / M[i][i] for i in range(3)]


def polynomial2_fit(points):
    """
    Polinomijalni fit 2. reda: y = ax² + bx + c.
    Vraća dict s koeficijentima ili None.
    """
    n = len(points)
    if n < 3:
        return None

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    # Normalne jednadžbe za least squares
    s0 = n
    s1 = sum(xs)
    s2 = sum(x**2 for x in xs)
    s3 = sum(x**3 for x in xs)
    s4 = sum(x**4 for x in xs)
    t0 = sum(ys)
    t1 = sum(x * y for x, y in zip(xs, ys))
    t2 = sum(x**2 * y for x, y in zip(xs, ys))

    A = [
        [s4, s3, s2],
        [s3, s2, s1],
        [s2, s1, s0],
    ]
    rhs = [t2, t1, t0]

    coeffs = _solve_3x3(A, rhs)
    if coeffs is None:
        return None

    a, b, c = coeffs

    ys_fit = [a * x**2 + b * x + c for x in xs]
    r2 = _r_squared(ys, ys_fit)
    rmse_val = _rmse(ys, ys_fit)

    sign_b = '+' if b >= 0 else '-'
    sign_c = '+' if c >= 0 else '-'
    formula = f"y = {a:.4f}x² {sign_b} {abs(b):.4f}x {sign_c} {abs(c):.4f}"

    return {
        'a': a, 'b': b, 'c': c,
        'r2': r2, 'rmse': rmse_val,
        'formula': formula,
        'fn': lambda x, a=a, b=b, c=c: a * x**2 + b * x + c,
    }

# ------------------------------------------------------------------
# Glavni entry point
# ------------------------------------------------------------------

FIT_TYPES = {
    'linear':      ('Linear',      linear_fit),
    'exponential': ('Exponential', exponential_fit),
    'logarithmic': ('Logarithmic', logarithmic_fit),
    'poly2':       ('Polynomial²', polynomial2_fit),
}

def run_fits(points, selected):
    """
    Pokreni odabrane fitove na točkama.
    selected: lista ključeva iz FIT_TYPES, npr. ['linear', 'poly2']
    Vraća dict: {key: result_dict or None}
    """
    results = {}
    for key in selected:
        if key in FIT_TYPES:
            _, fn = FIT_TYPES[key]
            try:
                results[key] = fn(points)
            except Exception:
                results[key] = None
    return results

def format_results(results):
    """
    Formatiraj rezultate fitova kao string za prikaz u UI-u.
    """
    lines = []
    for key, result in results.items():
        name = FIT_TYPES[key][0] if key in FIT_TYPES else key
        if result is None:
            lines.append(f"{name}: N/A")
        else:
            lines.append(f"{name}: {result['formula']}")
            lines.append(f"  R²={result['r2']:.4f}  RMSE={result['rmse']:.4f}")
    return '\n'.join(lines)
