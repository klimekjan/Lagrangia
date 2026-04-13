import sys
import pygame
import pygame_gui
import constants as C
from scenes import MenuScene, ExplorerScene, ChallengeScene

# mediapipe==0.10.1

class SceneManager:
   
    def __init__(self):
        self._manager = pygame_gui.UIManager((C.WINDOW_W, C.WINDOW_H))  #built in UI manager fitted to the window size
        self._manager.get_theme().load_theme(C.UI_THEME)                # loading custom theme from constants.py

        # list of scenes
        self._scenes = {
            "menu":      MenuScene(self._manager),
            "explorer":  ExplorerScene(self._manager),
            "challenge": ChallengeScene(self._manager),
        }

        self._active_key = "menu"           
        for key, scene in self._scenes.items():  # checking whether the scence needs to change
            if hasattr(scene, "on_enter"):
                if key == self._active_key:
                    scene.on_enter()
                else:
                    scene.on_exit()   # hides widgets for inactive scenes

    @property
    def active(self):
        return self._scenes[self._active_key]

    def transition(self, new_key: str):
        if new_key not in self._scenes:
            return
        if hasattr(self.active, "on_exit"):    #cleaning current scene
            self.active.on_exit()
        self._active_key = new_key #swiching keys
        self.active.next_scene = None
        if hasattr(self.active, "on_enter"):  # initialising new scene
            self.active.on_enter()

    def handle_event(self, event: pygame.event.Event):
        self._manager.process_events(event)
        self.active.handle_event(event)

    def update(self, dt: float):
        self._manager.update(dt)
        self.active.update(dt)

        if self.active.next_scene is not None:
            self.transition(self.active.next_scene)

    def draw(self, screen: pygame.Surface):
        self.active.draw(screen)
        self._manager.draw_ui(screen)




def main() -> None:
    pygame.init()

    screen = pygame.display.set_mode((C.WINDOW_W, C.WINDOW_H))
    pygame.display.set_caption("Lagrangia")

    clock   = pygame.time.Clock()
    manager = SceneManager()

    running = True
    while running:
        dt = clock.tick(C.FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:    #checking if ESC
                if manager._active_key == "menu":
                    running = False            # quit from the menu screen
                else:
                    manager.transition("menu") # return to menu from any other scene

            manager.handle_event(event)

        manager.update(dt)
        manager.draw(screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
