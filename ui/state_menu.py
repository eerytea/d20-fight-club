# ui/state_menu.py
from __future__ import annotations

from typing import List, Callable, Optional

try:
    import pygame
except Exception:
    pygame = None  # type: ignore

# Prefer your shared Button; fall back to an inline simple one if not available.
try:
    from .uiutil import Button  # expected: Button(pygame.Rect, label, on_click=callable)
except Exception:
    Button = None  # type: ignore


class _SimpleButton:  # fallback if uiutil.Button isn't available
    def __init__(self, rect, label, on_click: Callable[[], None]):
        self.rect = rect
        self.label = label
        self.on_click = on_click
        self.hover = False
        self._font = pygame.font.SysFont("consolas", 22) if pygame else None

    def handle_event(self, event) -> bool:
        if pygame is None:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.on_click()
                return True
        return False

    def draw(self, surface) -> None:
        if pygame is None:
            return
        bg = (120, 120, 120) if self.hover else (100, 100, 100)
        pygame.draw.rect(surface, bg, self.rect, border_radius=6)
        pygame.draw.rect(surface, (60, 60, 60), self.rect, width=2, border_radius=6)
        txt = self._font.render(self.label, True, (20, 20, 20))
        tx = self.rect.x + (self.rect.w - txt.get_width()) // 2
        ty = self.rect.y + (self.rect.h - txt.get_height()) // 2
        surface.blit(txt, (tx, ty))


class MenuState:
    """
    Start screen with centered title and clickable buttons.
    Matches the style in your screenshot: stacked gray buttons in the middle.
    """

    def __init__(self, app) -> None:
        self.app = app
        self._font = None
        self._small = None
        self._buttons: List = []

    def enter(self) -> None:
        if pygame is None:
            return
        pygame.font.init()
        self._font = pygame.font.SysFont("consolas", 36)
        self._small = pygame.font.SysFont("consolas", 18)
        self._build_buttons()

    def exit(self) -> None:
        pass

    # -------- helpers --------

    def _build_buttons(self) -> None:
        if pygame is None:
            return
        self._buttons.clear()
        w, h = self.app.width, self.app.height
        btn_w, btn_h, gap = 280, 48, 14
        start_y = h // 2 - (btn_h * 5 + gap * 4) // 2  # center block of 5 buttons
        x = (w - btn_w) // 2

        def mk(label: str, fn: Callable[[], None], y: int):
            rect = pygame.Rect(x, y, btn_w, btn_h)
            if Button is not None:
                self._buttons.append(Button(rect, label, on_click=fn))  # type: ignore
            else:
                self._buttons.append(_SimpleButton(rect, label, on_click=fn))

        y = start_y
        mk("New Game", self._new_game, y); y += btn_h + gap
        mk("Load Game", self._load_game, y); y += btn_h + gap
        mk("Play Match", self._play_match, y); y += btn_h + gap
        mk("Settings", self._settings, y); y += btn_h + gap
        mk("Quit", self._quit, y)

    # -------- events / update / draw --------

    def handle_event(self, event) -> bool:
        if pygame is None:
            return False
        # Mouse-only UI (keyboard still works via OS, but we don't rely on it)
        for b in self._buttons:
            if b.handle_event(event):
                return True
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface) -> None:
        if pygame is None:
            return
        w, h = surface.get_size()
        title = self._font.render("D20 Fight Club – Manager", True, (255, 255, 255))  # type: ignore
        surface.blit(title, (w // 2 - title.get_width() // 2, 60))

        # subtitle: "No career loaded" or current team name if you want
        subtitle = "No career loaded"
        try:
            career = self.app.data.get("career")
            if career:
                subtitle = f"Team: {career.team_names[career.user_team_id]}"
        except Exception:
            pass
        sub = self._small.render(subtitle, True, (200, 200, 200))  # type: ignore
        surface.blit(sub, (w // 2 - sub.get_width() // 2, 100))

        # buttons
        for b in self._buttons:
            b.draw(surface)

    # -------- actions --------

    def _new_game(self) -> None:
        try:
            from .state_team_select import TeamSelectState
            self.app.safe_push(TeamSelectState, app=self.app)
        except Exception as e:
            from .state_message import MessageState
            self.app.push_state(MessageState(app=self.app, text=f"New Game failed:\n{e}"))

    def _load_game(self) -> None:
        from .state_message import MessageState
        self.app.push_state(MessageState(app=self.app, text="Load/Save UI coming soon."))

    def _play_match(self) -> None:
        try:
            from .state_exhibition_picker import ExhibitionPickerState
            self.app.safe_push(ExhibitionPickerState, app=self.app)
        except Exception as e:
            from .state_message import MessageState
            self.app.push_state(MessageState(app=self.app, text=f"Play Match failed:\n{e}"))

    def _settings(self) -> None:
        try:
            from .state_settings import SettingsState  # if you have it
            self.app.safe_push(SettingsState, app=self.app)
        except Exception:
            from .state_message import MessageState
            self.app.push_state(MessageState(app=self.app, text="Settings screen not available."))

    def _quit(self) -> None:
        self.app.quit()
