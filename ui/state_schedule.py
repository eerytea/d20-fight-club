# ui/state_schedule.py
from __future__ import annotations

import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_text, draw_panel

try:
    from core.types import Fixture
except Exception:
    Fixture = object  # type: ignore


class ScheduleState(BaseState):
    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.theme = Theme()
        self._built = False

        self.week_idx = max(1, getattr(career, "week", 1))
        self.btn_prev = None
        self.btn_next = None
        self.btn_back = None

        self.rect_panel = None

    def enter(self) -> None:
        self._build_ui()

    def _build_ui(self):
        W, H = self.app.width, self.app.height
        self.rect_panel = pygame.Rect(16, 60, W - 32, H - 76)
        btn_w, btn_h, gap = 140, 42, 10
        y = self.rect_panel.bottom - (btn_h + 10)

        self.btn_prev = Button(pygame.Rect(self.rect_panel.x + 12, y, btn_w, btn_h), "Prev Week", self._prev)
        self.btn_next = Button(pygame.Rect(self.rect_panel.x + 12 + btn_w + gap, y, btn_w, btn_h), "Next Week", self._next)
        self.btn_back = Button(pygame.Rect(self.rect_panel.right - (btn_w + 12), y, btn_w, btn_h), "Back", self._back)

        self._built = True

    def _prev(self):
        self.week_idx = max(1, self.week_idx - 1)

    def _next(self):
        # Weeks are 1-based; rough cap (won't crash if over)
        self.week_idx = min(self.week_idx + 1, 999)

    def _back(self):
        self.app.pop_state()

    def handle(self, event) -> None:
        self.btn_prev.handle(event)
        self.btn_next.handle(event)
        self.btn_back.handle(event)

    def update(self, dt: float) -> None:
        mx, my = pygame.mouse.get_pos()
        self.btn_prev.update((mx, my))
        self.btn_next.update((mx, my))
        self.btn_back.update((mx, my))

    def draw(self, surf) -> None:
        th = self.theme
        surf.fill(th.bg)

        draw_text(surf, f"Schedule — Week {self.week_idx}", (surf.get_width() // 2, 16), 30, th.text, align="center")
        draw_panel(surf, self.rect_panel, th)

        # List fixtures for week
        y = self.rect_panel.y + 14
        week_fx = [fx for fx in getattr(self.career, "fixtures", []) if getattr(fx, "week", 0) == self.week_idx]
        if not week_fx:
            draw_text(surf, "No fixtures this week.", (self.rect_panel.x + 12, y), 20, th.subt)
        else:
            for fx in week_fx:
                hn = self.career.team_names[fx.home_id] if hasattr(self.career, "team_names") else str(fx.home_id)
                an = self.career.team_names[fx.away_id] if hasattr(self.career, "team_names") else str(fx.away_id)
                status = "vs"
                if getattr(fx, "played", False):
                    status = f"{fx.home_goals}-{fx.away_goals}"
                draw_text(surf, f"{hn} {status} {an}", (self.rect_panel.x + 12, y), 20, th.text)
                y += 24

        self.btn_prev.draw(surf, th)
        self.btn_next.draw(surf, th)
        self.btn_back.draw(surf, th)
