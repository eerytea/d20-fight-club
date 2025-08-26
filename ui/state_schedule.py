# ui/state_schedule.py — left-aligned weekly schedule with clipping
from __future__ import annotations
from typing import Dict, List, Tuple
import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_panel, draw_text, get_font


def _team_name_map(career) -> Dict[int, str]:
    m: Dict[int, str] = {}
    for t in getattr(career, "teams", []) or []:
        tid = int(getattr(t, "tid", t.get("tid", -1)) if not isinstance(t, dict) else t.get("tid", -1))
        nm  = str(getattr(t, "name", t.get("name", f"Team {tid}")) if not isinstance(t, dict) else t.get("name", f"Team {tid}"))
        if tid >= 0:
            m[tid] = nm
    return m

def _fixtures_for_week(career, week_idx: int) -> List[Tuple[int, int]]:
    if hasattr(career, "fixtures_for_week"):
        try:
            out = career.fixtures_for_week(week_idx)
            if out:
                return [(int(a), int(b)) for (a, b) in out]
        except Exception:
            pass

    sched = getattr(career, "schedule", None)
    wk = []
    if isinstance(sched, list):
        wk = sched[week_idx] if 0 <= week_idx < len(sched) else []
    elif isinstance(sched, dict):
        wk = sched.get(week_idx, [])

    pairs: List[Tuple[int, int]] = []
    for f in wk or []:
        if isinstance(f, dict):
            a = f.get("home_tid", f.get("home", f.get("a")))
            b = f.get("away_tid", f.get("away", f.get("b")))
        else:
            try:
                a, b = f
            except Exception:
                a = b = None
        if a is not None and b is not None:
            pairs.append((int(a), int(b)))
    return pairs


class ScheduleState(BaseState):
    def __init__(self, app, career, week_index: int):
        self.app = app
        self.career = career
        self.week_index = int(week_index)
        self.theme = Theme()

        self.rect_toolbar = pygame.Rect(0, 0, 0, 0)
        self.rect_panel   = pygame.Rect(0, 0, 0, 0)

        self.btn_back: Button | None = None
        self.btn_prev: Button | None = None
        self.btn_next: Button | None = None

        self.f_title = get_font(40)
        self.f_row   = get_font(28)

    def enter(self) -> None:
        self._layout()

    def _layout(self) -> None:
        W, H = self.app.width, self.app.height
        pad = 16
        toolbar_h = 80
        self.rect_toolbar = pygame.Rect(pad, pad, W - pad * 2, toolbar_h)
        self.rect_panel   = pygame.Rect(pad, self.rect_toolbar.bottom + pad, W - pad * 2, H - (toolbar_h + pad * 3))

        bw, bh = 160, 46
        by = self.rect_toolbar.y + (self.rect_toolbar.h - bh) // 2
        self.btn_back = Button(pygame.Rect(self.rect_toolbar.x, by, bw, bh), "Back", self._back)
        self.btn_prev = Button(pygame.Rect(self.rect_toolbar.right - (bw * 2 + 12), by, bw, bh), "Prev Week", self._prev)
        self.btn_next = Button(pygame.Rect(self.rect_toolbar.right - bw, by, bw, bh), "Next Week", self._next)

    def _back(self) -> None: self.app.pop_state()
    def _prev(self) -> None: self.week_index = max(0, self.week_index - 1)
    def _next(self) -> None: self.week_index = self.week_index + 1

    def handle(self, event) -> None:
        self.btn_back.handle(event); self.btn_prev.handle(event); self.btn_next.handle(event)

    def update(self, dt: float) -> None:
        mp = pygame.mouse.get_pos()
        self.btn_back.update(mp); self.btn_prev.update(mp); self.btn_next.update(mp)

    def draw(self, surf) -> None:
        th = self.theme
        surf.fill(th.bg)

        draw_panel(surf, self.rect_toolbar, th)
        title = f"Schedule — Week {self.week_index + 1}"
        tr = self.f_title.get_rect(title); tr.center = self.rect_toolbar.center
        self.f_title.render_to(surf, tr.topleft, title, th.text)
        self.btn_back.draw(surf, th); self.btn_prev.draw(surf, th); self.btn_next.draw(surf, th)

        draw_panel(surf, self.rect_panel, th)
        inner = self.rect_panel.inflate(-20, -20)

        # clipping region for rows
        clip = surf.get_clip(); surf.set_clip(inner)

        names = _team_name_map(self.career)
        fixtures = _fixtures_for_week(self.career, self.week_index)

        y = inner.y + 8
        lh = max(30, int(self.f_row.height * 1.25))
        for (a, b) in fixtures:
            left  = names.get(int(a), f"Team {a}")
            right = names.get(int(b), f"Team {b}")
            self.f_row.render_to(surf, (inner.x + 10, y), f"{left}  vs  {right}", th.text)
            y += lh

        surf.set_clip(clip)
