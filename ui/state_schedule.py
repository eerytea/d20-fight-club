# ui/state_schedule.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class Button:
    rect: pygame.Rect
    text: str
    action: callable
    hover: bool = False
    disabled: bool = False
    def draw(self, surf, font):
        bg = (58,60,70) if not self.hover else (76,78,90)
        if self.disabled: bg = (48,48,54)
        pygame.draw.rect(surf, bg, self.rect, border_radius=10)
        pygame.draw.rect(surf, (24,24,28), self.rect, 2, border_radius=10)
        txt = font.render(self.text, True, (235,235,240 if not self.disabled else 160))
        surf.blit(txt, (self.rect.x+14, self.rect.y + (self.rect.h - txt.get_height())//2))
    def handle(self, ev):
        if self.disabled: return
        if ev.type == pygame.MOUSEMOTION: self.hover = self.rect.collidepoint(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.rect.collidepoint(ev.pos):
            self.action()

def _norm_fixture(f: Any) -> Dict[str, Any]:
    if isinstance(f, dict):
        h = f.get("home_id", f.get("home_tid", f.get("A", f.get("home", 0))))
        a = f.get("away_id", f.get("away_tid", f.get("B", f.get("away", 0))))
        sh = f.get("score_home", f.get("sh", f.get("home_score")))
        sa = f.get("score_away", f.get("sa", f.get("away_score")))
        played = f.get("played", f.get("is_played", (sh is not None and sa is not None)))
        return {"home": int(h), "away": int(a), "played": bool(played), "sh": sh, "sa": sa}
    if isinstance(f, (list, tuple)):
        h = int(f[0]) if len(f)>=1 else 0; a = int(f[1]) if len(f)>=2 else 0
        sh = f[2] if len(f)>=3 else None; sa = f[3] if len(f)>=4 else None
        return {"home": h, "away": a, "played": (sh is not None and sa is not None), "sh": sh, "sa": sa}
    return {"home":0,"away":0,"played":False,"sh":None,"sa":None}

def _team_name(car, tid):
    if hasattr(car, "team_name") and callable(car.team_name):
        try: return car.team_name(int(tid))
        except Exception: pass
    for t in getattr(car, "teams", []):
        if int(t.get("tid",-1)) == int(tid): return t.get("name", f"Team {tid}")
    return f"Team {tid}"

class ScheduleState:
    def __init__(self, app, career):
        self.app = app
        self.car = career
        self.font  = pygame.font.SysFont(None, 22)
        self.h1    = pygame.font.SysFont(None, 34)
        self.h2    = pygame.font.SysFont(None, 20)
        self.week = int(getattr(self.car, "week", 1) or 1)
        self.total_weeks = len(getattr(self.car, "fixtures_by_week", [])) or getattr(self.car, "total_weeks", 0) or self.week

    def enter(self):
        w,h = self.app.screen.get_size()
        pad = 16
        self.rect_header = pygame.Rect(pad,pad,w-pad*2,48)
        self.rect_list   = pygame.Rect(pad, self.rect_header.bottom+pad, w-pad*2, h-(self.rect_header.bottom+pad*2))
        # Buttons
        bw,bh,g = 120,36,10
        self.btn_prev = Button(pygame.Rect(self.rect_header.x+12, self.rect_header.y+6, bw, bh), "Prev Week", self._prev)
        self.btn_next = Button(pygame.Rect(self.rect_header.x+12+bw+g, self.rect_header.y+6, bw, bh), "Next Week", self._next)
        self.btn_back = Button(pygame.Rect(self.rect_header.right-bw-12, self.rect_header.y+6, bw, bh), "Back", self._back)

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self._back(); return
        for b in (self.btn_prev, self.btn_next, self.btn_back): b.handle(ev)

    def update(self, dt): pass

    def draw(self, screen):
        screen.fill((16,16,20))
        pygame.draw.rect(screen,(42,44,52),self.rect_header,border_radius=12)
        pygame.draw.rect(screen,(24,24,28),self.rect_header,2,border_radius=12)
        t = self.h1.render(f"Schedule • Week {self.week}/{self.total_weeks}", True, (235,235,240))
        screen.blit(t,(self.rect_header.centerx - t.get_width()//2, self.rect_header.y + (self.rect_header.h - t.get_height())//2))
        for b in (self.btn_prev, self.btn_next, self.btn_back): b.draw(screen, self.font)

        pygame.draw.rect(screen,(42,44,52),self.rect_list,border_radius=12)
        pygame.draw.rect(screen,(24,24,28),self.rect_list,2,border_radius=12)
        weeks = getattr(self.car, "fixtures_by_week", [])
        fixtures = []
        if weeks and 0 <= self.week-1 < len(weeks):
            fixtures = [_norm_fixture(f) for f in weeks[self.week-1]]
        y = self.rect_list.y + 12
        line_h = self.font.get_height()+10
        for fx in fixtures:
            hname = _team_name(self.car, fx["home"])
            aname = _team_name(self.car, fx["away"])
            score = ""
            if fx["played"] and fx["sh"] is not None and fx["sa"] is not None:
                score = f" — {fx['sh']} - {fx['sa']}"
            label = f"{hname}  vs  {aname}{score}"
            surf = self.font.render(label, True, (230,230,235))
            screen.blit(surf, (self.rect_list.x + 14, y))
            y += line_h

    def _prev(self):
        self.week = max(1, self.week-1)

    def _next(self):
        self.week = min(self.total_weeks, self.week+1)

    def _back(self):
        self.app.pop_state()
