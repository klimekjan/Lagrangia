import pygame
import os

pygame.init()

monitor_info = pygame.display.Info()
WINDOW_W = monitor_info.current_w
WINDOW_H = monitor_info.current_h
PANEL_W   = 320
CANVAS_W  = WINDOW_W - PANEL_W
CANVAS_H  = WINDOW_H

# gridlines extend across the whole canvas; PLOT_RANGE defines where curves live
GRID_RANGE   = 20      # gridlines drawn from -30 to +30 (covers any canvas aspect)
GRID_STEP    = 1       # minor gridline every 1 unit
PLOT_RANGE_X = 20     # curves and drawing constrained horizontally to ±16
PLOT_RANGE_Y = 14     # ... and vertically to ±10
FPS          = 60

#file paths 
BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")

# backgrounds
C_BG           = ( 10,  12,  22)
C_PANEL_BG     = ( 16,  18,  32)
C_SCORE_BG     = ( 14,  18,  34)

# grid
C_GRID_MINOR   = ( 25,  29,  50)
C_GRID_MAJOR   = ( 45,  52,  85)
C_AXIS         = ( 90, 100, 150)

# curves
C_CURVE        = ( 70, 190, 255)   # explorer curve  (cyan)
C_CURVE_GLOW   = ( 25,  80, 130)
C_TARGET       = (255,  90, 130)   # challenge target (pink)
C_TARGET_GLOW  = (120,  20,  50)
C_DRAWN        = ( 80, 255, 160)   # mouse stroke     (green)
C_DRAWN_GLOW   = ( 20, 100,  55)
C_AIR          = (255, 210,  60)   # AirCanvas stroke (amber)
C_AIR_GLOW     = (120,  80,   0)

C_TITLE        = (240, 245, 255)
C_LABEL        = (170, 182, 215)
C_LABEL_DIM    = ( 65,  75, 110)
C_ACCENT       = (255, 160,  55)   
C_SEP          = ( 38,  44,  72)   
C_BORDER       = ( 40,  46,  78)   

# score bands
C_GREEN        = (100, 255, 140)   # ≥ 85
C_YELLOW       = (255, 220,  60)   # 60–84
C_RED          = (255,  80, 100)   # < 60

#theme used by manager in SceneManager class
UI_THEME = {
    "button": {
        "colours": {
            "normal_bg":      "#141828",
            "hovered_bg":     "#222b50",
            "active_bg":      "#2e3d6e",
            "normal_border":  "#323a66",
            "hovered_border": "#5060a0",
            "normal_text":    "#a8b4d8",
            "hovered_text":   "#ffffff",
        },
        "font": {"name": "consolas", "size": "14", "bold": "1"},
        "misc": {"border_width": "1", "border_radius": "4"},
    },
    "drop_down_menu": {
        "colours": {
            "normal_bg":     "#0e1120",
            "hovered_bg":    "#1a2040",
            "normal_border": "#323a66",
            "normal_text":   "#a8b4d8",
            "hovered_text":  "#ffffff",
        },
    },
    "label": {
        "colours": {"normal_text": "#7a86b0"},
        "font":    {"name": "consolas", "size": "13"},
    },
    "horizontal_slider": {
        "colours": {
            "normal_bg":    "#0e1120",
            "hovered_bg":   "#1a2040",
            "normal_border":"#323a66",
            "filled_bar":   "#46c0f0",
            "unfilled_bar": "#1a2040",
        },
        "misc": {"border_radius": "8"},
    },
}


#equations in explorer mode
EQUATIONS = [
    "Linear",        #0   y = ax + b
    "Parabola",      #1   y = ax² + bx + c
    "Cubic",         #2   y = ax³ + bx² + cx + d
    "Sine",          #3   y = a·sin(bx + c)
    "Cosine",        #4   y = a·cos(bx + c)
    "Tangent",       #5   y = a·tan(bx + c)
    "Abs Value",     #6   y = a|x + b| + c
    "Exponential",   #7   y = a·e^(bx) + c
]

PARAM_CONFIGS = {
    0: [("a", -5.0,  5.0,  1.0), ("b", -5.0, 5.0, 0.0)],
    1: [("a", -3.0,  3.0,  1.0), ("b", -5.0, 5.0, 0.0), ("c", -5.0,  5.0,  0.0)],
    2: [("a", -2.0,  2.0,  0.3), ("b", -3.0, 3.0, 0.0),
        ("c", -5.0,  5.0,  0.0), ("d", -5.0, 5.0, 0.0)],
    3: [("a", -5.0,  5.0,  1.0), ("b", -4.0, 4.0, 1.0), ("c", -3.14, 3.14, 0.0)],
    4: [("a", -5.0,  5.0,  1.0), ("b", -4.0, 4.0, 1.0), ("c", -3.14, 3.14, 0.0)],
    5: [("a", -3.0,  3.0,  1.0), ("b", -2.0, 2.0, 0.8), ("c", -1.5,  1.5,  0.0)],
    6: [("a", -5.0,  5.0,  1.0), ("b", -5.0, 5.0, 0.0), ("c", -5.0,  5.0,  0.0)],
    7: [("a", -3.0,  3.0,  1.0), ("b", -2.0, 2.0, 0.3), ("c", -5.0,  5.0,  0.0)],
}

# challenge (needs to be updated so it takes random functions)
CHALLENGE_PRESETS = [
    (0, [ 1.0,  0.0,  0.0      ], "y = x²"),
    (0, [ 0.5,  0.0, -2.0      ], "y = 0.5x² - 2"),
    (0, [-1.0,  2.0,  1.0      ], "y = -x² + 2x + 1"),
    (1, [ 2.0,  1.0,  0.0      ], "y = 2·sin(x)"),
    (1, [ 1.0,  2.0,  0.0      ], "y = sin(2x)"),
    (2, [ 1.5,  1.0,  0.0      ], "y = 1.5·cos(x)"),
    (3, [ 0.2,  0.0,  0.0, 0.0 ], "y = 0.2x³"),
    (3, [ 0.3, -1.0,  0.0, 0.0 ], "y = 0.3x³ - x²"),
    (4, [ 2.0, -1.0             ], "y = 2x - 1"),
    (4, [-1.5,  3.0             ], "y = -1.5x + 3"),
    (6, [ 1.0,  0.0,  0.0      ], "y = |x|"),
    (6, [ 1.0, -2.0,  1.0      ], "y = |x - 2| + 1"),
    (7, [ 1.0,  0.4,  0.0      ], "y = e^(0.4x)"),
]