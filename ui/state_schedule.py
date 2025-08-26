# ui/state_schedule.py — visible Back + Prev/Next in a fixed top toolbar
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

        self.week_idx = int(getattr(career, "week", 1))
        self.rect_toolbar = pygame.Rect(0, 0, 0, 0)
        self.rect_panel = pygame.Rect(0, 0, 0, 0)

        self.btn_back: Button | None = None
        self.btn_prev: Button | None = None
        self.btn_next: Button | None = None

        self._built = False

    def enter(self) -> None:
        self._build()

    # --- UI ---
    def _build(self):
        W, H = self.app.width, self.app.height
        pad = 16
        toolbar_h = 56

        self.rect_toolbar = pygame.Rect(pad, pad, W - pad * 2, toolbar_h)
        self.rect_panel   = pygame.Rect(pad, self.rect_toolbar.bottom + pad, W - pad * 2, H - (self.rect_toolbar.bottom + pad * 2))

        bw, bh = 140, 44
        yb = self.rect_toolbar.y + (self.rect_toolbar.h - bh) // 2

        # Back on the left; Prev/Next on the right
        self.btn_back = Button(pygame.Rect(self.rect_toolbar.x, yb, bw, bh), "Back", self._back)

        right_x = self.rect_toolbar.right
        self.btn_next = Button(pygame.Rect(right_x - bw, yb, bw, bh), "Next Week", self._next)
        self.btn_prev = Button(pygame.Rect(right_x - bw*2 - 8, yb, bw, bh), "Prev Week", self._prev)

        self._built = True

    def _back(self):
        self.app.pop_state()

    def _prev(self):
        self.week_idx = max(1, self.week_idx - 1)

    def _next(self):
        self.week_idx = min(self.week_idx + 1, 999)

    # --- pygame loop hooks ---
    def handle(self, event) -> None:
        if not self._built:
            return
        self.btn_back.handle(event)
        self.btn_prev.handle(event)
        self.btn_next.handle(event)

    def update(self, dt: float) -> None:
        if not self._built:
            return
        mx, my = pygame.mouse.get_pos()
        self.btn_back.update((mx, my))
        self.btn_prev.update((mx, my))
        self.btn_next.update((mx, my))

    def draw(self, surf) -> None:
        th = self.theme
        surf.fill(th.bg)

        # Toolbar
        draw_panel(surf, self.rect_toolbar, th)
        draw_text(surf, f"Schedule — Week {self.week_idx}", (self.rect_toolbar.centerx, self.rect_toolbar.centery), 26, th.text, align="center")
        self.btn_back.draw(surf, th)
        self.btn_prev.draw(surf, th)
        self.btn_next.draw(surf, th)

        # Content
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
