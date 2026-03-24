# pyplot/core/state.py

from dataclasses import dataclass

MARKERS = [".", "o", "x", "*", "+"]

@dataclass
class FunctionEntry:
    expr: str
    sympy_expr: object
    marker: str
    checked: bool = True

@dataclass
class ParametricEntry:
    xt_expr: str
    yt_expr: str
    xt_sympy: object
    yt_sympy: object
    marker: str
    checked: bool = True

class AppState:
    def __init__(self):
        self.functions = []       # lista FunctionEntry
        self.parametric = []      # lista ParametricEntry
        self.derivatives = []     # lista FunctionEntry (original + derivacije)
        self.marker = MARKERS[0]  # globalni marker (MarkerSelector)
        self.marker_index = 0     # za rotaciju

    def next_marker(self):
        marker = MARKERS[self.marker_index]
        self.marker_index = (self.marker_index + 1) % len(MARKERS)
        return marker

# Global singleton state
state = AppState()
