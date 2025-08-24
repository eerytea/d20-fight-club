# ui/app.py
from __future__ import annotations

import os
import time
from typing import Any, Optional, List, Callable

# pygame is required to actually run the app, but tests only import App.
# If pygame isn't installed, importing App will still work; running will error with a nice message.
try:
    import pygame
except Exception:  # pragma: no cover
    pygame = None  # type: ignore


# -------- tiny helpers --------

def _try_import_message_state():
    try:
        from .state_message import MessageState
        return MessageState
    except Exception:
        return None


def _try_import_menu_state():
    try:
        from .state_menu import MenuState
        return MenuState
    except Exception:
        return None


# -------- The App --------

class App:
    """
    Minimal app wrapper with a state stack and a safe game loop.

    Usage:
        app = App()
        app.run()
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

        # Arbitrary place to stash objects shared across states (career, settings, etc.)
        self.data: dict[str, Any] = {}

        # State stack: last item is the current state
        self._stack: List[Any] = []

        # pygame bits
        self._clock: Optional["pygame.time.Clock"] = None
        self._screen: Optional["pygame.Surface"] = None
        self.running: bool = False

        # If we crashed last time, leave a breadcrumb in saves/last_crash.txt
        self._crash_note_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saves", "last_crash.txt")

    # ---------- state stack API ----------

    @property
    def current(self) -> Optional[Any]:
        return self._stack[-1] if self._stack else None

    def push_state(self, state_obj: Any) -> None:
        """Push a constructed state object onto the stack."""
        self._stack.append(state_obj)
        _call(state_obj, "enter")

    def replace_state(self, state_obj: Any) -> None:
        """Replace the top state with another constructed state object."""
        if self._stack:
            _call(self._stack[-1], "exit")
            self._stack.pop()
        self._stack.append(state_obj)
        _call(state_obj, "enter")

    def pop_state(self) -> None:
        """Pop the current state."""
        if self._stack:
            _call(self._stack[-1], "exit")
            self._stack.pop()

    # ---------- safe transitions (constructor + args) ----------

    def safe_push(self, state_ctor: Callable[..., Any], *args, **kwargs) -> None:
        """Construct and push a state; on error, show MessageState instead of crashing."""
        try:
            state = state_ctor(*args, **kwargs)
            self.push_state(state)
        except Exception as e:  # pragma: no cover
            self._show_error(f"Couldn't open screen:\n{e}")

    def safe_replace(self, state_ctor: Callable[..., Any], *args, **kwargs) -> None:
        """Construct and replace top state; on error, show MessageState instead of crashing."""
        try:
            state = state_ctor(*args, **kwargs)
            self.replace_state(state)
        except Exception as e:  # pragma: no cover
            self._show_error(f"Couldn't switch screen:\n{e}")

    # ---------- run loop ----------

    def run(self) -> None:
        """Initialize pygame and enter the main loop."""
        if pygame is None:  # pragma: no cover
            raise RuntimeError("pygame is not installed. Install with: pip install pygame")

        pygame.init()
        pygame.display.set_caption(self.title)
        self._screen = pygame.display.set_mode((self.width, self.height))
        self._clock = pygame.time.Clock()
        self.running = True

        # If we have a crash breadcrumb, offer to show it
        self._maybe_show_crash_note()

        # Start at MenuState if stack is empty and MenuState is available
        if not self._stack:
            MenuState = _try_import_menu_state()
            if MenuState:
                # Prefer safe_* so we don't crash on bad constructors
                self.safe_push(MenuState, app=self)
            else:
                self._show_error("MenuState not found. Please implement ui/state_menu.py")

        # Main loop
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
                        # If state returns True, it consumed the event
                        consumed = _call(cur, "handle_event", event) is True
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
                    _call(cur, "update", dt)
                except Exception as e:  # pragma: no cover
                    self._show_error(f"Update error:\n{e}")

            # --- draw ---
            if self._screen is not None:
                try:
                    self._screen.fill((12, 12, 16))
                    if cur:
                        _call(cur, "draw", self._screen)
                    pygame.display.flip()
                except Exception as e:  # pragma: no cover
                    self._show_error(f"Draw error:\n{e}")

            # FPS cap
            if self._clock is not None:
                self._clock.tick(self.fps_cap)

        # Cleanup
        try:
            pygame.quit()
        except Exception:
            pass

    # ---------- utilities ----------

    def quit(self) -> None:
        """Request the app to exit after this frame."""
        self.running = False

    def _show_error(self, text: str) -> None:
        """Push a MessageState popup if available; otherwise print to console."""
        MessageState = _try_import_message_state()
        if MessageState and self._screen is not None:
            try:
                # Push a temporary message. User can Esc/Enter to dismiss (depending on your MessageState).
                self.push_state(MessageState(text=text))
                return
            except Exception:
                pass
        print(text)

    def _maybe_show_crash_note(self) -> None:
        """If saves/last_crash.txt exists, show a small message with the log path."""
        try:
            if os.path.exists(self._crash_note_path):
                with open(self._crash_note_path, "r", encoding="utf-8") as f:
                    path = f.read().strip()
                MessageState = _try_import_message_state()
                if MessageState:
                    self.push_state(MessageState(text=f"Previously crashed.\nLog: {path}"))
                # Optionally remove the breadcrumb so it shows only once:
                # os.remove(self._crash_note_path)
        except Exception:
            # Non-fatal if we can't read it
            pass


# -------- internal: safe method caller --------

def _call(obj: Any, name: str, *args, **kwargs) -> Any:
    """Call obj.name(*args) if present; otherwise no-op."""
    fn = getattr(obj, name, None)
    if callable(fn):
        return fn(*args, **kwargs)
    return None
