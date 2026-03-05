# =============================================================================
# renderer.py — Math Curve Explorer
# Stateless drawing utilities: grid and mathematical curve rendering.
# Every function takes a pygame.Surface and draws onto it.
# =============================================================================

import numpy as np
import pygame

import constants as C
from maths import evaluate, math_to_canvas


# -----------------------------------------------------------------------------
# Grid
# -----------------------------------------------------------------------------

# Pre-built font objects (created on first use, then reused)
_font_tick: pygame.font.Font | None = None
_font_axis: pygame.font.Font | None = None


def _get_fonts():
    global _font_tick, _font_axis
    if _font_tick is None:
        _font_tick = pygame.font.SysFont("consolas", 11)
        _font_axis = pygame.font.SysFont("consolas", 13, bold=True)
    return _font_tick, _font_axis


def draw_grid(surface: pygame.Surface,
              origin_x: int, origin_y: int, scale: float) -> None:
    """
    Draw a full Cartesian grid onto surface:
      • minor gridlines every 1 unit  (faint)
      • major gridlines every 2 units (slightly brighter)
      • bold x/y axes with arrowheads
      • numeric tick labels at every 2-unit mark
    """
    font_tick, font_axis = _get_fonts()

    # Minor gridlines
    for i in range(-C.GRID_RANGE * 2, C.GRID_RANGE * 2 + 1):
        px = int(origin_x + i * C.GRID_STEP * scale)
        if 0 <= px <= C.CANVAS_W:
            pygame.draw.line(surface, C.C_GRID_MINOR, (px, 0), (px, C.CANVAS_H), 1)
    for j in range(-C.GRID_RANGE * 2, C.GRID_RANGE * 2 + 1):
        py = int(origin_y - j * C.GRID_STEP * scale)
        if 0 <= py <= C.CANVAS_H:
            pygame.draw.line(surface, C.C_GRID_MINOR, (0, py), (C.CANVAS_W, py), 1)

    # Major gridlines
    for i in range(-C.GRID_RANGE, C.GRID_RANGE + 1):
        px = int(origin_x + i * 2 * scale)
        if 0 <= px <= C.CANVAS_W:
            pygame.draw.line(surface, C.C_GRID_MAJOR, (px, 0), (px, C.CANVAS_H), 1)
    for j in range(-C.GRID_RANGE, C.GRID_RANGE + 1):
        py = int(origin_y - j * 2 * scale)
        if 0 <= py <= C.CANVAS_H:
            pygame.draw.line(surface, C.C_GRID_MAJOR, (0, py), (C.CANVAS_W, py), 1)

    # Axes
    if 0 <= origin_y <= C.CANVAS_H:
        pygame.draw.line(surface, C.C_AXIS, (0, origin_y), (C.CANVAS_W, origin_y), 2)
    if 0 <= origin_x <= C.CANVAS_W:
        pygame.draw.line(surface, C.C_AXIS, (origin_x, 0), (origin_x, C.CANVAS_H), 2)

    # Arrowheads
    aw = 8
    pygame.draw.polygon(surface, C.C_AXIS, [
        (C.CANVAS_W - 4,      origin_y),
        (C.CANVAS_W - 4 - aw, origin_y - aw // 2),
        (C.CANVAS_W - 4 - aw, origin_y + aw // 2),
    ])
    pygame.draw.polygon(surface, C.C_AXIS, [
        (origin_x,           4),
        (origin_x - aw // 2, 4 + aw),
        (origin_x + aw // 2, 4 + aw),
    ])

    # Axis name labels
    surface.blit(font_axis.render("x", True, C.C_LABEL), (C.CANVAS_W - 18, origin_y - 18))
    surface.blit(font_axis.render("y", True, C.C_LABEL), (origin_x + 6, 4))

    # Tick labels  (every 2 units, skip 0)
    for i in range(-C.GRID_RANGE, C.GRID_RANGE + 1):
        xv = i * 2
        px = int(origin_x + xv * scale)
        if 15 < px < C.CANVAS_W - 15 and xv != 0:
            lbl = font_tick.render(str(xv), True, C.C_LABEL_DIM)
            surface.blit(lbl, (px - lbl.get_width() // 2, origin_y + 5))

    for j in range(-C.GRID_RANGE, C.GRID_RANGE + 1):
        yv = j * 2
        py = int(origin_y - yv * scale)
        if 15 < py < C.CANVAS_H - 15 and yv != 0:
            lbl = font_tick.render(str(yv), True, C.C_LABEL_DIM)
            surface.blit(lbl, (origin_x + 5, py - lbl.get_height() // 2))

    surface.blit(font_tick.render("0", True, C.C_LABEL_DIM), (origin_x + 4, origin_y + 4))


# -----------------------------------------------------------------------------
# Curve
# -----------------------------------------------------------------------------

def _clamp(pt: tuple) -> tuple:
    """Keep a point just inside drawable bounds so pygame never raises."""
    return (max(-5, min(C.CANVAS_W + 5, pt[0])),
            max(-5, min(C.CANVAS_H + 5, pt[1])))


def draw_curve(surface: pygame.Surface,
               eq_idx: int, params: list,
               origin_x: int, origin_y: int, scale: float,
               colour: tuple = None, glow: tuple = None,
               width: int = 2) -> None:
    """
    Sample the equation at 1 800 evenly-spaced x values, build continuous
    polyline segments (splitting at NaN gaps and large vertical jumps such
    as tan asymptotes), then draw each segment twice:
      1. Wide, dim glow pass   (gives the neon-light look)
      2. Narrow, bright pass   (the actual visible curve)
    """
    colour = colour or C.C_CURVE
    glow   = glow   or C.C_CURVE_GLOW

    x_arr = np.linspace(-C.GRID_RANGE - 1, C.GRID_RANGE + 1, 1800)
    y_arr = evaluate(eq_idx, x_arr, params)

    segments: list[list[tuple]] = []
    current:  list[tuple]       = []
    prev_py = None

    for x, y in zip(x_arr, y_arr):
        if np.isnan(y) or np.isinf(y):
            if len(current) > 1:
                segments.append(current)
            current = []
            prev_py = None
            continue

        px, py = math_to_canvas(x, y, origin_x, origin_y, scale)

        # Large vertical jump → discontinuity (e.g. tan asymptote crossing)
        if prev_py is not None and abs(py - prev_py) > C.CANVAS_H * 0.75:
            if len(current) > 1:
                segments.append(current)
            current = []
            prev_py = None

        current.append((px, py))
        prev_py = py

    if len(current) > 1:
        segments.append(current)

    for seg in segments:
        pts = [_clamp(p) for p in seg]
        if len(pts) > 1:
            pygame.draw.lines(surface, glow,   False, pts, 6)
            pygame.draw.lines(surface, colour, False, pts, width)
