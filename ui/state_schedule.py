# ui/state_schedule.py — robust weekly schedule reader
from __future__ import annotations
from typing import Dict, List, Tuple, Any
import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_panel, get_font


def _get(obj: Any, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

def _safe_int(v, default: int = -1) -> int:
    try:
        if v is None: return default
        return int(v)
    except Exception:
        return default

def _team_id_from(obj: Any, default: int = -1) -> int:
    for k in ("tid", "team_id", "id", "index"):
        val = _get(obj, k, None)
        if val is not None:
            try:
                return int(val)
            except Exception:
                pass
    return default

def _name_from(obj: Any, default: str = "Team") -> str:
    for k in ("name", "full_name", "display_name", "abbr", "short"):
        v = _get(obj, k, None)
        if v:
            return str(v)
    return default

def _team_name_map(career) -> Dict[int, str]:
    m: Dict[int, str] = {}
    if hasattr(career, "team_name"):
        for t in getattr(career, "teams", []) or []:
            tid = _team_id_from(t, -1)
            if tid >= 0:
                try: m[tid] = str(career.team_name(tid))
                except Exception: pass
    if m:
        return m
    for t in getattr(career, "teams", []) or []:
        tid = _team_id_from(t, -1)
        nm = _name_from(t, f"Team {tid}")
        if tid >= 0: m[tid] = nm
    tn = getattr(career, "team_names", None)
    if isinstance(tn, dict):
        for k, v in tn.items():
            try: m[int(k)] = str(v)
            except Exception: pass
    return m

def _pair_from_any(item) -> Tuple[int, int] | None:
    if item is None: return None
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        try: return (int(item[0]), int(item[1]))
        except Exception: return None
    if isinstance(item, dict):
        for hk, ak in (("home_tid", "away_tid"), ("home_id", "away_id"),
                       ("home", "away"), ("h", "v"), ("a", "b")):
            ha = item.get(hk, None); aw = item.get(ak, None)
            if ha is not None and aw is not None:
                try: return (int(ha), int(aw))
                except Exception: pass
    ha = _get(item, "home_tid", _get(item, "home", _get(item, "h", None)))
    aw = _get(item, "away_tid", _get(item, "away", _get(item, "v", None)))
    if ha is not None and aw is not None:
        try: return (int(ha), int(aw))
        except Exception: return None
    return None

def _fixtures_for_week(career, week_idx: int) -> List[Tuple[int, int]]:
    for meth in ("fixtures_for_week", "get_fixtures_for_week", "week_fixtures", "fixtures_in_week"):
        fn = getattr(career, meth, None)
        if callable(fn):
            try:
                out = fn(week_idx)
                pairs = []
                for it in out or []:
                    p = _pair_from_any(it)
                    if p: pairs.append(p)
                if pairs: return pairs
            except Exception:
                pass

    candidates = ["schedule", "fixtures", "fixtures_by_week", "rounds", "weeks"]
    for name in candidates:
        obj = getattr(career, name, None)
        if obj is None: continue

        if isinstance(obj, list):
            wk = obj[week_idx] if 0 <= week_idx < len(obj) else []
            pairs = []
            for it in wk or []:
                p = _pair_from_any(it)
                if p: pairs.append(p)
            if pairs: return pairs

        if isinstance(obj, dict):
            wk = obj.get(week_idx, [])
            pairs = []
            for it in wk or []:
                p = _pair_from_any(it)
                if p: pairs.append(p)
            if pairs: return pairs

        if isinstance(obj, list):
            pairs = []
            for it in obj:
                w = _get(it, "week", _get(it, "round", _get(it, "week_index", None)))
                if w is not None and int(w) == int(week_idx):
                    p = _pair_from_any(it)
                    if p: pairs.append(p)
            if pairs: return pairs

    return []

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
