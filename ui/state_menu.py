# ui/state_menu.py
from __future__ import annotations
from typing import Optional, List, Any, Callable

try:
    import pygame
except Exception:
    pygame = None  # type: ignore

# Prefer shared Button if present, but don't hard-require it.
try:
    from .uiutil import Button  # type: ignore
except Exception:
    Button = None  # type: ignore


class _SimpleButton:
    """Fallback button used if uiutil.Button isn't available."""
    def __init__(self, rect, label: str, on_click: Callable[[], None]):
        self.rect = rect
        self.label = label
        self.on_click = on_click
        self.hover = False
        self._font = pygame.font.SysFont("consolas", 22) if pygame else None

    def handle_event(self, e) -> bool:
        if pygame is None:
            return False
        if e.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            self.on_click()
            return True
        return False

    def draw(self, surf) -> None:
        if pygame is None:
            return
        bg = (120, 120, 120) if self.hover else (98, 98, 98)
        pygame.draw.rect(surf, bg, self.rect, border_radius=8)
        pygame.draw.rect(surf, (50, 50, 50), self.rect, 2, border_radius=8)
        t = self._font.render(self.label, True, (20, 20, 20))
        surf.blit(
            t,
            (
                self.rect.x + (self.rect.w - t.get_width()) // 2,
                self.rect.y + (self.rect.h - t.get_height()) // 2,
            ),
        )


class MenuState:
    """
    Clickable main menu.
    __init__ takes no required args so tests can call MenuState().

    App reference is injected by App.push_state; we also guard-draw so
    fonts/buttons are created even if enter() wasn't called.
    """

    def __init__(self, app: Optional[Any] = None) -> None:
        self.app = app
        self._title_font = None
        self._font = None
        self._buttons: List[Any] = []

    # ---- lifecycle ----

    def enter(self) -> None:
        if pygame is None:
            return
        self._ensure_fonts()
        self._layout_buttons()

    def exit(self) -> None:
        pass

    # ---- setup helpers ----

    def _ensure_fonts(self) -> None:
        """Lazy-create fonts if needed; safe to call from draw()."""
        if pygame is None:
            return
        if not pygame.font.get_init():
            pygame.font.init()
        if self._title_font is None:
            self._title_font = pygame.font.SysFont("consolas", 36)
        if self._font is None:
            self._font = pygame.font.SysFont("consolas", 22)

    def _layout_buttons(self) -> None:
        if pygame is None:
            return
        self._buttons.clear()
        # dimensions
        w = getattr(self.app, "width", 1024)
        h = getattr(self.app, "height", 600)
        btn_w, btn_h, gap = 260, 48, 16

        # center column
        x = w // 2 - btn_w // 2
        y = h // 2 - (btn_h * 5 + gap * 4) // 2

        def mk(label: str, fn: Callable[[], None]):
            rect = pygame.Rect(x, y, btn_w, btn_h)
            if Button is not None:
                self._buttons.append(Button(rect, label, on_click=fn))
            else:
                self._buttons.append(_SimpleButton(rect, label, fn))

        mk("New Game", self._new_game);        y += btn_h + gap
        mk("Load Game", self._load_game);      y += btn_h + gap
        mk("Exhibition", self._exhibition);    y += btn_h + gap
        mk("Settings", self._settings);        y += btn_h + gap
        mk("Quit", self._quit)

    # ---- input ----

    def handle_event(self, e) -> bool:
        if pygame is None:
            return False
        for b in self._buttons:
            if b.handle_event(e):
                return True
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self._quit()
            return True
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface) -> None:
        if pygame is None:
            return
        # Self-heal: if fonts/buttons aren't ready (enter() skipped), init now.
        if self._title_font is None or self._font is None:
            self._ensure_fonts()
        if not self._buttons:
            self._layout_buttons()

        w, h = surface.get_size()
        # Title
        title = self._title_font.render("D20 Fight Club", True, (255, 255, 255))
        surface.blit(title, (w // 2 - title.get_width() // 2, 80))
        # Subtitle
        sub = self._font.render("Turn-based exhibition & season manager", True, (220, 220, 220))
        surface.blit(sub, (w // 2 - sub.get_width() // 2, 130))
        # Buttons
        for b in self._buttons:
            b.draw(surface)

    # ---- actions ----

    def _new_game(self) -> None:
        try:
            from ui.state_team_select import TeamSelectState
            if hasattr(self.app, "safe_push"):
                self.app.safe_push(TeamSelectState, app=self.app)
            else:
                self.app.push_state(TeamSelectState(self.app))
        except Exception as e:
            self._message(f"New Game failed:\n{e}")

    def _load_game(self) -> None:
        try:
            from core.save import load_career  # type: ignore
            career = load_career()
            if not career:
                raise RuntimeError("No save found.")
            from ui.state_season_hub import SeasonHubState
            if hasattr(self.app, "safe_push"):
                self.app.safe_push(SeasonHubState, app=self.app, career=career)
            else:
                self.app.push_state(SeasonHubState(self.app, career))
        except Exception as e:
            self._message(f"Load failed:\n{e}")

    def _exhibition(self) -> None:
        try:
            from ui.state_exhibition_picker import ExhibitionPickerState
            if hasattr(self.app, "safe_push"):
                self.app.safe_push(ExhibitionPickerState, app=self.app)
            else:
                self.app.push_state(ExhibitionPickerState(self.app))
        except Exception as e:
            self._message(f"Exhibition failed:\n{e}")

    def _settings(self) -> None:
        try:
            from ui.state_settings import SettingsState
            if hasattr(self.app, "safe_push"):
                self.app.safe_push(SettingsState, app=self.app)
            else:
                self.app.push_state(SettingsState(self.app))
        except Exception as e:
            self._message(f"Settings failed:\n{e}")

    def _quit(self) -> None:
        if hasattr(self.app, "quit"):
            self.app.quit()
            return
        if hasattr(self.app, "running"):
            self.app.running = False
            return
        try:
            pygame.event.post(pygame.event.Event(pygame.QUIT))  # type: ignore
        except Exception:
            pass

    def _message(self, text: str) -> None:
        try:
            from .state_message import MessageState
            if hasattr(self.app, "push_state"):
                self.app.push_state(MessageState(app=self.app, text=text))
            else:
                print(text)
        except Exception:
            print(text)
