import os
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
from typing import List, Optional, Protocol

class UIState(Protocol):
    def handle_event(self, event: pygame.event.Event): ...
    def update(self, dt: float): ...
    def draw(self, surface: pygame.Surface): ...
    def on_enter(self): ...
    def on_exit(self): ...

class App:
    WIDTH, HEIGHT = 1280, 720
    TITLE = "D20 Fight Club"

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption(self.TITLE)
        self.clock = pygame.time.Clock()
        self._stack: List[UIState] = []
        self._running = False

    def push_state(self, state: UIState):
        self._stack.append(state)
        state.on_enter()

    def pop_state(self):
        if self._stack:
            s = self._stack.pop()
            s.on_exit()

    @property
    def state(self) -> Optional[UIState]:
        return self._stack[-1] if self._stack else None

    def run(self):
        self._running = True
        while self._running and self.state is not None:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    break
                nxt = self.state.handle_event(event)
                if nxt is not None:
                    self.push_state(nxt)
            nxt = self.state.update(dt)
            if nxt is not None:
                self.push_state(nxt)
            self.screen.fill((18,18,22))
            self.state.draw(self.screen)
            pygame.display.flip()
        pygame.quit()
