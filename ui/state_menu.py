# ui/state_menu.py
import pygame
from typing import Optional
from .app import UIState

class MenuState(UIState):
    def __init__(self):
        self.font_big: Optional[pygame.font.Font] = None
        self.font: Optional[pygame.font.Font] = None
        self.buttons = []  # not used yet; we just draw text to confirm rendering

    def on_enter(self) -> None:
        if not pygame.font.get_init():
            pygame.font.init()
        # Use None to force the default font so this can't fail due to missing font files
        self.font_big = pygame.font.Font(None, 48)
        self.font = pygame.font.Font(None, 28)

    def on_exit(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> Optional["UIState"]:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            # Press Enter to progress into Team Select to verify transitions
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                from .state_team_select import TeamSelectState
                return TeamSelectState(pygame._app_ref)  # type: ignore[attr-defined]
        return None

    def update(self, dt: float) -> Optional["UIState"]:
        return None

    def draw(self, surface: pygame.Surface) -> None:
        # Background
        surface.fill((18, 18, 22))

        # Bold header bar so you can see something even if text failed
        pygame.draw.rect(surface, (40, 70, 110), pygame.Rect(0, 0, surface.get_width(), 80))

        # Title text
        if self.font_big:
            title = self.font_big.render("D20 Fight Club — Main Menu", True, (240, 240, 245))
            surface.blit(title, (24, 20))

        # Instruction text
        if self.font:
            hint1 = self.font.render("Press Enter or Space to start a New Game", True, (230, 230, 235))
            hint2 = self.font.render("Press Esc to Quit", True, (200, 200, 205))
            surface.blit(hint1, (24, 120))
            surface.blit(hint2, (24, 160))

        # Big visible panel so the screen is never “empty”
        pygame.draw.rect(surface, (36, 38, 44), pygame.Rect(24, 200, surface.get_width()-48, 300), border_radius=12)
        pygame.draw.rect(surface, (22, 24, 28), pygame.Rect(24, 200, surface.get_width()-48, 300), 2, border_radius=12)
