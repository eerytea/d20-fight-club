# ui/state_menu.py
from __future__ import annotations

import pygame
from .app import BaseState
from .uiutil import Theme, Button, draw_text


class MenuState(BaseState):
    def __init__(self):
        self.theme = Theme()
        self.buttons: list[Button] = []
        self._layout_built = False

    def enter(self) -> None:
        self._build_layout()

    def _build_layout(self) -> None:
        self.buttons.clear()
        W, H = self.app.screen.get_size()
        w, h = 260, 44
        gap = 14
        labels = [
            ("New Season", self._new_season),
            ("Exhibition", self._exhibition),
            ("Roster Browser", self._open_roster_browser),  # has Generate
            ("Load Game (coming soon)", self._load_game),
            ("Settings (coming soon)", self._settings),
            ("Quit", self._quit),
        ]
        total_h = len(labels) * h + (len(labels) - 1) * gap
        x = (W - w) // 2
        y = max(90, (H - total_h) // 2)

        for label, fn in labels:
            self.buttons.append(Button(pygame.Rect(x, y, w, h), label, fn))
            y += h + gap

        self._layout_built = True

    # --- Button actions ------------------------------------------------------
    def _new_season(self):
        try:
            from .state_team_select import TeamSelectState
            self.app.push_state(TeamSelectState(self.app))
        except Exception:
            # Silently ignore if not ready
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
            pass

    def _load_game(self):
        # Placeholder — avoid pushing SeasonHub with None career (caused your crash)
        print("[Load] Coming soon.")

    def _settings(self):
        print("[Settings] Coming soon.")

    def _quit(self):
        self.app.quit()

    # --- State interface -----------------------------------------------------
    def handle(self, event) -> None:
        if not self._layout_built:
            return
        for b in self.buttons:
            b.handle(event)

    def update(self, dt: float) -> None:
        if not self._layout_built:
            self._build_layout()
        mx, my = pygame.mouse.get_pos()
        for b in self.buttons:
            b.update((mx, my))

    def draw(self, surf) -> None:
        if not self._layout_built:
            self._build_layout()
        W, _ = surf.get_size()
        surf.fill(self.theme.bg)
        draw_text(surf, "D20 Fight Club", (W // 2, 40), 48, self.theme.text, align="center")
        for b in self.buttons:
            b.draw(surf, self.theme)
