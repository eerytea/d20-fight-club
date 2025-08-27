from __future__ import annotations

import pygame
from pygame import Rect
from typing import Any, Dict, List, Optional

# UI kit fallbacks
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
            txt = font.render(self.label, True, (255,255,255) if self.enabled else (170,170,170))
            screen.blit(txt, (self.rect.x+10, self.rect.y+6))
        def handle(self, ev):
            if self.enabled and ev.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(ev.pos):
                self.cb()
    def draw_text(surface, text, x, y, color=(230,230,235), size=20):
        font = pygame.font.SysFont("arial", size)
        surface.blit(font.render(str(text), True, color), (x, y))
    def panel(surface, rect, color=(30,30,38)):
        pygame.draw.rect(surface, color, rect, border_radius=10)

def _team_by_tid(teams: List[Dict[str, Any]], tid: int) -> Dict[str, Any] | None:
    for t in teams:
        if int(t.get("tid", t.get("id", -1))) == int(tid):
            return t
    return None

class TeamSelectState:
    """
    Choose your team. Left: teams list (scrollable, clipped).
    Right: roster details of the selected team.
    """
    def __init__(self, app, career):
        self.app = app
        self.career = career

        self.rc_hdr  = Rect(20, 20, 860, 50)
        self.rc_left = Rect(20, 80, 380, 460)
        self.rc_right= Rect(420, 80, 460, 460)
        self.rc_btns = Rect(20, 550, 860, 50)

        self.teams: List[Dict[str, Any]] = list(getattr(career, "teams", []))
        self.sel_tid: int = int(getattr(career, "user_tid", 0)) if self.teams else 0

        # left list state
        self.row_h = 26
        self.scroll = 0

        # buttons
        x = self.rc_btns.x
        self.btn_confirm = Button(Rect(x, self.rc_btns.y + 8, 160, 34), "Confirm", self._confirm)
        self.btn_back    = Button(Rect(x + 180, self.rc_btns.y + 8, 140, 34), "Back", self._back)
        self._buttons = [self.btn_confirm, self.btn_back]

    # -------- events --------
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self._back(); return
        if ev.type == pygame.MOUSEWHEEL and self.rc_left.collidepoint(pygame.mouse.get_pos()):
            self.scroll = max(0, self.scroll - ev.y)
        if ev.type == pygame.MOUSEBUTTONDOWN:
            mx, my = ev.pos
            # hit test inside the clipped list
            list_area = Rect(self.rc_left.x + 8, self.rc_left.y + 34, self.rc_left.w - 16, self.rc_left.h - 42)
            if list_area.collidepoint(mx, my):
                idx = (my - list_area.y) // self.row_h + self.scroll
                if 0 <= idx < len(self.teams):
                    self.sel_tid = int(self.teams[idx].get("tid", self.teams[idx].get("id", 0)))
            for b in self._buttons:
                b.handle(ev)

    def update(self, dt): pass

    # -------- drawing --------
    def draw(self, screen):
        screen.fill((12,12,16))
        panel(screen, self.rc_hdr)
        draw_text(screen, "Team Select", self.rc_hdr.x + 10, self.rc_hdr.y + 12, size=22)

        panel(screen, self.rc_left, color=(24,24,28))
        draw_text(screen, "Teams", self.rc_left.x + 10, self.rc_left.y + 8, size=18)
        self._draw_team_list(screen)

        panel(screen, self.rc_right, color=(24,24,28))
        self._draw_team_detail(screen)

        for b in self._buttons:
            b.draw(screen)

    def _draw_team_list(self, screen):
        area = Rect(self.rc_left.x + 8, self.rc_left.y + 34, self.rc_left.w - 16, self.rc_left.h - 42)
        pygame.draw.rect(screen, (18,18,22), area, border_radius=6)
        start = self.scroll
        max_rows = area.h // self.row_h
        rows = self.teams[start:start+max_rows]

        for i, t in enumerate(rows):
            y = area.y + i*self.row_h
            tid = int(t.get("tid", t.get("id", -1)))
            # draw highlight behind the whole row if selected
            if tid == self.sel_tid:
                pygame.draw.rect(screen, (60,60,90), Rect(area.x+2, y+1, area.w-4, self.row_h-2), border_radius=4)
            name = t.get("name", f"Team {tid}")
            draw_text(screen, f"{tid:02d}  {name}", area.x + 8, y + 4, size=18)

    def _draw_team_detail(self, screen):
        team = _team_by_tid(self.teams, self.sel_tid) or {"name": f"Team {self.sel_tid}", "fighters": []}
        draw_text(screen, team.get("name", f"Team {self.sel_tid}"), self.rc_right.x + 10, self.rc_right.y + 8, size=20)
        # simple grid of fighter stats
        cols = [("PID", 60), ("Name", 180), ("HP", 80), ("AC", 60), ("STR", 60), ("DEX", 60)]
        x = self.rc_right.x + 10
        y = self.rc_right.y + 40
        # header
        cx = x
        for title, w in cols:
            draw_text(screen, title, cx, y, (220,220,230), 18)
            cx += w
        y += 26
        # rows
        fighters: List[Dict[str, Any]] = list(team.get("fighters", []))
        max_rows = (self.rc_right.h - 80) // 24
        for p in fighters[:max_rows]:
            cx = x
            vals = [
                int(p.get("pid", p.get("id", 0))),
                str(p.get("name", "?")),
                f"{int(p.get('hp', 0))}/{int(p.get('max_hp', p.get('hp', 0)))}",
                int(p.get("ac", p.get("AC", 10))),
                int(p.get("STR", 10)),
                int(p.get("DEX", 10)),
            ]
            for (title, w), val in zip(cols, vals):
                draw_text(screen, str(val), cx, y, (230,230,235), 18); cx += w
            y += 24

    # -------- actions --------
    def _confirm(self):
        try:
            self.career.user_tid = int(self.sel_tid)
        except Exception:
            pass
        self.app.pop_state()

    def _back(self):
        self.app.pop_state()
