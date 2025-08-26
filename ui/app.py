# ui/app.py
from __future__ import annotations

import os
from typing import Optional, List

import pygame


class App:
    def __init__(self, width: int = 1024, height: int = 576, title: str = "App"):
        # Headless-safe for CI/tests
        if os.environ.get("SDL_VIDEODRIVER") == "dummy":
            pass
        pygame.init()
        pygame.display.set_caption(title)

        # Create window and keep width/height attributes for states that use them
        self.screen = pygame.display.set_mode((width, height))
        self.width, self.height = self.screen.get_size()

        self.clock = pygame.time.Clock()
        self.running = True

        self._stack: List["BaseState"] = []

    # --- State stack ---------------------------------------------------------
    @property
    def state(self) -> Optional["BaseState"]:
        return self._stack[-1] if self._stack else None

    def push_state(self, st: "BaseState") -> None:
        st.app = self
        self._stack.append(st)
        if hasattr(st, "enter"):
            st.enter()

    def pop_state(self) -> None:
        if self._stack:
            st = self._stack.pop()
            if hasattr(st, "exit"):
                st.exit()

    # --- Main loop -----------------------------------------------------------
    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            st = self.state

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    # If you later make the window resizable, keep size attrs in sync
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    self.width, self.height = self.screen.get_size()
                elif st is not None and hasattr(st, "handle"):
                    st.handle(event)

            if st is not None and hasattr(st, "update"):
                st.update(dt)

            # Paint
            if st is not None and hasattr(st, "draw"):
                st.draw(self.screen)
            else:
                self.screen.fill((16, 20, 24))

            # Keep attributes in sync even without resize events (belt & suspenders)
            self.width, self.height = self.screen.get_size()

            pygame.display.flip()

    # Convenience
    def quit(self) -> None:
        self.running = False


class BaseState:
    """
    Optional base class for states; concrete states can ignore and simply
    define handle/update/draw as needed. The App sets `state.app = app`.
    """
    app: App

    def enter(self) -> None:  # optional
        pass

    def exit(self) -> None:  # optional
        pass

    def handle(self, event) -> None:  # optional
        pass

    def update(self, dt: float) -> None:  # optional
        pass

    def draw(self, surf) -> None:  # required-ish
        raise NotImplementedError
