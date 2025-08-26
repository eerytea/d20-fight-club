# ui/state_table.py — visible Back in a fixed top toolbar
from __future__ import annotations

import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_text, draw_panel
from core.standings import table_rows_sorted


def _get(r, keys, default=0):
    if isinstance(keys, str):
        keys = (keys,)
    if isinstance(r, dict):
        for k in keys:
            if k in r:
                return r.get(k, default)
        return default
    for k in keys:
        if hasattr(r, k):
            return getattr(r, k)
    return default


def _team_name(career, tid: int) -> str:
    try:
        return next(t.get("name", f"Team {tid}") for t in career.teams if int(t.get("tid")) == int(tid))
    except StopIteration:
        return f"Team {tid}"


class TableState(BaseState):
    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.theme = Theme()

        self.rect_toolbar = pygame.Rect(0, 0, 0, 0)
        self.rect_panel = pygame.Rect(0, 0, 0, 0)
        self.btn_back: Button | None = None
        self._built = False

    def enter(self) -> None:
        self._build()

    # --- UI ---
    def _build(self) -> None:
        W, H = self.app.width, self.app.height
        pad = 16
        toolbar_h = 56

        self.rect_toolbar = pygame.Rect(pad, pad, W - pad * 2, toolbar_h)
        self.rect_panel   = pygame.Rect(pad, self.rect_toolbar.bottom + pad, W - pad * 2, H - (self.rect_toolbar.bottom + pad * 2))

        bw, bh = 140, 44
        yb = self.rect_toolbar.y + (self.rect_toolbar.h - bh) // 2
        self.btn_back = Button(pygame.Rect(self.rect_toolbar.x, yb, bw, bh), "Back", self._back)

        self._built = True

    def _back(self):
        self.app.pop_state()

    # --- pygame loop hooks ---
    def handle(self, event) -> None:
        if not self._built:
            return
        self.btn_back.handle(event)

    def update(self, dt: float) -> None:
        if not self._built:
            return
        mx, my = pygame.mouse.get_pos()
        self.btn_back.update((mx, my))

    def draw(self, surf) -> None:
        th = self.theme
        surf.fill(th.bg)

        # Toolbar
        draw_panel(surf, self.rect_toolbar, th)
        draw_text(surf, "Standings", (self.rect_toolbar.centerx, self.rect_toolbar.centery), 26, th.text, align="center")
        self.btn_back.draw(surf, th)

        # Content
        draw_panel(surf, self.rect_panel, th)
        rows = table_rows_sorted(self.career.table, self.career.h2h)

        x0, y = self.rect_panel.x + 12, self.rect_panel.y + 14
        draw_text(surf, "Pos  Team                 P  W  D  L   K  KD  PTS", (x0, y), 20, th.subt)
        y += 26

        for i, r in enumerate(rows, start=1):
            tid = _get(r, ("tid", "team_id", "id"))
            name = _team_name(self.career, tid)

            PL = _get(r, ("PL", "played", "P"))
            W  = _get(r, ("W", "wins"))
            D  = _get(r, ("D", "draws"))
            L  = _get(r, ("L", "losses"))
            K  = _get(r, ("K", "kills", "goals_for"))
            KD = _get(r, ("KD", "kill_diff", "gd", "goal_diff"))
            PTS= _get(r, ("PTS", "points", "pts"))

            line = f"{i:>2}.  {name:<20}  {PL:>2} {W:>2} {D:>2} {L:>2}  {K:>3} {KD:>3}  {PTS:>3}"
            draw_text(surf, line, (x0, y), 20, th.text)
            y += 22
