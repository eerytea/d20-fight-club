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
        if ev.type == pygame.MOUSEMOTION: self.hover = self.rect.collidepoint(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.rect.collidepoint(ev.pos):
            self.action()

def _ovr(p: Dict[str,Any]) -> int:
    return int(p.get("OVR", p.get("ovr", p.get("OVR_RATING", 60))))

def _name(p: Dict[str,Any]) -> str:
    n = p.get("name") or p.get("full_name") or ""
    if n: return str(n)
    first = p.get("first_name") or p.get("firstName") or ""
    last  = p.get("last_name") or p.get("lastName") or ""
    return (first + " " + last).strip() or "Player"

def _pretty(x: Any) -> str:
    return str(x).replace("_"," ").title() if x is not None else "-"

class RosterViewState:
    def __init__(self, app, career):
        self.app = app
        self.car = career
        self.font  = pygame.font.SysFont(None, 22)
        self.h1    = pygame.font.SysFont(None, 34)
        self.h2    = pygame.font.SysFont(None, 20)
        self.player_idx = 0
        self.scroll = 0
        self.scroll_stats = 0
        self.stats_h = 0

    def enter(self):
        w,h = self.app.screen.get_size()
        pad = 16
        self.rect_header = pygame.Rect(pad,pad,w-pad*2,48)
        right_w = max(420, int(w*0.42))
        self.rect_list = pygame.Rect(pad, self.rect_header.bottom+pad, w-right_w-pad*3, h-(self.rect_header.bottom+pad*2))
        self.rect_stats= pygame.Rect(self.rect_list.right+pad, self.rect_list.y, right_w, self.rect_list.h)
        # back
        bw,bh = 120,36
        self.btn_back = Button(pygame.Rect(self.rect_header.right-bw-12, self.rect_header.y+6, bw, bh), "Back", self._back)

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE): self._back(); return
        if ev.type == pygame.MOUSEWHEEL:
            mx,my = pygame.mouse.get_pos()
            if self.rect_list.collidepoint(mx,my):
                self.scroll = self._clamp_scroll(self.scroll + ev.y*24, self.rect_list, len(self._fighters())*28)
            elif self.rect_stats.collidepoint(mx,my):
                self.scroll_stats = self._clamp_scroll(self.scroll_stats + ev.y*24, self.rect_stats, self.stats_h)
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.rect_list.collidepoint(ev.pos):
            row_h = 28
            idx = (ev.pos[1] - (self.rect_list.y + 36) - self.scroll)//row_h
            if 0 <= idx < len(self._fighters()):
                self.player_idx = int(idx)
        self.btn_back.handle(ev)

    def update(self, dt): pass

    def draw(self, screen):
        screen.fill((16,16,20))
        # header
        pygame.draw.rect(screen,(42,44,52),self.rect_header,border_radius=12)
        pygame.draw.rect(screen,(24,24,28),self.rect_header,2,border_radius=12)
        tid = int(getattr(self.car, "user_tid", 0))
        team_name = self.car.team_name(tid) if hasattr(self.car,"team_name") else "Your Team"
        t = self.h1.render(f"Roster • {team_name}", True, (235,235,240))
        screen.blit(t,(self.rect_header.x+12, self.rect_header.y+(self.rect_header.h-t.get_height())//2))
        self.btn_back.draw(screen, self.font)

        # list
        pygame.draw.rect(screen,(42,44,52),self.rect_list,border_radius=12)
        pygame.draw.rect(screen,(24,24,28),self.rect_list,2,border_radius=12)
        surf = self.h2.render("Players", True, (215,215,220))
        screen.blit(surf, (self.rect_list.x+12, self.rect_list.y+10))

        inner = self.rect_list.inflate(-16, -52); inner.y = self.rect_list.y + 36
        prev_clip = screen.get_clip(); screen.set_clip(inner)
        y0 = inner.y + self.scroll
        row_h = 28
        for i,p in enumerate(self._fighters()):
            r = pygame.Rect(inner.x, y0 + i*row_h, inner.w, row_h-4)
            sel = (i == self.player_idx)
            bg = (58,60,70) if not sel else (88,92,110)
            pygame.draw.rect(screen,bg,r,border_radius=8); pygame.draw.rect(screen,(24,24,28),r,2,border_radius=8)
            label = f"{_name(p)}   AGE {int(p.get('age',18))}   OVR {_ovr(p)}"
            txt = self.font.render(label, True, (230,230,235))
            screen.blit(txt,(r.x+10, r.y + (r.h - txt.get_height())//2))
        screen.set_clip(prev_clip)
        self._scrollbar(screen, inner, len(self._fighters())*row_h, self.scroll)

        # stats
        pygame.draw.rect(screen,(42,44,52),self.rect_stats,border_radius=12)
        pygame.draw.rect(screen,(24,24,28),self.rect_stats,2,border_radius=12)
        self._draw_stats(screen)

    # helpers
    def _fighters(self) -> List[Dict[str,Any]]:
        tid = int(getattr(self.car, "user_tid", 0))
        for t in getattr(self.car, "teams", []):
            if int(t.get("tid",-1)) == tid:
                return t.get("fighters", [])
        return []

    def _draw_stats(self, screen):
        p = None
        fs = self._fighters()
        if fs: p = fs[max(0, min(self.player_idx, len(fs)-1))]
        if not p:
            self.stats_h = 0; return
        def G(k,d=None): return p.get(k, p.get(k.upper(), d))
        name = _name(p)
        lvl = int(G("level",1)); age = int(G("age",18)); ovr = int(G("ovr", G("OVR",60))); pot = int(G("potential",70))
        race = _pretty(G("race","-")); origin = G("origin","-"); cls = _pretty(G("class","Fighter"))
        hp = int(G("hp",10)); max_hp=int(G("max_hp",hp)); ac = int(G("ac",12))
        STR=int(G("str",G("STR",10))); DEX=int(G("dex",G("DEX",10))); CON=int(G("con",G("CON",10)))
        INT=int(G("int",G("INT",10))); WIS=int(G("wis",G("WIS",10))); CHA=int(G("cha",G("CHA",10)))

        clip = self.rect_stats.inflate(-12,-16)
        prev = screen.get_clip(); screen.set_clip(clip)
        x0 = self.rect_stats.x+12; y = self.rect_stats.y+12 + self.scroll_stats
        lh = self.font.get_height()+6
        def line(s):
            nonlocal y
            t = self.font.render(s,True,(220,220,225)); screen.blit(t,(x0,y)); y += lh
        line(f"{name}    AGE: {age}    LVL: {lvl}")
        line(f"{race}    {origin}    OVR: {ovr}    POT: {pot}")
        line(f"{cls}    HP: {hp}/{max_hp}    AC: {ac}")

        y += 4
        labels=("STR","DEX","CON","INT","WIS","CHA"); vals=(STR,DEX,CON,INT,WIS,CHA)
        col_w = (self.rect_stats.w-24)//6; top = y
        for i,lab in enumerate(labels):
            lx = x0 + i*col_w + col_w//2
            t = self.font.render(lab,True,(210,210,215))
            screen.blit(t,(lx - t.get_width()//2, top))
        y = top + self.font.get_height()+4
        for i,v in enumerate(vals):
            lx = x0 + i*col_w + col_w//2
            t = self.font.render(str(v),True,(235,235,240))
            screen.blit(t,(lx - t.get_width()//2, y))
        y += self.font.get_height() + 10
        self.stats_h = max(0, y - (self.rect_stats.y+12))
        screen.set_clip(prev)

    def _scrollbar(self, screen, area, content_h, scroll_px):
        if content_h <= area.h: return
        track = pygame.Rect(area.right-6, area.y, 4, area.h)
        pygame.draw.rect(screen,(30,30,35),track,border_radius=2)
        denom = max(1, content_h - area.h)
        ratio = min(1.0, max(0.0, -scroll_px / denom))
        thumb_h = max(18, int(area.h * area.h / content_h))
        thumb_y = area.y + int((area.h - thumb_h) * ratio)
        pygame.draw.rect(screen,(120,120,130),pygame.Rect(track.x, thumb_y, track.w, thumb_h),border_radius=2)

    def _clamp_scroll(self, val, rect, content_h):
        max_neg = min(0, rect.h - content_h)
        if val > 0: val = 0
        if val < max_neg: val = max_neg
        return val

    def _back(self): self.app.pop_state()
