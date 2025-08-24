# ui/state_message.py
import pygame
from typing import Optional
from .app import UIState
from .uiutil import draw_text, BIG, FONT, Button

class MessageState(UIState):
    def __init__(self, title: str, body: str):
        self.title = title
        self.body = body
        self._btn = None

    def on_enter(self) -> None:
        W = pygame._app_ref.WIDTH  # type: ignore[attr-defined]
        self._btn = Button(pygame.Rect(W - 180, 24, 140, 40), "Back", on_click=self._back)

    def on_exit(self) -> None:
        self._btn = None

    def _back(self):
        pygame._app_ref.pop_state()  # type: ignore[attr-defined]

    def handle_event(self, event: pygame.event.Event) -> Optional["UIState"]:
        if self._btn:
            self._btn.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
            self._back()
        return None

    def update(self, dt: float) -> Optional["UIState"]:
        return None

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((18,18,22))
        draw_text(surface, self.title, (24, 24), font=BIG)
        # simple multiline body
        x, y = 24, 84
        for line in self.body.splitlines():
            draw_text(surface, line, (x, y), font=FONT)
            y += 24
        if self._btn:
            self._btn.draw(surface)
