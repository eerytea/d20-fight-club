# ui/state_settings.py
import pygame
from typing import Optional
from .app import UIState
from .uiutil import draw_text, BIG, FONT, Button

class SettingsState(UIState):
    def __init__(self):
        self._btn = None

    def on_enter(self) -> None:
        self._btn = Button(pygame.Rect(24, 24, 120, 40), "Back", on_click=self._back)

    def on_exit(self) -> None:
        self._btn = None

    def _back(self):
        pygame._app_ref.pop_state()  # type: ignore[attr-defined]

    def handle_event(self, event: pygame.event.Event) -> Optional["UIState"]:
        if self._btn: self._btn.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self._back()
        return None

    def update(self, dt: float) -> Optional["UIState"]:
        return None

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((18,18,22))
        draw_text(surface, "Settings (placeholder)", (24, 24), font=BIG)
        draw_text(surface, "Coming soon: audio, speed, UI scale, etc.", (24, 84), font=FONT)
        if self._btn: self._btn.draw(surface)
