# ui/state_menu.py
from __future__ import annotations

from typing import Callable, List, Optional

try:
    import pygame
except Exception:
    pygame = None  # type: ignore

# Try to use your shared Button helper if available
try:
    from .uiutil import Button  # expected signature: Button(rect, label, on_click=callable)
except Exception:
    Button = None  # type: ignore

from .state_team_select import TeamSelectState
from .state_exhibition_picker import ExhibitionPickerState
from .state_message import MessageState


class MenuState:
    """
    Main menu with buttons (mouse) and keyboard fallback.

    Keyboard:
      UP/DOWN   – select
      ENTER     – confirm
      ESC       – quit
    """

    def __init__(self, app) -> None:
        self.app = app
        self._font = None
        self._small = None
        self._buttons: List = []
        self._items = [
            ("New Game", self._new_game),
            ("Exhibition", self._exhibition),
            ("Settings", self._settings),
            ("Quit", self._quit),
        ]
        self._index = 0  # for keyboard fallback

    # ---------- lifecycle ----------

    def enter(self) -> None:
        if pygame is None:
            return
        pygame.font.init()
        self._font = pygame.font.SysFont("consolas", 28)
        self._small = pygame.font.SysFont("consolas", 16)

        # Build buttons if helper is available
        self._buttons.clear()
        if Button is not None and self.app is not None:
            x, y = 80, 140
            for label, fn in self._items:
                rect = pygame.Rect(x, y, 240, 48)
                self._buttons.append(Button(rect, label, on_click=fn))  # type: ignore
                y += 64

    def exit(self) -> None:
        pass

    # ---------- events / update / draw ----------

    def handle_event(self, event) -> bool:
        if pygame is None:
            return False

        # Mouse → buttons
        if Button is not None and self._buttons:
            for b in self._buttons:
                if hasattr(b, "handle_event") and b.handle_event(event):  # type: ignore
                    return True

        # Keyboard fallback
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._quit()
                return True
            if event.key == pygame.K_UP:
                self._index = (self._index - 1) % len(self._items)
                return True
            if event.key == pygame.K_DOWN:
                self._index = (self._index + 1) % len(self._items)
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                _, fn = self._items[self._index]
                fn()
                return True
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface) -> None:
        if pygame is None:
            return
        w, h = surface.get_size()
        title = self._font.render("D20 Fight Club", True, (255, 255, 255))  # type: ignore
        surface.blit(title, (24, 24))

        if Button is not None and self._buttons:
            # Button UI
            for b in self._buttons:
                if hasattr(b, "draw"):
                    b.draw(surface)  # type: ignore
            hint = self._small.render("Click a button • ESC to quit", True, (200, 200, 200))  # type: ignore
            surface.blit(hint, (24, h - 32))
            return

        # Keyboard fallback list
        y = 140
        for i, (label, _) in enumerate(self._items):
            sel = (i == self._index)
            prefix = "> " if sel else "  "
            color = (255, 255, 255) if sel else (200, 200, 200)
            txt = self._font.render(prefix + label, True, color)  # type: ignore
            surface.blit(txt, (80, y))
            y += 40
        hint = self._small.render("UP/DOWN to choose • ENTER confirm • ESC quit", True, (200, 200, 200))  # type: ignore
        surface.blit(hint, (24, h - 32))

    # ---------- actions ----------

    def _new_game(self) -> None:
        if hasattr(self.app, "safe_push"):
            self.app.safe_push(TeamSelectState, app=self.app)
        else:
            self.app.push_state(TeamSelectState(app=self.app))

    def _exhibition(self) -> None:
        if hasattr(self.app, "safe_push"):
            self.app.safe_push(ExhibitionPickerState, app=self.app)
        else:
            self.app.push_state(ExhibitionPickerState(app=self.app))

    def _settings(self) -> None:
        # If you have a SettingsState, push it; else show a friendly popup
        try:
            from .state_settings import SettingsState  # type: ignore
            if hasattr(self.app, "safe_push"):
                self.app.safe_push(SettingsState, app=self.app)
            else:
                self.app.push_state(SettingsState(app=self.app))
        except Exception:
            self.app.push_state(MessageState(app=self.app, text="Settings screen not available."))

    def _quit(self) -> None:
        self.app.quit()
