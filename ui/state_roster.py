from __future__ import annotations

import pygame
from pygame import Rect
from typing import Any, Dict, List

# ---- Optional real UI kit ----
try:
    from ui.uiutil import Theme, Button, draw_text, panel
except Exception:
    Theme = None
    class Button:
        def __init__(self, rect, label, cb, enabled=True):
            self.rect, self.label, self.cb, self.enabled = rect, label, cb, enabled
        def draw(self, screen):
            pygame.draw.rect(screen, (60,60,70) if self.enabled else (40,40,48), self.rect, border_radius=8)
            font = pygame.font.SysFont("arial", 18)
            screen.blit(font.render(self.label, True, (255,255,255) if self.enabled else (170,170,170)),
                        (self.rect.x+10, self.rect.y+6))
        def handle(self, ev):
            if self.enabled and ev.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(ev.pos):
                self.cb()
    def draw_text(surface, text, x, y, color=(230,230,235), size=20):
        font = pygame.font.SysFont("arial", size)
        surface.blit(font.render(str(text), True, color), (x, y))
    def panel(surface, rect, color=(30,30,38)):
        pygame.draw.rect(surface, color, rect, border_radius=10)

# ---- Helpers ----
def _team_by_tid(teams: List[Dict[str, Any]], tid: int) -> Dict[str, Any] | None:
    for t in teams:
        if int(t.get("tid", t.get("id", -1))) == int(tid):
            return t
    return None

class RosterState:
    """
    Read-only roster viewer for a single team.
    Columns: PID, Name, HP, AC, STR, DEX, CON, INT, WIS, CHA
    """
    def __init__(self, app, career, tid: int):
        self.app = app
        self.career = career
        self.tid = int(tid)

        self.rc_hdr = Rect(20, 20, 860, 50)
        self.rc_grid = Rect(20, 80, 860, 460)
        self.rc_btns = Rect(20, 550, 860, 50)

        self.scroll = 0
        self.row_h = 26

        x = self.rc_btns.x
        self.btn_back = Button(Rect(x, self.rc_btns.y + 8, 140, 34), "Back", self._back)
        self._buttons = [self.btn_back]

    # -------------- events --------------
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self._back(); return
        if ev.type == pygame.MOUSEWHEEL and self.rc_grid.collidepoint(pygame.mouse.get_pos()):
            self.scroll = max(0, self.scroll - ev.y)
        if ev.type == pygame.MOUSEBUTTONDOWN:
            for b in self._buttons:
                b.handle(ev)

    def update(self, dt): pass

    def draw(self, screen):
        screen.fill((12,12,16))
        t = _team_by_tid(getattr(self.career, "teams", []), self.tid) or {"name": f"Team {self.tid}", "fighters": []}
        name = t.get("name", f"Team {self.tid}")
        fighters = list(t.get("fighters", []))

        panel(screen, self.rc_hdr)
        draw_text(screen, f"Roster — {name}", self.rc_hdr.x + 10, self.rc_hdr.y + 12, size=22)

        panel(screen, self.rc_grid, color=(24,24,28))
        self._draw_table(screen, self.rc_grid, fighters)

        for b in self._buttons:
            b.draw(screen)

    # -------------- drawing --------------
    def _draw_table(self, screen, rect: Rect, fighters: List[Dict[str, Any]]):
        cols = [
            ("PID", 60), ("Name", 200), ("HP", 80), ("AC", 60),
            ("STR", 60), ("DEX", 60), ("CON", 60), ("INT", 60), ("WIS", 60), ("CHA", 60),
        ]
        x = rect.x + 10; y = rect.y + 10
        # header
        cx = x
        for title, w in cols:
            draw_text(screen, title, cx, y, (220,220,230), 18)
            cx += w
        y += self.row_h

        # rows
        start = self.scroll
        max_rows = (rect.h - 20) // self.row_h - 1
        vis = fighters[start:start+max_rows]

        for p in vis:
            cx = x
            vals = [
                int(p.get("pid", p.get("id", 0))),
                str(p.get("name", "?")),
                f"{int(p.get('hp', 0))}/{int(p.get('max_hp', p.get('hp', 0)))}",
                int(p.get("ac", p.get("AC", 10))),
                int(p.get("STR", 10)),
                int(p.get("DEX", 10)),
                int(p.get("CON", 10)),
                int(p.get("INT", 8)),
                int(p.get("WIS", 8)),
                int(p.get("CHA", 8)),
            ]
            for (title, w), val in zip(cols, vals):
                draw_text(screen, str(val), cx, y, (230,230,235), 18)
                cx += w
            y += self.row_h

    # -------------- actions --------------
    def _back(self):
        self.app.pop_state()
