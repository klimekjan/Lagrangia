# =============================================================================
# maths.py — Math Curve Explorer
# Pure mathematical helpers. No pygame dependency — safe to unit-test alone.
# =============================================================================

import numpy as np
from constants import (
    GRID_RANGE, CANVAS_W, CANVAS_H,
    C_CURVE, C_CURVE_GLOW,
    EQUATIONS,
)


# -----------------------------------------------------------------------------
# Coordinate conversion
# -----------------------------------------------------------------------------

def math_to_canvas(mx: float, my: float,
                   origin_x: int, origin_y: int, scale: float) -> tuple:
    """Map a mathematical (x, y) point to pixel coordinates on the canvas."""
    return int(origin_x + mx * scale), int(origin_y - my * scale)


def canvas_to_math(px: int, py: int,
                   origin_x: int, origin_y: int, scale: float) -> tuple:
    """Map canvas pixel coordinates back to mathematical (x, y)."""
    return (px - origin_x) / scale, (origin_y - py) / scale


# -----------------------------------------------------------------------------
# Equation evaluator
# -----------------------------------------------------------------------------

def evaluate(eq_idx: int, x_arr: np.ndarray, params: list) -> np.ndarray:
    """
    Evaluate equation eq_idx over the array x_arr using params = [a, b, c, ...].
    Returns a clipped float64 array; asymptote regions become NaN.
    """
    p = params
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        if   eq_idx == 0: y = p[0]*x_arr**2 + p[1]*x_arr + p[2]
        elif eq_idx == 1: y = p[0] * np.sin(p[1]*x_arr + p[2])
        elif eq_idx == 2: y = p[0] * np.cos(p[1]*x_arr + p[2])
        elif eq_idx == 3: y = p[0]*x_arr**3 + p[1]*x_arr**2 + p[2]*x_arr + p[3]
        elif eq_idx == 4: y = p[0]*x_arr + p[1]
        elif eq_idx == 5:
            raw = p[0] * np.tan(p[1]*x_arr + p[2])
            y   = np.where(np.abs(raw) > 50, np.nan, raw)   # hide asymptotes
        elif eq_idx == 6: y = p[0] * np.abs(x_arr + p[1]) + p[2]
        elif eq_idx == 7: y = p[0] * np.exp(np.clip(p[1]*x_arr, -30, 30)) + p[2]
        else:             y = np.zeros_like(x_arr)
    return np.clip(y, -500, 500)


# -----------------------------------------------------------------------------
# Equation string builder
# -----------------------------------------------------------------------------

def equation_string(eq_idx: int, params: list) -> str:
    """Return a compact, human-readable equation string suitable for the panel."""
    def s(v): return f"{v:+.2f}" if abs(v) >= 0.005 else "+0.00"   # signed
    def r(v): return f"{v:.2f}"                                      # plain

    p = params
    if   eq_idx == 0: return f"y = {r(p[0])}x²  {s(p[1])}x  {s(p[2])}"
    elif eq_idx == 1: return f"y = {r(p[0])}·sin({r(p[1])}x {s(p[2])})"
    elif eq_idx == 2: return f"y = {r(p[0])}·cos({r(p[1])}x {s(p[2])})"
    elif eq_idx == 3: return f"y = {r(p[0])}x³ {s(p[1])}x² {s(p[2])}x {s(p[3])}"
    elif eq_idx == 4: return f"y = {r(p[0])}x  {s(p[1])}"
    elif eq_idx == 5: return f"y = {r(p[0])}·tan({r(p[1])}x {s(p[2])})"
    elif eq_idx == 6: return f"y = {r(p[0])}·|x {s(p[1])}|  {s(p[2])}"
    elif eq_idx == 7: return f"y = {r(p[0])}·e^({r(p[1])}x)  {s(p[2])}"
    return ""


# -----------------------------------------------------------------------------
# Precision scorer
# -----------------------------------------------------------------------------

def compute_score(drawn_pixels: list, eq_idx: int, params: list,
                  origin_x: int, origin_y: int, scale: float) -> float:
    """
    Measure how accurately the user traced the target curve.

    Algorithm:
      1. Convert each drawn pixel to mathematical (x, y).
      2. Evaluate the true curve at those x values.
      3. Compute the mean squared vertical error.
      4. Map MSE → score:  MSE = 0 → 100,  MSE ≥ 25 → 0.

    Returns a float in [0.0, 100.0].
    """
    if len(drawn_pixels) < 5:
        return 0.0

    pts    = np.array(drawn_pixels, dtype=float)
    mx     = (pts[:, 0] - origin_x) / scale
    my     = (origin_y  - pts[:, 1]) / scale
    true_y = evaluate(eq_idx, mx, params)
    valid  = ~np.isnan(true_y) & ~np.isinf(true_y)

    if valid.sum() == 0:
        return 0.0

    mse = float(np.mean((my[valid] - true_y[valid]) ** 2))
    return round(max(0.0, 100.0 * (1.0 - mse / 25.0)), 1)


# -----------------------------------------------------------------------------
# Score presentation helpers
# -----------------------------------------------------------------------------

def score_colour(score: float) -> tuple:
    from constants import C_GREEN, C_YELLOW, C_RED
    if score >= 85: return C_GREEN
    if score >= 60: return C_YELLOW
    return C_RED


def score_label(score: float) -> str:
    if score >= 90: return "EXCELLENT!"
    if score >= 75: return "GREAT!"
    if score >= 55: return "GOOD"
    if score >= 35: return "KEEP TRYING"
    return "NEEDS WORK"
