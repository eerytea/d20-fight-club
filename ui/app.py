# ui/app.py
import os
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
from typing import Protocol, Optional, List

# make a global ref available for states (like MenuState)
pygame._app_ref = None  # type: ignore[attr-defined]


class UIState(Protocol):
    def on_enter(self) -> None: ...
    def on_exit(self) -> None: ...
    def handle_event(self, event: pygame.event.Event) -> Optional["UIState"]: ...
    def update(self, dt: float) -> Optional["UIState"]: ...
    def draw(self, surface: pygame.Surface) -> None: ...


class App:
    def __init__(self, width: int = 1280, height: int = 720,
                 title: str = "D20 Fight Club", fps: int = 60):
        pygame.init()
        pygame._app_ref = self  # 👈 set the global reference here

        self.WIDTH, self.HEIGHT = width, height
        self.TITLE = title
        self.FPS = fps

        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption(self.TITLE)
        self.clock = pygame.time.Clock()

        self._stack: List[UIState] = []
        self._running = False

    def push_state(self, state: UIState) -> None:
        self._stack.append(state)
        state.on_enter()

    def pop_state(self) -> None:
        if not self._stack:
            return
        s = self._stack.pop()
        try:
            s.on_exit()
        except Exception:
            pass
        if not self._stack:
            self._running = False

    def replace_state(self, state: UIState) -> None:
        if self._stack:
            self.pop_state()
        self.push_state(state)

    @property
    def state(self) -> Optional[UIState]:
        return self._stack[-1] if self._stack else None

    def run(self) -> None:
        sel
