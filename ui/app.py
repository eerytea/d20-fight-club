# ui/app.py
from __future__ import annotations

import os
from typing import Any, List, Optional, Type

try:
    import pygame
except Exception:  # pragma: no cover
    pygame = None  # type: ignore


class App:
    """
    Minimal app shell:
      - Initializes pygame (with safe fallback to headless 'dummy' driver if needed)
      - Owns the window/screen, clock, state stack
      - Provides push_state/pop_state/replace helpers used by UI states
    """

    def __init__(self, width: int = 1280, height: int = 720, title: str = "D20 Fight Club") -> None:
        self.width = width
        self.height = height
        self.title = title
        self.data: dict[str, Any] = {}
        self.running: bool = True
        self._stack: List[Any] = []

        self.screen = None
        self.clock = None

        self._init_pygame()

    # --------------- init / teardown ---------------

    def _init_pygame(self) -> None:
        """Initialize pygame and a display surface. Fall back to 'dummy' if a video driver is unavailable."""
        if pygame is None:
            return
        try:
            pygame.init()
            pygame.display.set_caption(self.title)
            self.screen = pygame.display.set_mode((self.width, self.height))
        except Exception:
            # Headless fallback for test environments / CI
            try:
                pygame.quit()
            except Exception:
                pass
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
            pygame.init()
            try:
                pygame.display.set_caption(self.title)
                self.screen = pygame.display.set_mode((self.width, self.height))
            except Exception:
                # As a last resort, ensure event module is initialized to satisfy tests calling pygame.event.get()
                pygame.display.init()
                self.screen = None  # no window, but event queue works

        self.clock = pygame.time.Clock()

    def quit(self) -> None:
        self.running = False
        # Do not pygame.quit() here; tests may still call pygame.event.get()

    # --------------- state management ---------------

    def push_state(self, state: Any) -> None:
        """Push an already-constructed state; inject app and call enter()."""
        if hasattr(state, "app") and getattr(state, "app") is None:
            state.app = self  # type: ignore
        elif not hasattr(state, "app"):
            try:
                state.app = self  # type: ignore
            except Exception:
                pass

        self._stack.append(state)
        if hasattr(state, "enter"):
            state.enter()

    def pop_state(self) -> None:
        if not self._stack:
            return
        st = self._stack.pop()
        if hasattr(st, "exit"):
            try:
                st.exit()
            except Exception:
                pass

    def replace_state(self, state: Any) -> None:
        if self._stack:
            self.pop_state()
        self.push_state(state)

    # Safer helpers that construct the state for you (avoid import cycles at callsite)
    def safe_push(self, cls: Type[Any], **kwargs) -> None:
        st = cls(**kwargs)
        self.push_state(st)

    def safe_replace(self, cls: Type[Any], **kwargs) -> None:
        st = cls(**kwargs)
        self.replace_state(st)

    # --------------- main loop utilities ---------------

    def run(self) -> None:
        """Simple loop; states are expected to implement handle_event/update/draw."""
        if pygame is None:
            return
        while self.running:
            dt = self.clock.tick(60) / 1000.0 if self.clock else 0.016

            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                    break
                if self._stack and hasattr(self._stack[-1], "handle_event"):
                    try:
                        if self._stack[-1].handle_event(event):
                            continue
                    except Exception:
                        pass

            # Update / Draw
            if not self._stack:
                continue

            st = self._stack[-1]
            try:
                if hasattr(st, "update"):
                    st.update(dt)
                if self.screen is not None and hasattr(st, "draw"):
                    self.screen.fill((22, 24, 28))
                    st.draw(self.screen)
                    pygame.display.flip()
            except Exception:
                # Keep loop alive even if a state draw/update errors; useful during dev
                pass

    # --------------- misc helpers ---------------

    def apply_resolution(self, res: tuple[int, int]) -> None:
        """Change resolution at runtime and update the surface."""
        if pygame is None:
            return
        self.width, self.height = res
        try:
            self.screen = pygame.display.set_mode(res)
        except Exception:
            # If display is headless dummy, ensure display module stays initialized
            if not pygame.display.get_init():
                pygame.display.init()
            self.screen = None
