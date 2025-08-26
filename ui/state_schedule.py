# ui/state_schedule.py — show real team names from career.teams
from __future__ import annotations

import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_text, draw_panel

try:
    from core.types import Fixture
except Exception:
    Fixture = object  # type: ignore


def _team_name(career, tid: int) -> str:
    try:
        return next(t.get("name", f"Team {tid}") for t in career.teams if int(t.get("tid")) == int(tid))
    except StopIteration:
        return f"Team {tid}"


class ScheduleState(BaseState):
    def __init__(self, app, career):
        self.app = app
        self.theme = Theme()
        self.career = career

        self.week_idx = getattr(career, "week", 1)
        self.rect_panel = pygame.Rect(0, 0, 0, 0)

        self.btn_prev: Button | None = None
        self.btn_next: Button | None = None
        self.btn_back: Button | None = None

        self._built = False

    def enter(self) -> None:
        self._build()

    def _build(self):
        W, H = self.app.width, self.app.height
        pad = 16
        self.rect_panel = pygame.Rect(pad, pad + 50, W - pad * 2, H - (pad * 2 + 50))

        bw, bh = 160, 44
        yb = self.rect_panel.bottom + 8
        self.btn_prev = Button(pygame.Rect(self.rect_panel.x, yb, bw, bh), "Prev Week", self._prev)
        self.btn_next = Button(pygame.Rect(self.rect_panel.x + bw + 8, yb, bw, bh), "Next Week", self._next)
        self.btn_back = Button(pygame.Rect(self.rect_panel.right - bw, yb, bw, bh), "Back", self._back)

        self._built = True

    def _prev(self):
        self.week_idx = max(1, self.week_idx - 1)

    def _next(self):
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

        y = self.rect_panel.y + 14
        week_fx = [fx for fx in getattr(self.career, "fixtures", []) if int(getattr(fx, "week", 0)) == int(self.week_idx)]
        if not week_fx:
            draw_text(surf, "No fixtures this week.", (self.rect_panel.x + 12, y), 20, th.subt)
        else:
            for fx in week_fx:
                hn = _team_name(self.career, fx.home_id)
                an = _team_name(self.career, fx.away_id)
                status = "vs"
                if getattr(fx, "played", False):
                    status = f"{getattr(fx, 'kills_home', 0)}-{getattr(fx, 'kills_away', 0)}"
                draw_text(surf, f"{hn} {status} {an}", (self.rect_panel.x + 12, y), 20, th.text)
                y += 24

        self.btn_prev.draw(surf, th)
        self.btn_next.draw(surf, th)
        self.btn_back.draw(surf, th)
