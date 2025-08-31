# ui/state_roster_view.py
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
        txt = font.render(self.text, True, (235,235,240))
        surf.blit(txt, (self.rect.x+14, self.rect.y + (self.rect.h - txt.get_height())//2))
    def handle(self, ev):
        if self.disabled: return
        if ev.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                self.action()

def _pretty(s: Any) -> str:
    if s is None: return "-"
    t = str(s)
    if "_" in t: t = t.replace("_", " ")
    return t.title()

def _name(p: Dict[str, Any]) -> str:
    return p.get("name") or p.get("Name") or f"P{int(p.get('pid', p.get('id', 0)))+1}"

class RosterView:
    def __init__(self, car):
        self.car = car
        self.font = pygame.font.SysFont("Inter", 18)
        self.title_font = pygame.font.SysFont("Inter", 24, bold=True)
        self.rect = pygame.Rect(40, 60, 960, 560)
        self.rows_start = 0
        self.rows_per_page = 10

        self.btn_prev = Button(pygame.Rect(self.rect.right-200, self.rect.bottom-44, 90, 32), "Prev", self._prev)
        self.btn_next = Button(pygame.Rect(self.rect.right-100, self.rect.bottom-44, 90, 32), "Next", self._next)

    def _prev(self): self.rows_start = max(0, self.rows_start - self.rows_per_page)
    def _next(self): self.rows_start = self.rows_start + self.rows_per_page

    def _team_players(self) -> List[Dict[str, Any]]:
        tid = int(getattr(self.car, "user_tid", 0))
        for t in getattr(self.car, "teams", []):
            if int(t.get("tid",-1)) == tid:
                # NOTE: Keep the data key 'fighters' – UI displays them as "Players"
                return t.get("fighters", [])
        return []

    def _draw_stats(self, screen):
        pygame.draw.rect(screen, (30,32,38), self.rect, border_radius=12)
        pygame.draw.rect(screen, (22,24,28), self.rect, width=2, border_radius=12)

        title = self.title_font.render("Players", True, (235,235,240))
        screen.blit(title, (self.rect.x + 16, self.rect.y + 12))

        y0 = self.rect.y + 56
        colx = [self.rect.x+16, self.rect.x+240, self.rect.x+390, self.rect.x+520, self.rect.x+640, self.rect.x+740]

        hdrs = ["Name", "Class", "Level", "OVR", "HP/Max", "AC"]
        for i,h in enumerate(hdrs):
            screen.blit(self.font.render(h, True, (180,182,192)), (colx[i], y0))

        players = self._team_players()
        start = self.rows_start
        rows = players[start:start + self.rows_per_page]

        y = y0 + 28
        for p in rows:
            def G(k,d=None): return p.get(k, p.get(k.upper(), d))
            name = _name(p)
            lvl = int(G("level",1)); ovr = int(G("ovr", G("OVR",60)))
            race = _pretty(G("race","-")); origin = G("origin","-")
            cls = _pretty(G("class","-"))
            hp = int(G("hp",10)); max_hp=int(G("max_hp",hp)); ac = int(G("ac",12))

            cols = [
                name,
                cls,
                f"{lvl}",
                f"{ovr}",
                f"{hp}/{max_hp}",
                f"{ac}",
            ]
            for i,txt in enumerate(cols):
                screen.blit(self.font.render(str(txt), True, (220,222,228)), (colx[i], y))
            y += 26

        # paging
        self.btn_prev.draw(screen, self.font); self.btn_next.draw(screen, self.font)

    def handle(self, ev):
        self.btn_prev.handle(ev); self.btn_next.handle(ev)

    def draw(self, screen):
        self._draw_stats(screen)
