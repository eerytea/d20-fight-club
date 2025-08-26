# ui/state_schedule.py — clean, left-aligned matchups with clipping
from __future__ import annotations
from typing import List, Dict, Any, Tuple
import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_panel, draw_text, get_font

# ---- helpers ---------------------------------------------------------------

def _team_name_map(career) -> Dict[int, str]:
    m: Dict[int, str] = {}
    for t in getattr(career, "teams", []) or []:
        if isinstance(t, dict):
            tid = int(t.get("tid", -1)); nm = str(t.get("name", f"Team {tid}"))
        else:
            tid = int(getattr(t, "tid", -1)); nm = str(getattr(t, "name", f"Team {tid}"))
        if tid >= 0: m[tid] = nm
    return m

def _fixtures_for_week(career, week_idx: int) -> List[Tuple[int, int]]:
    """
    Return list of (home_tid, away_tid) or (a,b). Tries several shapes.
    """
    # 1) explicit helper
    if hasattr(career, "fixtures_for_week"):
        try:
            out = career.fixtures_for_week(week_idx)
            if out: return [(int(a), int(b)) for (a,b) in out]
        except Exception:
            pass
    # 2) schedule attr (list or dict)
    sched = getattr(career, "schedule", None)
    if sched is not None:
        try:
            wk = sched[week_idx] if isinstance(sched, list) else sched.get(week_idx, [])
        except Exception:
            wk = []
        pairs: List[Tuple[int, int]] = []
        for f in wk or []:
            if isinstance(f, dict):
                a = f.get("home_tid", f.get("home", f.get("a", None)))
                b = f.get("away_tid", f.get("away", f.get("b", None)))
            else:
                try:
                    a, b = f
                except Exception:
                    a = b = None
            if a is not None and b is not None:
                pairs.append((int(a), int(b)))
        if pairs: return pairs
    # 3) fallback none
    return []

# ---- state -----------------------------------------------------------------

class ScheduleState(BaseState):
    def __init__(self, app, career, week_index: int):
        self.app = app
        self.career = career
        self.week_index = week_index
        self.theme = Theme()

        self.rect_toolbar = pygame.Rect(0, 0, 0, 0)
        self.rect_panel   = pygame.Rect(0, 0, 0, 0)

        self.btn_back: Button | None = None
        self.btn_prev: Button | None = None
        self.btn_next: Button | None = None

        self.f_title = get_font(36)
        self.f_row   = get_font(28)

    def enter(self) -> None:
        self._layout()

    def _layout(self) -> None:
        W, H = self.app.width, self.app.height
        pad = 16
        toolbar_h = 74
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

        # toolbar
        draw_panel(surf, self.rect_toolbar, th)
        title = f"Schedule — Week {self.week_index + 1}"
        tr = self.f_title.get_rect(title); tr.center = self.rect_toolbar.center
        self.f_title.render_to(surf, tr.topleft, title, th.text)
        self.btn_back.draw(surf, th); self.btn_prev.draw(surf, th); self.btn_next.draw(surf, th)

        # list panel
        draw_panel(surf, self.rect_panel, th)
        inner = self.rect_panel.inflate(-20, -20)

        # clipping
        clip = surf.get_clip(); surf.set_clip(inner)

        # names + fixtures
        name_by_tid = _team_name_map(self.career)
        fixtures = _fixtures_for_week(self.career, self.week_index)

        y = inner.y + 8
        lh = max(30, int(self.f_row.height * 1.25))
        for (a, b) in fixtures:
            left  = name_by_tid.get(int(a), f"Team {a}")
            right = name_by_tid.get(int(b), f"Team {b}")
            line = f"{left}  vs  {right}"
            # STRICT top-left anchor so it never creeps off the panel
            self.f_row.render_to(surf, (inner.x + 10, y), line, th.text)
            y += lh

        surf.set_clip(clip)
