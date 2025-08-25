# ui/state_menu.py
from __future__ import annotations

import pygame
from typing import Optional, Callable, List

try:
    from .uiutil import Theme, Button, draw_text
    HAS_UIKIT = True
except Exception:
    HAS_UIKIT = False
    class Theme:
        def __init__(self):
            self.bg = (20, 24, 28)
            self.btn_bg = (50, 55, 64)
            self.btn_bg_hover = (70, 75, 84)
            self.btn_text = (240, 240, 245)
        @staticmethod
        def default(): return Theme()
    def draw_text(surf, text, pos, color=(230,230,235), size=28):
        font = pygame.font.SysFont(None, size)
        surf.blit(font.render(text, True, color), pos)
    class Button:
        def __init__(self, rect, text, on_click=None, enabled=True):
            self.rect = pygame.Rect(rect)
            self.text = text
            self.on_click = on_click
            self.enabled = enabled
            self._hover = False
            self._font = pygame.font.SysFont(None, 24)
        def handle_event(self, ev):
            if not self.enabled: return
            if ev.type == pygame.MOUSEMOTION:
                self._hover = self.rect.collidepoint(ev.pos)
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                if self.rect.collidepoint(ev.pos) and callable(self.on_click):
                    self.on_click()
        def draw(self, surf, theme: Theme):
            col = (100,100,110) if not self.enabled else (theme.btn_bg_hover if self._hover else theme.btn_bg)
            pygame.draw.rect(surf, col, self.rect, border_radius=10)
            txt = self._font.render(self.text, True, theme.btn_text)
            surf.blit(txt, txt.get_rect(center=self.rect.center))

# Optional states
try:
    from .state_team_select import TeamSelectState
except Exception:
    TeamSelectState = None
try:
    from .state_exhibition_picker import ExhibitionPickerState
except Exception:
    ExhibitionPickerState = None
try:
    from .state_settings import SettingsState
except Exception:
    SettingsState = None

# Our new roster browser
try:
    from .state_roster_browser import RosterBrowserState
except Exception:
    RosterBrowserState = None


class MenuState:
    """
    Allows construction with no args (tests do MenuState()).
    App will be attached later via app.push_state(...).
    """
    def __init__(self, app: Optional[object] = None):
        self.app = app
        self.theme: Theme = Theme.default() if hasattr(Theme, "default") else Theme()
        self.screen = None  # filled when app is attached
        self.W, self.H = 800, 600  # safe defaults
        self.title_font = pygame.font.SysFont(None, 48)
        self.buttons: List[Button] = []
        self._built = False
        if self.app is not None:
            self._attach_app(self.app)

    # App/framework may set state.app directly; build lazily on first draw/update.
    def _attach_app(self, app):
        self.app = app
        if hasattr(app, "screen"):
            self.screen = app.screen
            self.W, self.H = self.screen.get_size()
        self._build_ui()
        self._built = True

    def _ensure_built(self):
        if not self._built and getattr(self, "app", None) is not None:
            self._attach_app(self.app)

    def _push(self, state_cls, *args, **kwargs):
        if hasattr(self.app, "push_state"):
            self.app.push_state(state_cls(self.app, *args, **kwargs))

    def _build_ui(self):
        btn_w, btn_h = 340, 54
        gap = 14
        total_h = 6 * btn_h + 5 * gap  # 6 buttons including Roster
        x = (self.W - btn_w) // 2
        y = (self.H - total_h) // 2 + 30

        def maybe(label: str, rect: pygame.Rect, state_cls: Optional[type], builder: Optional[Callable]=None):
            enabled = state_cls is not None or builder is not None
            if not enabled:
                return Button(rect, f"{label} (missing)", None, enabled=False)
            def go():
                if builder: builder()
                else: self._push(state_cls)
            return Button(rect, label, go, enabled=True)

        self.buttons = []
        self.buttons.append(maybe("New Game", pygame.Rect(x, y, btn_w, btn_h), TeamSelectState)); y += btn_h + gap
        try:
            from .state_load import LoadState
            self.buttons.append(maybe("Load", pygame.Rect(x, y, btn_w, btn_h), LoadState))
        except Exception:
            self.buttons.append(Button(pygame.Rect(x, y, btn_w, btn_h), "Load (coming soon)", None, enabled=False))
        y += btn_h + gap
        self.buttons.append(maybe("Exhibition", pygame.Rect(x, y, btn_w, btn_h), ExhibitionPickerState)); y += btn_h + gap
        self.buttons.append(
            Button(pygame.Rect(x, y, btn_w, btn_h),
                   "Roster",
                   (lambda: self._push(RosterBrowserState)) if RosterBrowserState else None,
                   enabled=bool(RosterBrowserState))
        ); y += btn_h + gap
        self.buttons.append(maybe("Settings", pygame.Rect(x, y, btn_w, btn_h), SettingsState)); y += btn_h + gap
        self.buttons.append(Button(pygame.Rect(x, y, btn_w, btn_h), "Quit", self._quit))

    def _quit(self):
        if hasattr(self.app, "quit"):
            self.app.quit()
        else:
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    # ---- state api ----
    def handle_event(self, ev):
        self._ensure_built()
        if ev.type == pygame.KEYUP and ev.key in (pygame.K_ESCAPE, pygame.K_q):
            self._quit(); return
        for b in self.buttons:
            b.handle_event(ev)

    def update(self, dt: float):
        self._ensure_built()

    def draw(self, surf):
        self._ensure_built()
        if surf is None and self.screen is not None:
            surf = self.screen
        if surf is None:
            return
        surf.fill(self.theme.bg if hasattr(self.theme, "bg") else (20, 24, 28))
        draw_text(surf, "D20 Fight Club", (40, 40), (220, 225, 230), 48)
        for b in self.buttons:
            b.draw(surf, self.theme)
