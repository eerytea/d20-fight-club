# ui/state_menu.py
import pygame
from typing import Optional
from .app import UIState
from .uiutil import draw_text, BIG, FONT

class MenuState(UIState):
    def __init__(self):
        self._entered = False

    def on_enter(self) -> None:
        if not pygame.font.get_init():
            pygame.font.init()

    def on_exit(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> Optional["UIState"]:
        # Start new career on Enter / Space / Mouse click
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            from .state_team_select import TeamSelectState
            # App instance exposed as pygame._app_ref in App.__init__
            return TeamSelectState(pygame._app_ref)  # type: ignore[attr-defined]

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            from .state_team_select import TeamSelectState
            return TeamSelectState(pygame._app_ref)  # type: ignore[attr-defined]

        # Allow ESC / Q to quit the app
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
            # Returning None keeps current state; ask App to stop by posting QUIT
            pygame.event.post(pygame.event.Event(pygame.QUIT))

        return None

    def update(self, dt: float) -> Optional["UIState"]:
        return None

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((18, 18, 22))
        draw_text(surface, "D20 Fight Club", (40, 40), font=BIG)
        draw_text(surface, "Press Enter (or click) to start a New Career", (40, 92), font=FONT)
        draw_text(surface, "Esc to quit", (40, 122), font=FONT)
