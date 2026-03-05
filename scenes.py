# =============================================================================
# scenes.py — Math Curve Explorer
# All three game scenes in one file:
#
#   MenuScene      — animated landing screen, two mode-select cards
#   ExplorerScene  — real-time graphing with parameter sliders
#   ChallengeScene — freehand curve tracing + MSE score + AirCanvas
#
# Each scene follows the same protocol used by main.py:
#   scene.handle_event(event)  → called for every pygame event
#   scene.update(dt)           → called once per frame with delta-time
#   scene.draw(screen)         → called once per frame
#   scene.next_scene           → None to stay, or a string key to transition
# =============================================================================

import math
import random

import numpy as np
import pygame
import pygame_gui

import constants as C
from maths    import evaluate, equation_string, compute_score, score_colour, score_label
from renderer import draw_grid, draw_curve
from aircanvas import AirCanvasThread


# =============================================================================
# MenuScene
# =============================================================================

class MenuScene:
    """
    Animated landing screen.
    Two clickable cards let the user choose Explorer or Challenge mode.
    Sets next_scene to "explorer" or "challenge" on click.
    """

    # Card layout constants
    CARD_W   = 340
    CARD_H   = 190
    CARD_GAP = 60

    # Card definitions: title, subtitle, icon, accent colour, target scene key
    CARDS = [
        ("EXPLORER MODE",   "Adjust parameters — graph in real-time",
         "📈", C.C_CURVE,   "explorer"),
        ("CHALLENGE MODE",  "Trace curves — mouse or AirCanvas",
         "✏️", C.C_TARGET, "challenge"),
    ]

    def __init__(self, manager: pygame_gui.UIManager) -> None:
        self.next_scene: str | None = None
        self._manager   = manager
        self._t         = 0.0   # animation clock (seconds)
        self._stars     = [_Star() for _ in range(180)]

        # Fonts (created once, reused every frame)
        self._f_title    = pygame.font.SysFont("consolas", 38, bold=True)
        self._f_byline   = pygame.font.SysFont("consolas", 14)
        self._f_icon     = pygame.font.SysFont("segoe ui emoji", 42)
        self._f_card_t   = pygame.font.SysFont("consolas", 20, bold=True)
        self._f_card_sub = pygame.font.SysFont("consolas", 13)
        self._f_hint     = pygame.font.SysFont("consolas", 12)

    # ── Scene protocol ────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, (_, _, _, _, key) in enumerate(self.CARDS):
                if self._card_rect(i).collidepoint(event.pos):
                    self.next_scene = key

    def update(self, dt: float) -> None:
        self._t += dt * 0.85
        for star in self._stars:
            star.update()

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(C.C_BG)
        self._draw_background_curves(screen)

        for star in self._stars:
            star.draw(screen)

        cx = C.WINDOW_W // 2

        # Decorative horizontal rules
        pygame.draw.line(screen, C.C_SEP, (cx - 290, 128), (cx + 290, 128), 1)
        pygame.draw.line(screen, C.C_SEP,
                         (cx - 290, C.WINDOW_H - 58), (cx + 290, C.WINDOW_H - 58), 1)

        # Title
        title_s = self._f_title.render("MATH CURVE EXPLORER", True, C.C_TITLE)
        screen.blit(title_s, (cx - title_s.get_width() // 2, 50))

        # Byline
        byline_s = self._f_byline.render(
            "IB Computer Science  ·  Internal Assessment  ·  Python / Pygame",
            True, C.C_LABEL_DIM)
        screen.blit(byline_s, (cx - byline_s.get_width() // 2, 98))

        # Cards
        mouse = pygame.mouse.get_pos()
        for i, (title, sub, icon, accent, _) in enumerate(self.CARDS):
            self._draw_card(screen, i, title, sub, icon, accent,
                            self._card_rect(i).collidepoint(mouse))

        # Hint
        hint_s = self._f_hint.render(
            "Select a mode above   ·   ESC to quit", True, C.C_LABEL_DIM)
        screen.blit(hint_s, (cx - hint_s.get_width() // 2, C.WINDOW_H - 38))

    # ── Private helpers ───────────────────────────────────────────────────────

    def _card_rect(self, index: int) -> pygame.Rect:
        total = self.CARD_W * 2 + self.CARD_GAP
        x0    = (C.WINDOW_W - total) // 2
        x     = x0 + index * (self.CARD_W + self.CARD_GAP)
        y     = C.WINDOW_H // 2 - self.CARD_H // 2 + 30
        return pygame.Rect(x, y, self.CARD_W, self.CARD_H)

    def _draw_card(self, screen, index, title, subtitle, icon, accent, hovered):
        rect = self._card_rect(index)

        if hovered:
            glow = pygame.Surface((self.CARD_W + 28, self.CARD_H + 28), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*accent, 28), glow.get_rect(), border_radius=18)
            screen.blit(glow, (rect.x - 14, rect.y - 14))

        bg  = (26, 30, 52) if hovered else (20, 24, 42)
        bdr = accent        if hovered else (50, 58, 96)
        pygame.draw.rect(screen, bg,  rect, border_radius=12)
        pygame.draw.rect(screen, bdr, rect, 2 if hovered else 1, border_radius=12)

        for surf, y_off in [
            (self._f_icon.render(icon, True, accent),        22),
            (self._f_card_t.render(title, True, C.C_TITLE),  88),
            (self._f_card_sub.render(subtitle, True, C.C_LABEL_DIM), 116),
        ]:
            screen.blit(surf, (rect.x + (self.CARD_W - surf.get_width()) // 2,
                                rect.y + y_off))

        if hovered:
            enter = self._f_card_sub.render("→  Click to enter", True, accent)
            screen.blit(enter, (rect.x + (self.CARD_W - enter.get_width()) // 2,
                                 rect.y + 152))

    def _draw_background_curves(self, screen):
        """Three slow animated sine waves give the menu visual depth."""
        layers = [
            (60,  0.008, 0.0, -120, C.C_CURVE,  16),
            (45,  0.012, 1.2,    0, C.C_TARGET, 12),
            (75,  0.005, 2.5,  120, C.C_ACCENT, 10),
        ]
        for amp, freq, phase, y_off, colour, alpha in layers:
            pts = [
                (px, int(C.WINDOW_H // 2 + y_off
                         + amp * math.sin(freq * px + self._t + phase)))
                for px in range(0, C.WINDOW_W + 2, 3)
            ]
            overlay = pygame.Surface((C.WINDOW_W, C.WINDOW_H), pygame.SRCALPHA)
            pygame.draw.lines(overlay, (*colour, alpha), False, pts, 2)
            screen.blit(overlay, (0, 0))


# =============================================================================
# ExplorerScene
# =============================================================================

class ExplorerScene:
    """
    Explorer Mode: choose an equation family, drag sliders, watch the curve
    update live on a Cartesian grid.
    """

    SLIDER_TOP    = 290   # y of the first slider row
    SLIDER_ROW_H  = 58    # vertical spacing between rows

    def __init__(self, manager: pygame_gui.UIManager) -> None:
        self.next_scene: str | None = None
        self._manager   = manager

        # Canvas geometry (same for both graph scenes)
        self._ox    = C.CANVAS_W // 2                         # origin x (pixels)
        self._oy    = C.CANVAS_H // 2                         # origin y (pixels)
        self._scale = C.CANVAS_H / (C.GRID_RANGE * 2 + 2)    # pixels per unit
        self._panel = pygame.Rect(C.CANVAS_W, 0, C.PANEL_W, C.WINDOW_H)

        # Off-screen surface for the grid + curve (redrawn only on change)
        self._canvas    = pygame.Surface((C.CANVAS_W, C.CANVAS_H))
        self._dirty     = True    # True → rebuild _canvas this frame

        # Equation state
        self._eq_idx = 0
        self._params: list[float] = []

        # pygame_gui widgets
        self._dropdown = pygame_gui.elements.UIDropDownMenu(
            options_list=C.EQUATIONS,
            starting_option=C.EQUATIONS[0],
            relative_rect=pygame.Rect(C.CANVAS_W + 14, 88, C.PANEL_W - 28, 34),
            manager=manager)

        self._btn_reset = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(C.CANVAS_W + 14, C.WINDOW_H - 98,
                                      C.PANEL_W - 28, 38),
            text="↺  Reset Parameters",
            manager=manager)

        self._btn_back = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(C.CANVAS_W + 14, C.WINDOW_H - 52,
                                      C.PANEL_W - 28, 36),
            text="← Main Menu",
            manager=manager)

        # Slider widgets (rebuilt whenever the equation changes)
        self._sliders:    list = []
        self._lbl_names:  list = []
        self._lbl_values: list = []
        self._build_sliders(self._eq_idx)

        # Fonts
        self._f_title = pygame.font.SysFont("consolas", 19, bold=True)
        self._f_mode  = pygame.font.SysFont("consolas", 13)
        self._f_sub   = pygame.font.SysFont("consolas", 13)
        self._f_eq    = pygame.font.SysFont("consolas", 14, bold=True)
        self._f_hint  = pygame.font.SysFont("consolas", 12)

    def on_enter(self) -> None:
        """Called by main.py whenever this scene becomes active."""
        self._show_widgets(True)
        self._dirty = True

    def on_exit(self) -> None:
        """Called by main.py just before switching away from this scene."""
        self._show_widgets(False)

    # ── Scene protocol ────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element is self._btn_back:
                self.next_scene = "menu"
            elif event.ui_element is self._btn_reset:
                self._build_sliders(self._eq_idx)
                self._dirty = True

        elif (event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED
              and event.ui_element is self._dropdown):
            self._eq_idx = C.EQUATIONS.index(event.text)
            self._build_sliders(self._eq_idx)
            self._dirty = True

        else:
            # Check all sliders for a value change
            if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                for i, sl in enumerate(self._sliders):
                    if event.ui_element is sl:
                        self._params[i] = sl.get_current_value()
                        self._lbl_values[i].set_text(f"= {self._params[i]:.2f}")
                        self._dirty = True
                        break

    def update(self, dt: float) -> None:
        if self._dirty:
            self._rebuild_canvas()
            self._dirty = False

    def draw(self, screen: pygame.Surface) -> None:
        screen.blit(self._canvas, (0, 0))
        self._draw_panel(screen)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_sliders(self, eq_idx: int) -> None:
        """Destroy old sliders and create fresh ones for eq_idx."""
        for el in self._sliders + self._lbl_names + self._lbl_values:
            el.kill()
        self._sliders.clear()
        self._lbl_names.clear()
        self._lbl_values.clear()
        self._params.clear()

        px = self._panel.x
        pw = self._panel.width

        for i, (name, lo, hi, default) in enumerate(C.PARAM_CONFIGS[eq_idx]):
            y = self.SLIDER_TOP + i * self.SLIDER_ROW_H

            self._lbl_names.append(pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(px + 14, y, 28, 20),
                text=name, manager=self._manager))

            sl = pygame_gui.elements.UIHorizontalSlider(
                relative_rect=pygame.Rect(px + 14, y + 22, pw - 28, 22),
                start_value=default, value_range=(lo, hi),
                manager=self._manager)
            self._sliders.append(sl)

            self._lbl_values.append(pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(px + 46, y, 90, 20),
                text=f"= {default:.2f}", manager=self._manager))

            self._params.append(default)

    def _rebuild_canvas(self) -> None:
        self._canvas.fill(C.C_BG)
        draw_grid(self._canvas, self._ox, self._oy, self._scale)
        draw_curve(self._canvas, self._eq_idx, self._params,
                   self._ox, self._oy, self._scale)

    def _show_widgets(self, visible: bool) -> None:
        toggle = (lambda el: el.show()) if visible else (lambda el: el.hide())
        for el in ([self._dropdown, self._btn_reset, self._btn_back]
                   + self._sliders + self._lbl_names + self._lbl_values):
            toggle(el)

    def _draw_panel(self, screen: pygame.Surface) -> None:
        px, pw = self._panel.x, self._panel.width

        pygame.draw.rect(screen, C.C_PANEL_BG, self._panel)
        pygame.draw.line(screen, C.C_BORDER, (px, 0), (px, C.WINDOW_H), 2)

        def blit_centred(surf, y):
            screen.blit(surf, (px + (pw - surf.get_width()) // 2, y))

        def sep(y):
            pygame.draw.line(screen, C.C_SEP, (px + 8, y), (px + pw - 8, y), 1)

        blit_centred(self._f_title.render("MATH EXPLORER",    True, C.C_TITLE),  18)
        blit_centred(self._f_mode.render("[ EXPLORER MODE ]", True, C.C_ACCENT), 42)
        sep(64)

        screen.blit(self._f_sub.render("Equation Type:", True, C.C_LABEL), (px + 14, 68))

        sep(130)
        screen.blit(self._f_sub.render("Live equation:", True, C.C_LABEL), (px + 14, 138))

        eq_str  = equation_string(self._eq_idx, self._params)
        eq_surf = self._f_eq.render(eq_str, True, C.C_CURVE)
        if eq_surf.get_width() > pw - 28:
            mid = len(eq_str) // 2
            screen.blit(self._f_eq.render(eq_str[:mid], True, C.C_CURVE), (px + 14, 158))
            screen.blit(self._f_eq.render(eq_str[mid:], True, C.C_CURVE), (px + 14, 176))
        else:
            screen.blit(eq_surf, (px + 14, 158))

        sep(198)
        screen.blit(self._f_sub.render("Parameters:", True, C.C_LABEL), (px + 14, 206))

        screen.blit(self._f_hint.render("Drag sliders to explore",
                                         True, C.C_LABEL_DIM), (px + 14, C.WINDOW_H - 118))
        screen.blit(self._f_hint.render("ESC  /  ← Main Menu",
                                         True, C.C_LABEL_DIM), (px + 14, C.WINDOW_H - 100))


# =============================================================================
# ChallengeScene
# =============================================================================

class ChallengeScene:
    """
    Challenge Mode: the user traces a displayed target curve freehand.
    Supports mouse drawing and AirCanvas (webcam + MediaPipe finger tracking).
    A Mean Squared Error score is computed on demand.
    """

    def __init__(self, manager: pygame_gui.UIManager) -> None:
        self.next_scene: str | None = None
        self._manager   = manager

        # Canvas geometry
        self._ox    = C.CANVAS_W // 2
        self._oy    = C.CANVAS_H // 2
        self._scale = C.CANVAS_H / (C.GRID_RANGE * 2 + 2)
        self._panel = pygame.Rect(C.CANVAS_W, 0, C.PANEL_W, C.WINDOW_H)

        # Surfaces
        self._canvas     = pygame.Surface((C.CANVAS_W, C.CANVAS_H))
        self._draw_surf  = pygame.Surface((C.CANVAS_W, C.CANVAS_H), pygame.SRCALPHA)
        self._canvas_dirty = True

        # Challenge state
        self._ch_eq, self._ch_params, self._ch_label = C.CHALLENGE_PRESETS[0]
        self._drawn:   list[tuple] = []
        self._drawing  = False
        self._scored   = False
        self._score    = 0.0
        self._show_true = False

        # AirCanvas state
        self._air_on     = False
        self._air_thread: AirCanvasThread | None = None
        self._air_prev:   tuple | None = None

        # AirCanvas cursor sprite
        self._cursor = pygame.Surface((18, 18), pygame.SRCALPHA)
        pygame.draw.circle(self._cursor, (*C.C_AIR, 200), (9, 9), 9, 2)
        pygame.draw.circle(self._cursor, (*C.C_AIR, 255), (9, 9), 3)

        # pygame_gui widgets
        W  = C.PANEL_W - 28
        HW = (C.PANEL_W - 32) // 2     # half-width for side-by-side buttons
        bx = C.CANVAS_W + 14

        self._btn_new   = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(bx, 68, W, 34),
            text="⟳  New Challenge", manager=manager)
        self._btn_clear = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(bx, 110, HW, 32),
            text="✕  Clear", manager=manager)
        self._btn_score = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(bx + HW + 4, 110, HW, 32),
            text="✓  Score", manager=manager)
        self._btn_true  = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(bx, 150, W, 32),
            text="👁  Show / Hide True Curve", manager=manager)
        self._btn_air   = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(bx, 190, W, 34),
            text="✋  AirCanvas  (Webcam)", manager=manager)
        self._btn_back  = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(bx, C.WINDOW_H - 52, W, 36),
            text="← Main Menu", manager=manager)

        # Fonts
        self._f_title     = pygame.font.SysFont("consolas", 19, bold=True)
        self._f_mode      = pygame.font.SysFont("consolas", 13)
        self._f_sub       = pygame.font.SysFont("consolas", 13)
        self._f_sub_b     = pygame.font.SysFont("consolas", 13, bold=True)
        self._f_eq        = pygame.font.SysFont("consolas", 14, bold=True)
        self._f_score     = pygame.font.SysFont("consolas", 38, bold=True)
        self._f_score_lbl = pygame.font.SysFont("consolas", 16, bold=True)
        self._f_hint      = pygame.font.SysFont("consolas", 12)

    def on_enter(self) -> None:
        self._show_widgets(True)
        self._canvas_dirty = True

    def on_exit(self) -> None:
        self._show_widgets(False)
        self._stop_air()

    # ── Scene protocol ────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            self._handle_button(event.ui_element)

        # Mouse drawing  (only when AirCanvas is off)
        elif not self._air_on:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if event.pos[0] < C.CANVAS_W:
                    self._drawing = True
                    self._scored  = False
                    self._drawn.append(event.pos)

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._drawing = False

            elif event.type == pygame.MOUSEMOTION and self._drawing:
                mx, my = event.pos
                if mx < C.CANVAS_W and self._drawn:
                    self._draw_stroke(self._drawn[-1], (mx, my))
                    self._drawn.append((mx, my))

    def update(self, dt: float) -> None:
        # Pull latest AirCanvas point
        if self._air_on and self._air_thread and self._air_thread.ready:
            pt = self._air_thread.point
            if pt:
                if self._air_prev:
                    self._draw_stroke(self._air_prev, pt,
                                      glow=C.C_AIR_GLOW, line=C.C_AIR)
                    self._drawn.append(pt)
                self._air_prev = pt
            else:
                self._air_prev = None

        if self._canvas_dirty:
            self._rebuild_canvas()
            self._canvas_dirty = False

    def draw(self, screen: pygame.Surface) -> None:
        screen.blit(self._canvas,    (0, 0))
        screen.blit(self._draw_surf, (0, 0))
        self._draw_air_overlay(screen)
        self._draw_panel(screen)

    # ── Button handler ────────────────────────────────────────────────────────

    def _handle_button(self, btn) -> None:
        if btn is self._btn_back:
            self.next_scene = "menu"

        elif btn is self._btn_new:
            self._ch_eq, self._ch_params, self._ch_label = random.choice(
                C.CHALLENGE_PRESETS)
            self._reset_drawing()
            self._canvas_dirty = True

        elif btn is self._btn_clear:
            self._reset_drawing()

        elif btn is self._btn_score:
            if self._drawn:
                self._score = compute_score(
                    self._drawn, self._ch_eq, self._ch_params,
                    self._ox, self._oy, self._scale)
                self._scored     = True
                self._show_true  = True
                self._canvas_dirty = True

        elif btn is self._btn_true:
            self._show_true    = not self._show_true
            self._canvas_dirty = True

        elif btn is self._btn_air:
            if not self._air_on:
                self._air_thread = AirCanvasThread()
                self._air_thread.start()
                self._air_on = True
            else:
                self._stop_air()

    # ── Drawing helpers ───────────────────────────────────────────────────────

    def _draw_stroke(self, p1, p2,
                     glow=C.C_DRAWN_GLOW, line=C.C_DRAWN) -> None:
        """Draw one segment of a freehand stroke onto the draw surface."""
        pygame.draw.line(self._draw_surf, (*glow, 150), p1, p2, 7)
        pygame.draw.line(self._draw_surf, (*line, 210), p1, p2, 3)

    def _reset_drawing(self) -> None:
        self._drawn.clear()
        self._drawing  = False
        self._scored   = False
        self._score    = 0.0
        self._air_prev = None
        self._draw_surf.fill((0, 0, 0, 0))

    def _stop_air(self) -> None:
        if self._air_thread:
            self._air_thread.stop()
            self._air_thread = None
        self._air_on   = False
        self._air_prev = None

    def _rebuild_canvas(self) -> None:
        self._canvas.fill(C.C_BG)
        draw_grid(self._canvas, self._ox, self._oy, self._scale)
        if self._show_true:
            draw_curve(self._canvas, self._ch_eq, self._ch_params,
                       self._ox, self._oy, self._scale,
                       colour=C.C_TARGET, glow=C.C_TARGET_GLOW)

    def _draw_air_overlay(self, screen: pygame.Surface) -> None:
        """Cursor dot and status text drawn directly on the screen (top layer)."""
        if not self._air_on:
            return
        t = self._air_thread
        pt = t.point if (t and t.ready) else None

        if pt:
            screen.blit(self._cursor, (pt[0] - 9, pt[1] - 9))
            screen.blit(self._f_hint.render("● TRACKING", True, C.C_AIR), (8, 8))
        elif t and t.ready:
            screen.blit(self._f_hint.render("◌  No hand detected",
                                             True, C.C_LABEL_DIM), (8, 8))
        elif t and t.error_msg:
            screen.blit(self._f_hint.render(t.error_msg[:56], True, C.C_RED), (8, 8))
        else:
            screen.blit(self._f_hint.render("Initialising webcam…",
                                             True, C.C_LABEL_DIM), (8, 8))

    # ── Panel renderer ────────────────────────────────────────────────────────

    def _draw_panel(self, screen: pygame.Surface) -> None:
        px, pw = self._panel.x, self._panel.width

        pygame.draw.rect(screen, C.C_PANEL_BG, self._panel)
        pygame.draw.line(screen, C.C_BORDER, (px, 0), (px, C.WINDOW_H), 2)

        def blit_c(surf, y):   # centre-align in panel
            screen.blit(surf, (px + (pw - surf.get_width()) // 2, y))

        def sep(y):
            pygame.draw.line(screen, C.C_SEP, (px + 8, y), (px + pw - 8, y), 1)

        blit_c(self._f_title.render("MATH EXPLORER",     True, C.C_TITLE),   18)
        blit_c(self._f_mode.render("[ CHALLENGE MODE ]", True, C.C_TARGET),  42)
        sep(64)

        # Target equation
        sep(228)
        screen.blit(self._f_sub_b.render("Target equation:", True, C.C_LABEL),
                    (px + 14, 236))
        blit_c(self._f_eq.render(self._ch_label, True, C.C_TARGET), 256)
        sep(280)

        # Input mode
        inp_label  = "✋  AirCanvas" if self._air_on else "🖱   Mouse"
        inp_colour = C.C_AIR        if self._air_on else C.C_LABEL
        screen.blit(self._f_sub_b.render(f"Input: {inp_label}", True, inp_colour),
                    (px + 14, 288))

        if self._air_on:
            t      = self._air_thread
            status = ("Raise index finger → draw" if (t and t.ready)
                      else t.error_msg[:36]        if (t and t.error_msg)
                      else "Initialising webcam…")
            col    = C.C_RED if (t and t.error_msg and not t.ready) else C.C_LABEL_DIM
            screen.blit(self._f_hint.render(status, True, col), (px + 14, 308))
        else:
            screen.blit(self._f_hint.render("Click and drag on the grid",
                                             True, C.C_LABEL_DIM), (px + 14, 308))

        sep(328)
        screen.blit(self._f_sub.render(f"Points drawn: {len(self._drawn)}",
                                        True, C.C_LABEL), (px + 14, 336))

        # Score box
        if self._scored:
            box = pygame.Rect(px + 12, 362, pw - 24, 130)
            pygame.draw.rect(screen, C.C_SCORE_BG, box, border_radius=8)
            pygame.draw.rect(screen, score_colour(self._score), box, 2, border_radius=8)

            blit_c(self._f_score.render(f"{self._score:.1f}%",
                                         True, score_colour(self._score)), 374)
            blit_c(self._f_score_lbl.render(score_label(self._score),
                                             True, score_colour(self._score)), 420)
            blit_c(self._f_hint.render("Metric: Mean Squared Error",
                                        True, C.C_LABEL_DIM), 448)
            sep(502)
        else:
            screen.blit(self._f_sub.render("Score:  —  (press Score)",
                                            True, C.C_LABEL_DIM), (px + 14, 362))

        # Colour legend
        leg_y = 510 if self._scored else 388
        pygame.draw.line(screen, C.C_TARGET,
                         (px + 14, leg_y + 7), (px + 44, leg_y + 7), 2)
        screen.blit(self._f_hint.render("True curve",  True, C.C_LABEL_DIM), (px + 50, leg_y))

        d_col = C.C_AIR if self._air_on else C.C_DRAWN
        pygame.draw.line(screen, d_col,
                         (px + 14, leg_y + 22), (px + 44, leg_y + 22), 2)
        screen.blit(self._f_hint.render("Your drawing", True, C.C_LABEL_DIM),
                    (px + 50, leg_y + 14))

        # Bottom hints
        for i, hint in enumerate(["[Score] to evaluate",
                                   "[Clear] to redraw",
                                   "ESC  /  ← Main Menu"]):
            screen.blit(self._f_hint.render(hint, True, C.C_LABEL_DIM),
                        (px + 14, C.WINDOW_H - 72 + i * 18))

    def _show_widgets(self, visible: bool) -> None:
        toggle = (lambda el: el.show()) if visible else (lambda el: el.hide())
        for el in [self._btn_new, self._btn_clear, self._btn_score,
                   self._btn_true, self._btn_air, self._btn_back]:
            toggle(el)


# =============================================================================
# _Star  (private helper used only by MenuScene)
# =============================================================================

class _Star:
    """A single drifting star particle for the menu's animated starfield."""

    def __init__(self) -> None:
        self._respawn(initial=True)

    def _respawn(self, initial: bool = False) -> None:
        self.x      = random.uniform(0, C.WINDOW_W)
        self.y      = random.uniform(0, C.WINDOW_H) if initial else C.WINDOW_H + 4
        self.speed  = random.uniform(0.15, 0.55)
        self.drift  = random.uniform(-0.06, 0.06)
        self.radius = random.uniform(0.5, 2.2)

    def update(self) -> None:
        self.y -= self.speed
        self.x += self.drift
        if self.y < -4 or self.x < -4 or self.x > C.WINDOW_W + 4:
            self._respawn()

    def draw(self, surface: pygame.Surface) -> None:
        t   = self.radius / 2.2
        col = (int(150 + 80*t), int(160 + 70*t), int(210 + 40*t))
        pygame.draw.circle(surface, col,
                           (int(self.x), int(self.y)), max(1, int(self.radius)))
