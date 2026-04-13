import numpy as np
from constants import PLOT_RANGE_X, PLOT_RANGE_Y


def math_to_canvas(mx: float, my: float,
                   origin_x: int, origin_y: int, scale: float) -> tuple:

    return int(origin_x + mx * scale), int(origin_y - my * scale)


def canvas_to_math(px: int, py: int,
                   origin_x: int, origin_y: int, scale: float) -> tuple:
    return (px - origin_x) / scale, (origin_y - py) / scale


def evaluate(eq_idx: int, x_arr: np.ndarray, params: list) -> np.ndarray:

    p = params
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        if eq_idx == 0: y = p[0]*x_arr + p[1]
        elif eq_idx == 1: y = p[0]*x_arr**2 + p[1]*x_arr + p[2]
        elif eq_idx == 2: y = p[0]*x_arr**3 + p[1]*x_arr**2 + p[2]*x_arr + p[3]
        elif eq_idx == 3: y = p[0] * np.sin(p[1]*x_arr + p[2])
        elif eq_idx == 4: y = p[0] * np.cos(p[1]*x_arr + p[2])
        elif eq_idx == 5:
            raw = p[0] * np.tan(p[1]*x_arr + p[2])
            y   = np.where(np.abs(raw) > 50, np.nan, raw)   # hide asymptotes
        elif eq_idx == 6: y = p[0] * np.abs(x_arr + p[1]) + p[2]
        elif eq_idx == 7: y = p[0] * np.exp(np.clip(p[1]*x_arr, -30, 30)) + p[2]
        else:             y = np.zeros_like(x_arr)
    return np.clip(y, -500, 500)


def equation_string(eq_idx: int, params: list) -> str:
    def s(v): return f"{v:+.2f}" if abs(v) >= 0.005 else "+0.00"  
    def r(v): return f"{v:.2f}"                                     

    p = params
    if eq_idx == 0: return f"y = {r(p[0])}x  {s(p[1])}"
    elif eq_idx == 1: return f"y = {r(p[0])}x² + {s(p[1])}x + {s(p[2])}"
    elif eq_idx == 2: return f"y = {r(p[0])}x³ {s(p[1])}x² {s(p[2])}x {s(p[3])}"
    elif eq_idx == 3: return f"y = {r(p[0])}·sin({r(p[1])}x {s(p[2])})"
    elif eq_idx == 4: return f"y = {r(p[0])}·cos({r(p[1])}x {s(p[2])})"
    elif eq_idx == 5: return f"y = {r(p[0])}·tan({r(p[1])}x {s(p[2])})"
    elif eq_idx == 6: return f"y = {r(p[0])}·|x {s(p[1])}|  {s(p[2])}"
    elif eq_idx == 7: return f"y = {r(p[0])}·e^({r(p[1])}x)  {s(p[2])}"
    return ""


# number of sample points along the true curve for scoring
N_SAMPLES = 150

def compute_score(drawn_pixels: list, eq_idx: int, params: list,
                  origin_x: int, origin_y: int, scale: float) -> float:
    """Score the user's drawing against the true curve.

    Sample the true curve at N_SAMPLES evenly-spaced x-values across the
    visible plot region.  For each sample point, find the closest drawn
    point (Euclidean distance in canvas pixels).  The mean of those minimum
    distances becomes the error metric — undrawn sections of the curve
    contribute a large distance each, so missing coverage is penalised."""

    if len(drawn_pixels) < 5:
        return 0.0

    # step 1: sample the TRUE curve at regular x-intervals across the plot region
    x_math = np.linspace(-PLOT_RANGE_X, PLOT_RANGE_X, N_SAMPLES)
    y_math = evaluate(eq_idx, x_math, params)

    # keep only finite samples that fit inside the visible vertical plot range
    valid = ~np.isnan(y_math) & ~np.isinf(y_math) & (np.abs(y_math) <= PLOT_RANGE_Y)
    x_math = x_math[valid]
    y_math = y_math[valid]

    if len(x_math) == 0:
        return 0.0

    # convert true curve samples to canvas pixel coordinates
    cx = origin_x + x_math * scale
    cy = origin_y - y_math * scale

    # step 2: for each true-curve sample, find the nearest drawn point
    # stack true samples as (N, 2) and drawn points as (M, 2)
    true_pts  = np.column_stack((cx, cy))                         # (N, 2)
    drawn_pts = np.array(drawn_pixels, dtype=float)               # (M, 2)

    # vectorised pairwise distance: diff[i, j] = true[i] - drawn[j]
    # reshape for broadcasting: (N, 1, 2) - (1, M, 2) → (N, M, 2)
    diff  = true_pts[:, np.newaxis, :] - drawn_pts[np.newaxis, :, :]
    dists = np.sqrt((diff ** 2).sum(axis=2))   # (N, M) euclidean distances

    # minimum distance from each true-curve sample to any drawn point
    min_dists = dists.min(axis=1)              # (N,)

    # step 3: convert mean distance to a 0–100 score
    # a mean distance of 0 px = perfect, ~50 px or more = 0%
    mean_dist = float(min_dists.mean())
    score = max(0.0, 100.0 * (1.0 - mean_dist / 50.0))

    return round(score, 1)


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