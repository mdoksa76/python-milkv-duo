# pyplot/core/parser.py

import sympy as sp

def parse_expression(expr_text, var='x'):
    """
    Parse a mathematical expression string into a SymPy expression.
    var: 'x' za funkcije, 't' za parametarske krivulje
    Returns:
        sympy_expr (object) or None
        error_message (str) or None
    """
    sym = sp.symbols(var)
    try:
        sympy_expr = sp.sympify(expr_text, locals={var: sym})
        return sympy_expr, None
    except Exception as e:
        return None, f"Invalid expression: {e}"
