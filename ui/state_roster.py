from __future__ import annotations

import pygame
from pygame import Rect
from typing import Any, Dict, List, Optional

# Shared fighter adapter
try:
    from core.adapters import as_fighter_dict
except Exception:
    def as_fighter_dict(p, default_team_id=0, default_pid=0):
        d = dict(p) if isinstance(p, dict) else p.__dict__.copy()
        d.setdefault("pid", d.get("id", default_pid))
        d.setdefault("name", d.get("n", f"P{d['pid']}"))
        d.setdefault("team_id", d.get("tid", default_team_id))
        d.setdefault("hp", d.get("HP", 10))
        d.setdefault("max_hp", d.get("max_hp", d.get("HP_max", d.get("hp", 10))))
        d.setdefault("ac", d.get("AC", 10))
        d.setdefault("alive", d.get("alive", True))
        return d

# Tiny UI kit fallback
try:
    from ui.uiutil import Theme, Button, draw_text, panel
except Exception:
    Theme = None
    class Button:
        def __init__(self, rect, label, cb, enabled=True):
            self.rect, self.label, self.cb, self.enabled = rect, label, cb, enabled
        def draw(self, screen):
            pygame.draw.rect(screen, (60,60,70) if self.enabled else (40,40,48), self.rect, border_radius=6)
            font = pygame.font.SysFont("arial", 18)
            screen.blit(font.render(self.label, True, (255,255,255) if self.enabled else (180,180,180)),
                        (self.rect.x+8, self.rect.y+6))
        def handle(self, ev):
            if self.enabled and ev.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(ev.pos):
                self.cb()
    def draw_text(surface, text, x, y, color=(230,230,235), size=20):
        font = pygame.font.SysFont("arial", size)
        surface.blit(font.render(str(text), True, color), (x, y))
    def panel(surface, rect, color=(30,30,38)):
        pygame.draw.rect(surface, color, rect, border_radius=8)

def _find_team(career, tid) -> Optional[Dict[str, Any]]:
    teams = getattr(career, "teams", [])
    for t in teams:
        if str(t.get("tid", t.get("id"))) == str(tid):
            return t
    return None

class RosterState:
    """
    Shows one team’s roster (defaults to user's team).
    Left: player list. Right: selected player details.
    """
    def __init__(self, app, career, tid: Optional[int] = None):
        self.app = app
        self.career = career
        self.tid = tid if tid is not None else getattr(career, "user_tid", 0)

        self.team = _find_team(career, self.tid) or {"tid": self.tid, "name": career.team_name(self.tid), "fighters": []}
        roster = self.team.get("fighters") or self.team.get("players") or []
        # normalize
        self.roster: List[Dict[str, Any]] = [as_fighter_dict(p, default_team_id=0, default_pid=i) for i, p in enumerate(roster)]

        self.sel_ix = 0 if self.roster else -1
        self.scroll = 0

        # layout
        self.rc_hdr = Rect(20, 20, 860, 40)
        self.rc_left = Rect(20, 70, 420, 470)
        self.rc_right = Rect(460, 70, 420, 470)
        self.rc_btns = Rect(20, 550, 860, 46)
        self._build_buttons()

    def _build_buttons(self):
        self.btn_back = Button(Rect(self.rc_btns.x, self.rc_btns.y, 120, 36), "Back", self._back)
        self._buttons = [self.btn_back]

    # events
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self._back()
                return
            if ev.key in (pygame.K_DOWN, pygame.K_s):
                self.sel_ix = min(self.sel_ix + 1, len(self.roster) - 1)
            if ev.key in (pygame.K_UP, pygame.K_w):
                self.sel_ix = max(self.sel_ix - 1, 0)
        if ev.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - ev.y)
        if ev.type == pygame.MOUSEBUTTONDOWN:
            if self.rc_left.collidepoint(ev.pos):
                # click selects a row
                line_h = 24
                y0 = self.rc_left.y + 12
                ix = (ev.pos[1] - y0) // line_h + self.scroll
                if 0 <= ix < len(self.roster):
                    self.sel_ix = ix
            for b in self._buttons:
                b.handle(ev)

    def update(self, dt): pass

    def draw(self, screen):
        screen.fill((12,12,16))
        # header
        panel(screen, self.rc_hdr)
        draw_text(screen, f"Roster — {self.career.team_name(self.tid)}", self.rc_hdr.x+10, self.rc_hdr.y+8, size=22)

        # left list
        panel(screen, self.rc_left, color=(24,24,28))
        y = self.rc_left.y + 12
        line_h = 24
        start = self.scroll
        per_page = (self.rc_left.h - 24) // line_h
        end = min(len(self.roster), start + per_page)
        for i in range(start, end):
            p = self.roster[i]
            name = p.get("name", f"P{i}")
            role = p.get("role", "")
            hp = p.get("hp", 0); mx = p.get("max_hp", 0)
            row = f"{name:<12}  HP {hp}/{mx}  {role}"
            col_bg = (38,38,46) if i == self.sel_ix else (24,24,28)
            pygame.draw.rect(screen, col_bg, Rect(self.rc_left.x+8, y-2, self.rc_left.w-16, line_h), border_radius=4)
            draw_text(screen, row, self.rc_left.x+14, y, (220,220,230), 18)
            y += line_h

        # right details
        panel(screen, self.rc_right, color=(24,24,28))
        if 0 <= self.sel_ix < len(self.roster):
            p = self.roster[self.sel_ix]
            x = self.rc_right.x + 12
            y = self.rc_right.y + 12
            draw_text(screen, p.get("name","?"), x, y, (240,240,250), 20); y += 28
            draw_text(screen, f"HP: {p.get('hp',0)}/{p.get('max_hp',0)}", x, y, (220,220,230), 18); y += 22
            draw_text(screen, f"AC: {p.get('ac',10)}", x, y, (220,220,230), 18); y += 22
            if p.get("role"):
                draw_text(screen, f"Role: {p.get('role')}", x, y, (220,220,230), 18); y += 22
            # stats grid
            y += 8
            stats = ["STR","DEX","CON","INT","WIS","CHA"]
            for i, k in enumerate(stats):
                v = p.get(k, "-")
                draw_text(screen, f"{k}: {v}", x + (i%3)*120, y + (i//3)*24, (210,210,220), 18)

        for b in self._buttons:
            b.draw(screen)

    def _back(self):
        self.app.pop_state()
