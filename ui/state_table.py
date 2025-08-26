# ui/state_table.py
from __future__ import annotations

import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_text, draw_panel
from core.standings import table_rows_sorted


class TableState(BaseState):
    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.theme = Theme()
        self._built = False

        self.btn_back = None
        self.rect_panel = None

    def enter(self) -> None:
        self._build_ui()

    def _build_ui(self):
        W, H = self.app.width, self.app.height
        self.rect_panel = pygame.Rect(16, 60, W - 32, H - 76)
        btn_w, btn_h = 140, 42
        self.btn_back = Button(pygame.Rect(self.rect_panel.right - (btn_w + 12), self.rect_panel.bottom - (btn_h + 10), btn_w, btn_h), "Back", self._back)
        self._built = True

    def _back(self):
        self.app.pop_state()

    def handle(self, event) -> None:
        self.btn_back.handle(event)

    def update(self, dt: float) -> None:
        mx, my = pygame.mouse.get_pos()
        self.btn_back.update((mx, my))

    def draw(self, surf) -> None:
        th = self.theme
        surf.fill(th.bg)
        draw_text(surf, "Standings", (surf.get_width() // 2, 16), 30, th.text, align="center")
        draw_panel(surf, self.rect_panel, th)

        # Build rows (dict-like rows)
        rows = table_rows_sorted(self.career.table, self.career.h2h)

        # Header
        x0, y = self.rect_panel.x + 12, self.rect_panel.y + 14
        draw_text(surf, "Pos  Team                 P  W  D  L   K  KD  PTS", (x0, y), 20, th.subt)
        y += 26

        for i, r in enumerate(rows, start=1):
            name = self.career.team_names[r["tid"]] if hasattr(self.career, "team_names") else str(r["tid"])
            line = f"{i:>2}.  {name:<20}  {r['PL']:>2} {r['W']:>2} {r['D']:>2} {r['L']:>2}  {r['K']:>3} {r['KD']:>3}  {r['PTS']:>3}"
            draw_text(surf, line, (x0, y), 20, th.text)
            y += 22

        self.btn_back.draw(surf, th)
