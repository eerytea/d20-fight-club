import pygame
from .app import UIState

class MenuState(UIState):
    def __init__(self):
        self._font = None

    def on_enter(self):
        if not pygame.font.get_init():
            pygame.font.init()
        self._font = pygame.font.Font(pygame.font.get_default_font(), 28)

    def on_exit(self): pass
    def handle_event(self, event): return None
    def update(self, dt): return None

    def draw(self, surface):
        txt = self._font.render("D20 Fight Club — Press Enter (stub)", True, (220,220,230))
        surface.blit(txt, (40, 40))
