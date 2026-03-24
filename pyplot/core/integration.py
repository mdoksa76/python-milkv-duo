# pyplot/core/integration.py

"""
Numeričke metode određenog integrala.
Čisti Python, nema dependencija.
"""

def _eval_fn(sympy_expr, x):
    """Evaluiraj sympy izraz u točki x."""
    try:
        y = float(sympy_expr.subs("x", x))
        if abs(y) > 1e10:
            return None
        return y
    except Exception:
        return None

# ------------------------------------------------------------------
# Edukacijske metode
# ------------------------------------------------------------------

def rectangle_left(sympy_expr, a, b, n=1000):
    """
    Lijevi Riemannov zbroj.
    Koristi lijevu točku svakog podintervala.
    """
    h = (b - a) / n
    total = 0.0
    for i in range(n):
        x = a + i * h
        y = _eval_fn(sympy_expr, x)
        if y is None:
            return None, "Function undefined in interval"
        total += y * h
    return total, None


def rectangle_right(sympy_expr, a, b, n=1000):
    """
    Desni Riemannov zbroj.
    Koristi desnu točku svakog podintervala.
    """
    h = (b - a) / n
    total = 0.0
    for i in range(1, n + 1):
        x = a + i * h
        y = _eval_fn(sympy_expr, x)
        if y is None:
            return None, "Function undefined in interval"
        total += y * h
    return total, None


def rectangle_mid(sympy_expr, a, b, n=1000):
    """
    Srednji Riemannov zbroj (midpoint rule).
    Koristi srednju točku svakog podintervala — precizniji od L/R.
    """
    h = (b - a) / n
    total = 0.0
    for i in range(n):
        x = a + (i + 0.5) * h
        y = _eval_fn(sympy_expr, x)
        if y is None:
            return None, "Function undefined in interval"
        total += y * h
    return total, None


# ------------------------------------------------------------------
# Napredna metoda
# ------------------------------------------------------------------

def simpson(sympy_expr, a, b, n=1000):
    """
    Simpsonova metoda — aproksimira parabolicima umjesto pravcima.
    n mora biti paran.
    Red greške: O(h^4) — puno bolji od rectangle metoda O(h^2).
    """
    if n % 2 != 0:
        n += 1  # osiguraj parni n

    h = (b - a) / n
    total = 0.0

    y0 = _eval_fn(sympy_expr, a)
    yn = _eval_fn(sympy_expr, b)
    if y0 is None or yn is None:
        return None, "Function undefined at interval endpoints"

    total = y0 + yn

    for i in range(1, n):
        x = a + i * h
        y = _eval_fn(sympy_expr, x)
        if y is None:
            return None, "Function undefined in interval"
        if i % 2 == 0:
            total += 2 * y
        else:
            total += 4 * y

    total *= h / 3
    return total, None


# ------------------------------------------------------------------
# Procjena greške (usporedba s dvostrukim brojem koraka)
# ------------------------------------------------------------------

def estimate_error(method_fn, sympy_expr, a, b, n=1000):
    """
    Procijeni grešku Richardson ekstrapolacijom:
    pokreni s n i 2n koraka, razlika je aproksimacija greške.
    """
    r1, err = method_fn(sympy_expr, a, b, n)
    if err:
        return None
    r2, err = method_fn(sympy_expr, a, b, n * 2)
    if err:
        return None
    return abs(r2 - r1)


# ------------------------------------------------------------------
# Registar metoda
# ------------------------------------------------------------------

METHODS = {
    'left':    ('Left Rectangle',  rectangle_left),
    'right':   ('Right Rectangle', rectangle_right),
    'mid':     ('Midpoint',        rectangle_mid),
    'simpson': ('Simpson',         simpson),
}

def integrate(sympy_expr, a, b, method_key, n=1000):
    """
    Pokreni integraciju odabranom metodom.
    Vraća (result, error_estimate, error_msg).
    """
    if method_key not in METHODS:
        return None, None, f"Unknown method: {method_key}"

    name, fn = METHODS[method_key]
    result, err = fn(sympy_expr, a, b, n)
    if err:
        return None, None, err

    error_est = estimate_error(fn, sympy_expr, a, b, n)

    return result, error_est, None

def format_result(result, error_est, method_key):
    """Formatiraj rezultat za prikaz u UI-u."""
    name = METHODS[method_key][0] if method_key in METHODS else method_key
    lines = [f"{name}:"]
    lines.append(f"  Result: {result:.8f}")
    if error_est is not None:
        lines.append(f"  Error est.: {error_est:.2e}")
    return '\n'.join(lines)
