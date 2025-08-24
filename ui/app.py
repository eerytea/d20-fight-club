# ui/app.py
import os
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
from typing import Protocol, Optional, List


# Optional global so states can grab the current App without wiring
# (used by MenuState -> TeamSelectState handoff)
pygame._app_ref = None  # type: ignore[attr-defined]


class UIState(Protocol):
    """Interface for UI states."""
    def on_enter(self) -> None: ...
    def on_exit(self) -> None: ...
    def handle_event(self, event: pygame.event.Event) -> Optional["UIState"]: ...
    def update(self, dt: float) -> Optional["UIState"]: ...
    def draw(self, surface: pygame.Surface) -> None: ...


class App:
    def __init__(self, width: int = 1280, height: int = 720, title: str = "D20 Fight Club", fps: int = 60):
        pygame.init()
        pygame._app_ref = self  # type: ignore[attr-defined]

        self.WIDTH, self.HEIGHT = width, height
        self.TITLE = title
        self.FPS = fps

        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption(self.TITLE)
        self.clock = pygame.time.Clock()

        self._stack: List[UIState] = []
        self._running = False

    # ---------- state stack ----------
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
            pass  # don't crash if an on_exit is empty

        if not self._stack:
            # no states left -> exit
            self._running = False

    def replace_state(self, state: UIState) -> None:
        """Pop current state and push a new one."""
        if self._stack:
            self.pop_state()
        self.push_state(state)

    @property
    def state(self) -> Optional[UIState]:
        return self._stack[-1] if self._stack else None

    # ---------- main loop ----------
    def run(self) -> None:
        self._running = True
        try:
            while self._running and self.state is not None:
                dt = self.clock.tick(self.FPS) / 1000.0

                # events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self._running = False
                        break
                    nxt = self.state.handle_event(event)  # type: ignore[union-attr]
                    if nxt is not None:
                        self.push_state(nxt)

                # update
                nxt = self.state.update(dt)  # type: ignore[union-attr]
                if nxt is not None:
                    self.push_state(nxt)

                # draw
                self.screen.fill((18, 18, 22))
                self.state.draw(self.screen)  # type: ignore[union-attr]
                pygame.display.flip()
        finally:
            pygame.quit()
