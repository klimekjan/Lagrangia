# =============================================================================
# main.py — Math Curve Explorer
# Entry point. Creates one pygame window that lives for the entire session.
# Manages the active scene and routes events, updates, and draws.
#
# Run:  python main.py
# =============================================================================

import sys
import pygame
import pygame_gui

import constants as C
from scenes import MenuScene, ExplorerScene, ChallengeScene


# -----------------------------------------------------------------------------
# SceneManager
# -----------------------------------------------------------------------------

class SceneManager:
    """
    Owns the single UIManager and all scene instances.
    Every frame it asks the active scene whether it wants to transition
    (scene.next_scene is set to a key string), and if so switches cleanly
    by calling on_exit() / on_enter() and hiding/showing the right widgets.
    """

    def __init__(self) -> None:
        self._manager = pygame_gui.UIManager((C.WINDOW_W, C.WINDOW_H))
        self._manager.get_theme().load_theme(C.UI_THEME)

        # Instantiate every scene once; they share the single UIManager so
        # all widgets are always in the same element pool.
        self._scenes = {
            "menu":      MenuScene(self._manager),
            "explorer":  ExplorerScene(self._manager),
            "challenge": ChallengeScene(self._manager),
        }

        # Start on the menu; hide all other scenes' widgets immediately
        self._active_key = "menu"
        for key, scene in self._scenes.items():
            if hasattr(scene, "on_enter"):
                if key == self._active_key:
                    scene.on_enter()
                else:
                    scene.on_exit()   # hides widgets for inactive scenes

    @property
    def active(self):
        return self._scenes[self._active_key]

    def transition(self, new_key: str) -> None:
        if new_key not in self._scenes:
            return
        # Let the current scene clean up
        if hasattr(self.active, "on_exit"):
            self.active.on_exit()
        # Switch
        self._active_key = new_key
        self.active.next_scene = None
        # Let the new scene initialise
        if hasattr(self.active, "on_enter"):
            self.active.on_enter()

    def handle_event(self, event: pygame.event.Event) -> None:
        self._manager.process_events(event)
        self.active.handle_event(event)

    def update(self, dt: float) -> None:
        self._manager.update(dt)
        self.active.update(dt)

        # Check for a requested scene change
        if self.active.next_scene is not None:
            self.transition(self.active.next_scene)

    def draw(self, screen: pygame.Surface) -> None:
        self.active.draw(screen)
        self._manager.draw_ui(screen)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> None:
    pygame.init()

    screen = pygame.display.set_mode((C.WINDOW_W, C.WINDOW_H))
    pygame.display.set_caption("Math Curve Explorer — IB CS IA")

    clock   = pygame.time.Clock()
    manager = SceneManager()

    running = True
    while running:
        dt = clock.tick(C.FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if manager._active_key == "menu":
                    running = False            # ESC on menu → quit
                else:
                    manager.transition("menu") # ESC in a scene → back to menu

            manager.handle_event(event)

        manager.update(dt)
        manager.draw(screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
