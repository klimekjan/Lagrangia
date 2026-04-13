import os
import random
from collections import deque

import numpy as np
import pygame
import pygame_gui

import constants as C
from maths import equation_string, compute_score, score_colour, score_label
from renderer import draw_grid, draw_curve
from aircanvas import AirCanvasThread


def _random_challenge():
    eq_idx = random.randint(0, len(C.EQUATIONS) - 1)
    params = []
    for _, lo, hi, _ in C.PARAM_CONFIGS[eq_idx]:
        raw = random.uniform(lo, hi)
        params.append(round(raw, 2))
    if eq_idx in (3, 4):
        if abs(params[1]) < 0.3:
            params[1] = random.choice([-1.0, 1.0]) * round(random.uniform(0.5, 2.0), 2)
    if eq_idx == 5:
        if abs(params[1]) < 0.3:
            params[1] = random.choice([-1.0, 1.0]) * round(random.uniform(0.4, 1.5), 2)
    label = equation_string(eq_idx, params)
    return eq_idx, params, label


def _catmull_rom(p0, p1, p2, p3, n_points: int = 8):
    """Generate n_points along the Catmull-Rom spline segment between p1 and p2,
    using p0 and p3 as outer control points for curvature.

    Returns a list of (int, int) pixel positions.  At 30 fps input this turns
    ~30 sparse camera samples/sec into ~240 smooth sub-points/sec, which is
    enough to capture tight cosine waves and other narrow curves."""

    points = []
    for i in range(1, n_points + 1):
        t  = i / n_points
        t2 = t * t
        t3 = t2 * t

        # Catmull-Rom basis matrix applied to each axis
        x = 0.5 * ((2 * p1[0]) +
                    (-p0[0] + p2[0]) * t +
                    (2*p0[0] - 5*p1[0] + 4*p2[0] - p3[0]) * t2 +
                    (-p0[0] + 3*p1[0] - 3*p2[0] + p3[0]) * t3)

        y = 0.5 * ((2 * p1[1]) +
                    (-p0[1] + p2[1]) * t +
                    (2*p0[1] - 5*p1[1] + 4*p2[1] - p3[1]) * t2 +
                    (-p0[1] + 3*p1[1] - 3*p2[1] + p3[1]) * t3)

        points.append((int(x), int(y)))
    return points


