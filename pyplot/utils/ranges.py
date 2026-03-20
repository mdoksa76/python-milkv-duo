# pyplot/utils/ranges.py

def parse_float(value, default=None):
    """
    Convert a string to float.
    If empty string: return default.
    If invalid: return (None, "error message")
    """
    if value == "" or value is None:
        return default, None
    try:
        return float(value), None
    except Exception:
        return None, f"Invalid number: '{value}'"

def parse_range(x_min_str, x_max_str, y_min_str, y_max_str):
    """
    Parse all range inputs and return:
        x_min, x_max, y_min, y_max, error_message
    """
    x_min, err = parse_float(x_min_str, default=-10)
    if err: return None, None, None, None, err
    x_max, err = parse_float(x_max_str, default=10)
    if err: return None, None, None, None, err
    y_min, err = parse_float(y_min_str, default=None)
    if err: return None, None, None, None, err
    y_max, err = parse_float(y_max_str, default=None)
    if err: return None, None, None, None, err

    if x_min >= x_max:
        return None, None, None, None, "X min must be less than X max."

    if y_min is not None and y_max is not None:
        if y_min >= y_max:
            return None, None, None, None, "Y min must be less than Y max."

    return x_min, x_max, y_min, y_max, None

def parse_t_range(t_min_str, t_max_str, t_step_str):
    """
    Parse parametric t range inputs and return:
        t_min, t_max, t_step, error_message
    """
    t_min, err = parse_float(t_min_str, default=0.0)
    if err: return None, None, None, err
    t_max, err = parse_float(t_max_str, default=6.2832)  # 2*pi default
    if err: return None, None, None, err
    t_step, err = parse_float(t_step_str, default=0.1)
    if err: return None, None, None, err

    if t_min >= t_max:
        return None, None, None, "T min must be less than T max."
    if t_step <= 0:
        return None, None, None, "T step must be greater than 0."
    if t_step >= (t_max - t_min):
        return None, None, None, "T step must be smaller than T range."

    return t_min, t_max, t_step, None
