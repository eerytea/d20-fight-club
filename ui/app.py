# ui/app.py
from __future__ import annotations

import os
import random
from typing import Any, List, Type, Optional

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
      - Supports fps_cap and exposes a deterministic seed + rng for UI screens
    """

    def __init__(
        self,
        width: int = 1280,
        height:  int = 720,
        title:   str = "D20 Fight Club",
        fps_cap: Optional[int] = 60,
        seed:    Optional[int] = None,
    ) -> None:
        self.width = width
        self.height = height
        self.title = title
        self.data: dict[str, Any] = {}
        self.running: bool = True
        self._stack: List[Any] = []

        self.screen = None
        self.clock = None
        self.fps_cap = fps_cap or 60

        # Deterministic RNG for UI helpers (team lists, random previews, etc.)
        self.seed: int = int(seed) if seed is not None else random.randint(1, 2_147_483_647)
        self.rng = random.Random(self.seed)

        self._init_pygame()

    # ---------- NEW: seed helpers ----------

    def derive_seed(self, *parts: object) -> int:
        """Stable child seed derived from app.seed and arbitrary parts (week, fixture idx, etc.)."""
        from core.rng import mix  # local import to avoid hard coupling at import time
        return mix(self.seed, *parts)

    def rng_child(self, *parts: object) -> random.Random:
        """Child RNG derived from app.seed and parts."""
        from core.rng import child_rng
        return child_rng(self.seed, *parts)

    # --------------- init / teardown ---------------

    def _init_pygame(self) -> None:
        if pygame is None:
            return
        try:
            pygame.init()
            pygame.display.set_caption(self.title)
            self.screen = pygame.display.set_mode((self.width, self.height))
        except Exception:
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
                pygame.display.init()
                self.screen = None
        self.clock = pygame.time.Clock()

    def quit(self) -> None:
        self.running = False

    # --------------- state management ---------------

    def push_state(self, state: Any) -> None:
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

    def safe_push(self, cls: Type[Any], **kwargs) -> None:
        st = cls(**kwargs)
        self.push_state(st)

    def safe_replace(self, cls: Type[Any], **kwargs) -> None:
        st = cls(**kwargs)
        self.replace_state(st)

    # --------------- main loop ---------------

    def run(self) -> None:
        if pygame is None:
            return
        while self.running:
            cap = max(1, int(self.fps_cap)) if self.fps_cap else 60
            dt = self.clock.tick(cap) / 1000.0 if self.clock else 0.016

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
                pass

    # --------------- misc ---------------

    def apply_resolution(self, res: tuple[int, int]) -> None:
        if pygame is None:
            return
        self.width, self.height = res
        try:
            self.screen = pygame.display.set_mode(res)
        except Exception:
            if not pygame.display.get_init():
                pygame.display.init()
            self.screen = None

    def set_fps_cap(self, fps: Optional[int]) -> None:
        self.fps_cap = fps or 60

    @property
    def state(self) -> Any | None:
        return self._stack[-1] if self._stack else None