class MenuScene():

    CARD_W   = 340
    CARD_H   = 190 # card dimenstions
    CARD_GAP = 60

    CARDS = [
        ("EXPLORER MODE", "", C.C_CURVE,  "explorer"),
        ("CHALLENGE MODE", "", C.C_TARGET, "challenge"),
    ]

    def __init__(self, manager: pygame_gui.UIManager):
        self.next_scene: str | None = None

        bg_path = os.path.join(C.ASSETS_DIR, "menu_background.png")
        raw = pygame.image.load(bg_path).convert()
        self._bg = pygame.transform.smoothscale(raw, (C.WINDOW_W, C.WINDOW_H))

        self._f_title    = pygame.font.Font(os.path.join(C.FONTS_DIR, "Orbitron-Bold.ttf"), 70)
        self._f_card_t   = pygame.font.Font(os.path.join(C.FONTS_DIR, "Exo2-SemiBold.ttf"), 30)
        self._f_card_sub = pygame.font.Font(os.path.join(C.FONTS_DIR, "Exo2-SemiBold.ttf"), 15)
        self._f_hint     = pygame.font.SysFont("consolas", 12)

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # checking if left - click
            for i, (_, _, _, key) in enumerate(self.CARDS):
                if self._card_rect(i).collidepoint(event.pos):  # reassigning next_scene to a key of clicked card
                    self.next_scene = key

    def _card_rect(self, index: int) -> pygame.Rect:  # calcualting rectangle of a card
        total = self.CARD_W * 2 + self.CARD_GAP
        x0    = (C.WINDOW_W - total) // 2
        x     = x0 + index * (self.CARD_W + self.CARD_GAP)
        y     = C.WINDOW_H // 2 - self.CARD_H // 2 + 30
        return pygame.Rect(x, y, self.CARD_W, self.CARD_H)

    def update(self, dt: float):    # no need to update anything
        pass

    def draw(self, screen: pygame.Surface):  # drawing the menu screen

        screen.blit(self._bg, (0, 0))   # setting background

        cx = C.WINDOW_W // 2

        title_s = self._f_title.render("LAGRANGIA", True, C.C_TITLE)   #title
        screen.blit(title_s, (cx - title_s.get_width() // 2, 60))

        mouse = pygame.mouse.get_pos()
        for i, (title, sub, accent, _) in enumerate(self.CARDS):   # calling draw_card function
            self._draw_card(screen, i, title, sub, accent,
                            self._card_rect(i).collidepoint(mouse))


    def _draw_card(self, screen, index, title, subtitle, accent, hovered):
        rect = self._card_rect(index)

        bg  = (26, 30, 52) if hovered else C.C_PANEL_BG
        bdr = accent        if hovered else (50, 58, 96)
        pygame.draw.rect(screen, bg,  rect, border_radius=12)
        pygame.draw.rect(screen, bdr, rect, 2 if hovered else 1, border_radius=12)

        pygame.draw.line(screen, C.C_SEP,
                         (rect.x + 20, rect.y + 108), (rect.right - 20, rect.y + 108), 1)

        title_s = self._f_card_t.render(title, True, C.C_TITLE)
        screen.blit(title_s, (rect.x + (self.CARD_W - title_s.get_width()) // 2, rect.y + 60))

        if hovered:
            enter = self._f_card_sub.render("Click to enter", True, accent)
            screen.blit(enter, (rect.x + (self.CARD_W - enter.get_width()) // 2, rect.y + 124))
            bar = pygame.Rect(rect.x + 12, rect.bottom - 3, rect.width - 24, 2)
            pygame.draw.rect(screen, accent, bar)


class ExplorerScene():

    SLIDER_TOP    = 290
    SLIDER_ROW_H  = 58

    def __init__(self, manager: pygame_gui.UIManager):
        self.next_scene: str | None = None
        self._manager   = manager

        self._ox    = C.CANVAS_W // 2
        self._oy    = C.CANVAS_H // 2
        self._scale = min(C.CANVAS_W / (C.GRID_RANGE * 2),
                  C.CANVAS_H / (C.GRID_RANGE * 2))
        self._panel = pygame.Rect(C.CANVAS_W, 0, C.PANEL_W, C.WINDOW_H)

        self._canvas    = pygame.Surface((C.CANVAS_W, C.CANVAS_H))
        self._dirty     = True

        self._eq_idx = 0
        self._params: list[float] = []

        self._dropdown = pygame_gui.elements.UIDropDownMenu(  #dropdown menu for equations
            options_list=C.EQUATIONS,
            starting_option=C.EQUATIONS[0],
            relative_rect=pygame.Rect(C.CANVAS_W + 14, 88, C.PANEL_W - 28, 34),
            manager=manager)

        self._btn_reset = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(C.CANVAS_W + 14, C.WINDOW_H - 98,
                                      C.PANEL_W - 28, 38),
            text="Reset Parameters",
            manager=manager)

        self._btn_back = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(C.CANVAS_W + 14, C.WINDOW_H - 52,
                                      C.PANEL_W - 28, 36),
            text="Main Menu",
            manager=manager)

        self._sliders:    list = []
        self._lbl_names:  list = []
        self._lbl_values: list = []
        self._build_sliders(self._eq_idx)

        # fonts
        self._f_title = pygame.font.SysFont("consolas", 19, bold=True)
        self._f_mode  = pygame.font.SysFont("consolas", 13)
        self._f_sub   = pygame.font.SysFont("consolas", 13)
        self._f_eq    = pygame.font.SysFont("consolas", 14, bold=True)
        self._f_hint  = pygame.font.SysFont("consolas", 12)

    def on_enter(self) -> None:   #changing scene functions
        self._show_widgets(True)
        self._dirty = True

    def on_exit(self) -> None:
        self._show_widgets(False)

    def handle_event(self, event: pygame.event.Event):
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

        elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            for i, sl in enumerate(self._sliders):
                if event.ui_element is sl:
                    self._params[i] = sl.get_current_value()
                    self._lbl_values[i].set_text(f"= {self._params[i]:.2f}")
                    self._dirty = True
                    break

    def update(self, dt: float) -> None:  # checking if canvas needs to be redrawn by dirty flag
        if self._dirty:
            self._rebuild_canvas()
            self._dirty = False

    def _rebuild_canvas(self) -> None:
        self._canvas.fill(C.C_BG)
        draw_grid(self._canvas, self._ox, self._oy, self._scale)
        draw_curve(self._canvas, self._eq_idx, self._params,
                   self._ox, self._oy, self._scale)

    def draw(self, screen: pygame.Surface):
        screen.blit(self._canvas, (0, 0))
        self._draw_panel(screen)

    def _build_sliders(self, eq_idx: int):
        for el in self._sliders + self._lbl_names + self._lbl_values:  # removing old sliders
            el.kill()
        self._sliders.clear()
        self._lbl_names.clear()
        self._lbl_values.clear()
        self._params.clear()

        px = self._panel.x
        pw = self._panel.width

        for i, (name, lo, hi, default) in enumerate(C.PARAM_CONFIGS[eq_idx]):   #getting parameter configurations
            y = self.SLIDER_TOP + i * self.SLIDER_ROW_H

            self._lbl_names.append(pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(px + 14, y, 28, 20),
                text=name, manager=self._manager))      # creating sliders

            sl = pygame_gui.elements.UIHorizontalSlider(
                relative_rect=pygame.Rect(px + 14, y + 22, pw - 28, 22),
                start_value=default, value_range=(lo, hi),
                manager=self._manager)
            self._sliders.append(sl)

            self._lbl_values.append(pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(px + 46, y, 90, 20),
                text=f"= {default:.2f}", manager=self._manager))

            self._params.append(default)

    def _show_widgets(self, visible: bool):
        toggle = (lambda el: el.show()) if visible else (lambda el: el.hide())
        for el in ([self._dropdown, self._btn_reset, self._btn_back]
                   + self._sliders + self._lbl_names + self._lbl_values):
            toggle(el)

    def _draw_panel(self, screen: pygame.Surface):
        px, pw = self._panel.x, self._panel.width

        pygame.draw.rect(screen, C.C_PANEL_BG, self._panel)
        pygame.draw.line(screen, C.C_BORDER, (px, 0), (px, C.WINDOW_H), 2)

        def blit_centred(surf, y):
            screen.blit(surf, (px + (pw - surf.get_width()) // 2, y))

        def sep(y):
            pygame.draw.line(screen, C.C_SEP, (px + 8, y), (px + pw - 8, y), 1)

        blit_centred(self._f_title.render("LAGRANGIA",         True, C.C_TITLE),  18)
        blit_centred(self._f_mode.render("[ EXPLORER MODE ]",  True, C.C_ACCENT), 42)
        sep(64)

        screen.blit(self._f_sub.render("Equation Type:", True, C.C_LABEL), (px + 14, 68))

        sep(130)
        screen.blit(self._f_sub.render("Live equation:", True, C.C_LABEL), (px + 14, 138))
        screen.blit(self._f_eq.render(equation_string(self._eq_idx, self._params),
                                       True, C.C_CURVE), (px + 14, 158))

        sep(198)
        screen.blit(self._f_sub.render("Parameters:", True, C.C_LABEL), (px + 14, 206))

        screen.blit(self._f_hint.render("Drag sliders to explore",
                                         True, C.C_LABEL_DIM), (px + 14, C.WINDOW_H - 118))
        screen.blit(self._f_hint.render("ESC  /  Main Menu",
                                         True, C.C_LABEL_DIM), (px + 14, C.WINDOW_H - 100))


class ChallengeScene():

    # camera preview size — fits inside the 320px panel with margins
    CAM_W = 200
    CAM_H = 150

    # number of sub-points generated between each pair of camera samples
    # by the Catmull-Rom spline — higher = smoother curves
    SPLINE_DENSITY = 8

    def __init__(self, manager: pygame_gui.UIManager):
        self.next_scene: str | None = None
        self._manager   = manager

        self._ox    = C.CANVAS_W // 2
        self._oy    = C.CANVAS_H // 2
        self._scale = min(C.CANVAS_W / (C.GRID_RANGE * 2),
                  C.CANVAS_H / (C.GRID_RANGE * 2))
        self._panel = pygame.Rect(C.CANVAS_W, 0, C.PANEL_W, C.WINDOW_H)

        self._canvas     = pygame.Surface((C.CANVAS_W, C.CANVAS_H))
        self._draw_surf  = pygame.Surface((C.CANVAS_W, C.CANVAS_H), pygame.SRCALPHA)
        self._canvas_dirty = True

        self._ch_eq, self._ch_params, self._ch_label = _random_challenge()
        self._drawn:   list[tuple] = []
        self._drawing  = False
        self._scored   = False
        self._score    = 0.0
        self._show_true = False

        # AirCanvas state
        self._air_on      = False
        self._air_thread: AirCanvasThread | None = None
        self._cam_surface: pygame.Surface | None = None

        # rolling buffer of last 4 control points for Catmull-Rom spline;
        # deque with maxlen=4 automatically drops the oldest point
        self._air_ctrl: deque = deque(maxlen=4)

        # two cursor sprites: hollow ring for hovering, filled dot for drawing
        self._cursor_hover = pygame.Surface((18, 18), pygame.SRCALPHA)
        pygame.draw.circle(self._cursor_hover, (*C.C_AIR, 160), (9, 9), 9, 2)

        self._cursor_draw = pygame.Surface((18, 18), pygame.SRCALPHA)
        pygame.draw.circle(self._cursor_draw, (*C.C_AIR, 255), (9, 9), 9)

        # pygame_gui widgets
        W  = C.PANEL_W - 28
        HW = (C.PANEL_W - 32) // 2
        bx = C.CANVAS_W + 14

        self._btn_new   = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(bx, 68, W, 34),
            text="New Challenge", manager=manager)
        self._btn_clear = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(bx, 110, HW, 32),
            text="Clear", manager=manager)
        self._btn_score = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(bx + HW + 4, 110, HW, 32),
            text="Score", manager=manager)
        self._btn_true  = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(bx, 150, W, 32),
            text="Show / Hide True Curve", manager=manager)
        self._btn_air   = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(bx, 190, W, 34),
            text="AirCanvas  (Webcam)", manager=manager)
        self._btn_back  = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(bx, C.WINDOW_H - 52, W, 36),
            text="Main Menu", manager=manager)

        # fonts
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

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            self._handle_button(event.ui_element)

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
        # poll the AirCanvas thread for new finger positions
        if self._air_on and self._air_thread and self._air_thread.ready:
            pt       = self._air_thread.point      # already filtered in the capture thread
            pinching = self._air_thread.pinching    # True when thumb + index are pressed

            if pt and pinching:
                # record every position for scoring accuracy
                self._drawn.append(pt)
                self._scored = False

                # add this point to the spline control buffer
                self._air_ctrl.append(pt)

                if len(self._air_ctrl) >= 4:
                    # we have 4 control points — generate a smooth spline segment
                    # between ctrl[1] and ctrl[2], shaped by ctrl[0] and ctrl[3]
                    p0, p1, p2, p3 = self._air_ctrl[0], self._air_ctrl[1], \
                                     self._air_ctrl[2], self._air_ctrl[3]
                    spline_pts = _catmull_rom(p0, p1, p2, p3, self.SPLINE_DENSITY)

                    # draw the smooth sub-segments
                    prev = p1
                    for sp in spline_pts:
                        self._draw_stroke(prev, sp,
                                          glow=C.C_AIR_GLOW, line=C.C_AIR)
                        prev = sp

                elif len(self._air_ctrl) >= 2:
                    # only 2–3 points so far — fall back to straight line
                    # (happens at the very start of a stroke)
                    self._draw_stroke(self._air_ctrl[-2], self._air_ctrl[-1],
                                      glow=C.C_AIR_GLOW, line=C.C_AIR)

            else:
                # fingers apart or hand lost — "pen up", clear the control buffer
                # so the next pinch starts a fresh spline
                self._air_ctrl.clear()

            self._cam_surface = self._air_thread.get_frame_surface(
                self.CAM_W, self.CAM_H)

        if self._canvas_dirty:
            self._rebuild_canvas()
            self._canvas_dirty = False

    def draw(self, screen: pygame.Surface) -> None:
        screen.blit(self._canvas,    (0, 0))
        screen.blit(self._draw_surf, (0, 0))
        self._draw_air_overlay(screen)
        self._draw_panel(screen)
        self._draw_cam_preview(screen)   # on top of panel, so drawn last

    def _handle_button(self, btn):
        if btn is self._btn_back:
            self.next_scene = "menu"

        elif btn is self._btn_new:
            self._ch_eq, self._ch_params, self._ch_label = _random_challenge()
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

    def _draw_stroke(self, p1, p2, glow=C.C_DRAWN_GLOW, line=C.C_DRAWN):
        pygame.draw.line(self._draw_surf, (*glow, 150), p1, p2, 7)
        pygame.draw.line(self._draw_surf, (*line, 210), p1, p2, 3)

    def _reset_drawing(self):
        self._drawn.clear()
        self._drawing    = False
        self._scored     = False
        self._score      = 0.0
        self._air_ctrl.clear()
        self._draw_surf.fill((0, 0, 0, 0))

    def _stop_air(self):
        if self._air_thread:
            self._air_thread.stop()
            self._air_thread = None
        self._air_on      = False
        self._air_ctrl.clear()
        self._cam_surface = None

    def _rebuild_canvas(self):
        self._canvas.fill(C.C_BG)
        draw_grid(self._canvas, self._ox, self._oy, self._scale)
        if self._show_true:
            draw_curve(self._canvas, self._ch_eq, self._ch_params,
                       self._ox, self._oy, self._scale,
                       colour=C.C_TARGET, glow=C.C_TARGET_GLOW)

    def _draw_cam_preview(self, screen: pygame.Surface):
        if not self._air_on or self._cam_surface is None:
            return
        # centred on the panel, just above the back button
        cam_x = C.CANVAS_W + (C.PANEL_W - self.CAM_W) // 2
        cam_y = C.WINDOW_H - 52 - 14 - self.CAM_H
        screen.blit(self._cam_surface, (cam_x, cam_y))

    def _draw_air_overlay(self, screen: pygame.Surface):
        if not self._air_on:
            return
        t = self._air_thread
        pt       = t.point    if (t and t.ready) else None
        pinching = t.pinching if (t and t.ready) else False

        if pt:
            # swap cursor sprite depending on pinch state
            cursor = self._cursor_draw if pinching else self._cursor_hover
            screen.blit(cursor, (pt[0] - 9, pt[1] - 9))
            # on-canvas status label
            if pinching:
                screen.blit(self._f_hint.render("● DRAWING", True, C.C_AIR), (8, 8))
            else:
                screen.blit(self._f_hint.render("○ MOVE", True, C.C_LABEL_DIM), (8, 8))
        elif t and t.ready:
            screen.blit(self._f_hint.render("◌  No hand detected",
                                             True, C.C_LABEL_DIM), (8, 8))
        elif t and t.error_msg:
            screen.blit(self._f_hint.render(t.error_msg[:56], True, C.C_RED), (8, 8))
        else:
            screen.blit(self._f_hint.render("Initialising webcam",
                                             True, C.C_LABEL_DIM), (8, 8))

    def _draw_panel(self, screen: pygame.Surface) -> None:
        px, pw = self._panel.x, self._panel.width

        pygame.draw.rect(screen, C.C_PANEL_BG, self._panel)
        pygame.draw.line(screen, C.C_BORDER, (px, 0), (px, C.WINDOW_H), 2)

        def blit_c(surf, y):   # centre-align in panel
            screen.blit(surf, (px + (pw - surf.get_width()) // 2, y))

        def sep(y):
            pygame.draw.line(screen, C.C_SEP, (px + 8, y), (px + pw - 8, y), 1)

        blit_c(self._f_title.render("LAGRANGIA",          True, C.C_TITLE),  18)
        blit_c(self._f_mode.render("[ CHALLENGE MODE ]",  True, C.C_TARGET), 42)
        sep(64)

        sep(228)
        screen.blit(self._f_sub_b.render("Target equation:", True, C.C_LABEL), (px + 14, 236))
        blit_c(self._f_eq.render(self._ch_label, True, C.C_TARGET), 256)
        sep(280)

        inp_label  = "AirCanvas" if self._air_on else "Mouse"
        inp_colour = C.C_AIR        if self._air_on else C.C_LABEL
        screen.blit(self._f_sub_b.render(f"Input: {inp_label}", True, inp_colour),
                    (px + 14, 288))

        if self._air_on:
            t      = self._air_thread
            status = ("Pinch to draw, release to move" if (t and t.ready)
                      else t.error_msg[:36]            if (t and t.error_msg)
                      else "Initialising webcam")
            col    = C.C_RED if (t and t.error_msg and not t.ready) else C.C_LABEL_DIM
            screen.blit(self._f_hint.render(status, True, col), (px + 14, 308))
        else:
            screen.blit(self._f_hint.render("Click and drag on the grid",
                                             True, C.C_LABEL_DIM), (px + 14, 308))

        sep(328)
        screen.blit(self._f_sub.render(f"Points drawn: {len(self._drawn)}",
                                        True, C.C_LABEL), (px + 14, 336))

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

        leg_y = 510 if self._scored else 388
        pygame.draw.line(screen, C.C_TARGET,
                         (px + 14, leg_y + 7), (px + 44, leg_y + 7), 2)
        screen.blit(self._f_hint.render("True curve",  True, C.C_LABEL_DIM), (px + 50, leg_y))

        d_col = C.C_AIR if self._air_on else C.C_DRAWN
        pygame.draw.line(screen, d_col,
                         (px + 14, leg_y + 22), (px + 44, leg_y + 22), 2)
        screen.blit(self._f_hint.render("Your drawing", True, C.C_LABEL_DIM),
                    (px + 50, leg_y + 14))

    def _show_widgets(self, visible: bool) -> None:
        toggle = (lambda el: el.show()) if visible else (lambda el: el.hide())
        for el in [self._btn_new, self._btn_clear, self._btn_score,
                   self._btn_true, self._btn_air, self._btn_back]:
            toggle(el)