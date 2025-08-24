# ui/state_menu.py
from __future__ import annotations

try:
    import pygame
except Exception:
    pygame = None  # type: ignore

from .state_team_select import TeamSelectState
from .state_exhibition_picker import ExhibitionPickerState
from .state_message import MessageState


class MenuState:
    """
    Very small keyboard menu.

    Controls:
      UP/DOWN   — select
      ENTER     — confirm
      ESC       — quit
    """
    def __init__(self, app) -> None:
        self.app = app
        self._font = None
        self.items = [
            ("New Game", self._new_game),
            ("Exhibition", self._exhibition),
            ("Quit", self._quit),
        ]
        self.index = 0

    def enter(self) -> None:
        if pygame is None:
            return
        pygame.font.init()
        self._font = pygame.font.SysFont("consolas", 26)

    def handle_event(self, event) -> bool:
        if pygame is None:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._quit()
                return True
            if event.key == pygame.K_UP:
                self.index = (self.index - 1) % len(self.items)
                return True
            if event.key == pygame.K_DOWN:
                self.index = (self.index + 1) % len(self.items)
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                _, fn = self.items[self.index]
                fn()
                return True
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface) -> None:
        if pygame is None:
            return
        w, h = surface.get_size()
        title = self._text("D20 Fight Club", 36, bold=True)
        surface.blit(title, (24, 24))

        y = 140
        for i, (label, _) in enumerate(self.items):
            selected = (i == self.index)
            prefix = "> " if selected else "  "
            color = (255, 255, 255) if selected else (200, 200, 200)
            txt = self._font.render(prefix + label, True, color)  # type: ignore
            surface.blit(txt, (80, y))
            y += 40

        hint = self._text("UP/DOWN to choose • ENTER to confirm • ESC to quit", 18)
        surface.blit(hint, (24, h - 40))

    # ---- actions ----

    def _new_game(self):
        # Use safe transitions so errors show a popup instead of exiting
        if hasattr(self.app, "safe_push"):
            self.app.safe_push(TeamSelectState, app=self.app)
        else:
            self.app.push_state(TeamSelectState(app=self.app))

    def _exhibition(self):
        if hasattr(self.app, "safe_push"):
            self.app.safe_push(ExhibitionPickerState, app=self.app)
        else:
            self.app.push_state(ExhibitionPickerState(app=self.app))

    def _quit(self):
        self.app.quit()

    # ---- helpers ----

    def _text(self, s: str, size: int, bold: bool = False):
        ft = pygame.font.SysFont("consolas", size, bold=bold)  # type: ignore
        return ft.render(s, True, (255, 255, 255))
