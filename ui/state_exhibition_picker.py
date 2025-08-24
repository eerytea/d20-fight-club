# ui/state_exhibition_picker.py
from __future__ import annotations
from typing import Any, Optional, Callable

try:
    import pygame
except Exception:
    pygame = None  # type: ignore

try:
    from .uiutil import Button  # type: ignore
except Exception:
    Button = None  # type: ignore


def _mk_button(rect, label: str, on_click: Callable[[], None]):
    if Button is not None:
        return Button(rect, label, on_click=on_click)
    return _SimpleButton(rect, label, on_click)


class _SimpleButton:
    def __init__(self, rect, label: str, on_click: Callable[[], None]):
        self.rect = rect
        self.label = label
        self.on_click = on_click
        self.hover = False
        self._font = pygame.font.SysFont("consolas", 20) if pygame else None

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
        surf.blit(t, (self.rect.x + (self.rect.w - t.get_width()) // 2,
                      self.rect.y + (self.rect.h - t.get_height()) // 2))


class ExhibitionPickerState:
    """
    Pick Home/Away teams from a full generated league (temporary career),
    then launch ExhibitionState with those ids.
    """

    def __init__(self, app: Optional[Any] = None) -> None:
        self.app = app
        self._title_font = None
        self._font = None

        self.career = None    # temporary career used for team names/rosters
        self.home_id: Optional[int] = None
        self.away_id: Optional[int] = None

        self._buttons = []

    def enter(self) -> None:
        if pygame is None:
            return
        if not pygame.font.get_init():
            pygame.font.init()
        self._title_font = pygame.font.SysFont("consolas", 28)
        self._font = pygame.font.SysFont("consolas", 20)

        self._build_temp_career(getattr(self.app, "seed", 12345))
        self._layout_buttons()

    def exit(self) -> None:
        pass

    def _build_temp_career(self, seed: int) -> None:
        from core.career import new_career  # type: ignore
        self.career = new_career(seed=seed, user_team_id=None)
        if not getattr(self.career, "team_names", None):
            raise RuntimeError("Career generator returned no teams for exhibition list")

    def _layout_buttons(self) -> None:
        if pygame is None:
            return
        w, h = getattr(self.app, "width", 1024), getattr(self.app, "height", 600)
        y = h - 64
        self._buttons.clear()
        self._buttons.append(_mk_button(pygame.Rect(24, y, 120, 44), "Back", self._back))
        self._buttons.append(_mk_button(pygame.Rect(w - 220, y, 180, 44), "Start Match", self._start_match))

    # ---- input ----

    def handle_event(self, e) -> bool:
        if pygame is None:
            return False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            mx, my = e.pos
            left, right = self._left_list_rect(), self._right_list_rect()
            if left.collidepoint(mx, my):
                idx = self._idx_from_pos(my, left)
                if idx is not None:
                    self.home_id = idx
                    if self.away_id == self.home_id:
                        self.away_id = None
                    return True
            if right.collidepoint(mx, my):
                idx = self._idx_from_pos(my, right)
                if idx is not None:
                    self.away_id = idx
                    if self.home_id == self.away_id:
                        self.home_id = None
                    return True

        for b in self._buttons:
            if b.handle_event(e):
                return True
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self._back()
            return True
        return False

    def update(self, dt: float) -> None:
        pass

    # ---- drawing ----

    def _left_list_rect(self):
        w, h = getattr(self.app, "width", 1024), getattr(self.app, "height", 600)
        return pygame.Rect(24, 64, (w - 72) // 2, h - 64 - 80)

    def _right_list_rect(self):
        w, h = getattr(self.app, "width", 1024), getattr(self.app, "height", 600)
        return pygame.Rect(24 + (w - 72) // 2 + 24, 64, (w - 72) // 2, h - 64 - 80)

    def draw(self, surf) -> None:
        if pygame is None:
            return
        w, h = surf.get_size()
        title = self._title_font.render("Exhibition – Pick Home and Away", True, (255, 255, 255))
        surf.blit(title, (w // 2 - title.get_width() // 2, 16))

        left, right = self._left_list_rect(), self._right_list_rect()
        pygame.draw.rect(surf, (40, 44, 52), left, border_radius=8)
        pygame.draw.rect(surf, (40, 44, 52), right, border_radius=8)

        if self.career:
            self._draw_list(surf, left, self.career.team_names, selected=self.home_id, header="Home")
            self._draw_list(surf, right, self.career.team_names, selected=self.away_id, header="Away")

        for b in self._buttons:
            b.draw(surf)

    def _draw_list(self, surf, rect, names, selected: Optional[int], header: str) -> None:
        hdr = self._font.render(header, True, (220, 220, 220))
        surf.blit(hdr, (rect.x + 10, rect.y + 8))
        line_h = 24
        for i, name in enumerate(names):
            y = rect.y + 32 + i * line_h
            if y + line_h > rect.bottom - 8:
                break
            sel = (i == selected)
            color = (255, 230, 120) if sel else (220, 220, 220)
            t = self._font.render(name, True, color)
            surf.blit(t, (rect.x + 10, y))

    def _idx_from_pos(self, my: int, rect) -> Optional[int]:
        line_h = 24
        idx = (my - (rect.y + 32)) // line_h
        if self.career is None or idx < 0:
            return None
        if idx >= len(self.career.team_names):
            return None
        return int(idx)

    # ---- actions ----

    def _start_match(self) -> None:
        if self.career is None or self.home_id is None or self.away_id is None or self.home_id == self.away_id:
            return
        try:
            # Use existing ExhibitionState which expects (career, home_id, away_id)
            from ui.state_exhibition import ExhibitionState  # type: ignore
            if hasattr(self.app, "safe_push"):
                self.app.safe_replace(ExhibitionState, app=self.app, career=self.career,
                                      home_id=self.home_id, away_id=self.away_id)
            else:
                self.app.replace_state(ExhibitionState(self.app, self.career, self.home_id, self.away_id))
        except Exception as e:
            self._message(f"Couldn't start exhibition:\n{e}")

    def _back(self) -> None:
        if hasattr(self.app, "pop_state"):
            self.app.pop_state()

    def _message(self, text: str) -> None:
        try:
            from .state_message import MessageState
            if hasattr(self.app, "push_state"):
                self.app.push_state(MessageState(app=self.app, text=text))
            else:
                print(text)
        except Exception:
            print(text)
