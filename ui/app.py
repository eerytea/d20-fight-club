# ui/app.py
from __future__ import annotations

from typing import Any, Callable, Optional, List

# Import pygame lazily-friendly: tests can import App without pygame installed,
# but actually running the app requires pygame.
try:
    import pygame
except Exception:
    pygame = None  # type: ignore


def _try_import(cls_path: str):
    """Best-effort dynamic import: 'ui.state_menu.MenuState' -> class or None"""
    try:
        mod_path, cls_name = cls_path.rsplit(".", 1)
        mod = __import__(mod_path, fromlist=[cls_name])
        return getattr(mod, cls_name, None)
    except Exception:
        return None


class App:
    """
    Minimal app wrapper:
      - state stack with push/replace/pop
      - safe transitions (show popup instead of crashing)
      - simple pygame loop with FPS cap
    """

    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        title: str = "D20 Fight Club",
        fps_cap: int = 60,
        seed: Optional[int] = None,
    ) -> None:
        self.width = width
        self.height = height
        self.title = title
        self.fps_cap = max(15, int(fps_cap))
        self.seed = seed

        # Free bucket to share things between states (career, settings, etc.)
        self.data: dict[str, Any] = {}

        # State stack: last element is current state
        self._stack: List[Any] = []

        # pygame bits
        self._screen: Optional["pygame.Surface"] = None
        self._clock: Optional["pygame.time.Clock"] = None
        self.running: bool = False

    # ---------------- State stack ----------------

    @property
    def current(self) -> Optional[Any]:
        return self._stack[-1] if self._stack else None

    def push_state(self, state_obj: Any) -> None:
        self._stack.append(state_obj)
        _call_if(state_obj, "enter")

    def replace_state(self, state_obj: Any) -> None:
        if self._stack:
            _call_if(self._stack[-1], "exit")
            self._stack.pop()
        self._stack.append(state_obj)
        _call_if(state_obj, "enter")

    def pop_state(self) -> None:
        if self._stack:
            _call_if(self._stack[-1], "exit")
            self._stack.pop()

    # ------------- Safe transitions -------------

    def safe_push(self, ctor: Callable[..., Any], *args, **kwargs) -> None:
        try:
            self.push_state(ctor(*args, **kwargs))
        except Exception as e:  # pragma: no cover
            self._show_error(f"Couldn't open screen:\n{e}")

    def safe_replace(self, ctor: Callable[..., Any], *args, **kwargs) -> None:
        try:
            self.replace_state(ctor(*args, **kwargs))
        except Exception as e:  # pragma: no cover
            self._show_error(f"Couldn't switch screen:\n{e}")

    # ----------------- Run loop -----------------

    def run(self) -> None:
        if pygame is None:  # pragma: no cover
            raise RuntimeError("pygame is not installed. Install with: pip install pygame")

        pygame.init()
        pygame.display.set_caption(self.title)
        self._screen = pygame.display.set_mode((self.width, self.height))
        self._clock = pygame.time.Clock()
        self.running = True

        # If there's no state yet, push MenuState if present
        if not self._stack:
            MenuState = _try_import("ui.state_menu.MenuState")
            if MenuState is not None:
                self.safe_push(MenuState, app=self)
            else:
                self._show_error("MenuState not found (ui/state_menu.py).")

        last_ticks = pygame.time.get_ticks()
        while self.running:
            # --- events ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                    break
                cur = self.current
                if cur:
                    try:
                        consumed = _call_if(cur, "handle_event", event) is True
                        if consumed:
                            continue
                    except Exception as e:  # pragma: no cover
                        self._show_error(f"Event error:\n{e}")

            # --- update ---
            now = pygame.time.get_ticks()
            dt = (now - last_ticks) / 1000.0
            last_ticks = now

            cur = self.current
            if cur:
                try:
                    _call_if(cur, "update", dt)
                except Exception as e:  # pragma: no cover
                    self._show_error(f"Update error:\n{e}")

            # --- draw ---
            if self._screen is not None:
                try:
                    self._screen.fill((12, 12, 16))
                    cur = self.current
                    if cur:
                        _call_if(cur, "draw", self._screen)
                    pygame.display.flip()
                except Exception as e:  # pragma: no cover
                    self._show_error(f"Draw error:\n{e}")

            # FPS cap
            if self._clock is not None:
                self._clock.tick(self.fps_cap)

        try:
            pygame.quit()
        except Exception:
            pass

    # ---------------- Utilities ----------------

    def quit(self) -> None:
        self.running = False

    def _show_error(self, text: str) -> None:
        MessageState = _try_import("ui.state_message.MessageState")
        if MessageState is not None and self._screen is not None:
            try:
                self.push_state(MessageState(app=self, text=text))
                return
            except Exception:
                pass
        print(text)


def _call_if(obj: Any, name: str, *args, **kwargs) -> Any:
    fn = getattr(obj, name, None)
    if callable(fn):
        return fn(*args, **kwargs)
    return None
