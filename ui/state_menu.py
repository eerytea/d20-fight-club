# ui/state_menu.py
from __future__ import annotations

from typing import List, Optional

try:
    import pygame
except Exception:  # pragma: no cover
    pygame = None  # type: ignore

from .uiutil import Theme, Button, draw_text
from .app import App


class MenuState:
    def __init__(self, app: Optional[App] = None) -> None:
        self.app: App | None = app
        self._buttons: List[Button] = []

    # ------------- lifecycle -------------

    def enter(self) -> None:
        if pygame is None or self.app is None:
            return
        W, H = self.app.width, self.app.height

        btn_w, btn_h = 300, 48
        gap = 16
        left = (W - btn_w) // 2
        top = H // 3

        def rect_at(row: int) -> "pygame.Rect":
            return pygame.Rect(left, top + row * (btn_h + gap), btn_w, btn_h)

        def push_team_select():
            try:
                from .state_team_select import TeamSelectState
                self.app.safe_push(TeamSelectState)
            except Exception:
                self._show_msg("Team Select not available")

        def push_exhibition():
            try:
                from .state_exhibition_picker import ExhibitionPickerState
                self.app.safe_push(ExhibitionPickerState)
            except Exception:
                self._show_msg("Exhibition Picker not available")

        def push_settings():
            try:
                from .state_settings import SettingsState
                self.app.safe_push(SettingsState)
            except Exception:
                self._show_msg("Settings coming soon")

        def push_load():
            try:
                from core.save import load_latest
                career = load_latest()
                if career is None:
                    self._show_msg("No save found")
                    return
                self.app.data["career"] = career
                from .state_season_hub import SeasonHubState
                self.app.safe_push(SeasonHubState, career=career)
            except Exception:
                self._show_msg("Load game not wired yet")

        self._buttons = [
            Button(rect_at(0), "New Game", on_click=push_team_select),
            Button(rect_at(1), "Load Game", on_click=push_load),
            Button(rect_at(2), "Exhibition", on_click=push_exhibition),
            Button(rect_at(3), "Settings", on_click=push_settings),
            Button(rect_at(4), "Quit", on_click=self.app.quit if self.app else None),
        ]

    def exit(self) -> None:
        self._buttons.clear()

    # ------------- events -------------

    def handle_event(self, event: "pygame.event.Event") -> bool:
        for b in self._buttons:
            if b.handle_event(event):
                return True
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: "pygame.Surface") -> None:
        th = Theme()
        surface.fill(th.bg)
        draw_text(surface, "D20 Fight Club", (surface.get_width() // 2, 80), size=48, align="center")
        for b in self._buttons:
            b.draw(surface)

    # ------------- helpers -------------

    def _show_msg(self, text: str) -> None:
        try:
            from .state_message import MessageState
            self.app.safe_push(MessageState, message=text)
        except Exception:
            print(text)
