# ui/state_menu.py
from __future__ import annotations

import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_text


class MenuState(BaseState):
    def __init__(self):
        self.theme = Theme()
        self.buttons: list[Button] = []

    def enter(self) -> None:
        # Layout buttons in a column
        x, y = 60, 140
        w, h = 260, 44
        gap = 14

        def add(label, fn):
            nonlocal y
            self.buttons.append(Button(pygame.Rect(x, y, w, h), label, fn))
            y += h + gap

        add("New Season", self._new_season)
        add("Exhibition", self._exhibition)
        add("Roster Browser", self._open_roster_browser)  # <- shows all teams + Generate
        add("Load Game", self._load_game)
        add("Settings", self._settings)
        add("Quit", self._quit)

    # --- Button actions ------------------------------------------------------
    def _new_season(self):
        try:
            from .state_team_select import TeamSelectState
            self.app.push_state(TeamSelectState(self.app))
        except Exception:
            # Safe fallback: just ignore if screen not present yet
            pass

    def _exhibition(self):
        try:
            from .state_exhibition_picker import ExhibitionPickerState
            self.app.push_state(ExhibitionPickerState(self.app))
        except Exception:
            pass

    def _open_roster_browser(self):
        try:
            from .state_roster_browser import RosterBrowserState
            self.app.push_state(RosterBrowserState(self.app))
        except Exception:
            # If the file isn't present, silently ignore for now
            pass

    def _load_game(self):
        try:
            from .state_season_hub import SeasonHubState
            self.app.push_state(SeasonHubState(self.app))  # placeholder
        except Exception:
            pass

    def _settings(self):
        # Placeholder for a settings screen
        pass

    def _quit(self):
        self.app.quit()

    # --- State interface -----------------------------------------------------
    def handle(self, event) -> None:
        for b in self.buttons:
            b.handle(event)

    def update(self, dt: float) -> None:
        mx, my = pygame.mouse.get_pos()
        for b in self.buttons:
            b.update((mx, my))

    def draw(self, surf) -> None:
        surf.fill(self.theme.bg)
        draw_text(surf, "D20 Fight Club", (60, 60), 48, self.theme.text)
        for b in self.buttons:
            b.draw(surf, self.theme)
