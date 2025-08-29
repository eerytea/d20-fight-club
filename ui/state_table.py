# ui/state_table.py
from __future__ import annotations
import pygame
from typing import Any, Dict, List

def _team_name(car, tid):
    if hasattr(car, "team_name") and callable(car.team_name):
        try: return car.team_name(int(tid))
        except Exception: pass
    for t in getattr(car, "teams", []):
        if int(t.get("tid",-1)) == int(tid): return t.get("name", f"Team {tid}")
    return f"Team {tid}"

def _build_table(car) -> List[Dict[str, Any]]:
    # Prefer precomputed table
    rows = getattr(car, "table_sorted", None)
    if rows: return rows
    # else derive a minimal one from car.standings
    st = getattr(car, "standings", None)
    if st:
        rows = list(st.values())
        rows.sort(key=lambda r: (r.get("pts",0), r.get("gd",0), r.get("gf",0)), reverse=True)
        return rows
    # ultimate fallback: empty
    return []

class TableState:
    def __init__(self, app, career):
        self.app = app
        self.car = career
        self.font  = pygame.font.SysFont(None, 22)
        self.h1    = pygame.font.SysFont(None, 34)

    def enter(self):
        w,h = self.app.screen.get_size()
        pad = 16
        self.rect_header = pygame.Rect(pad,pad,w-pad*2,48)
        self.rect_body   = pygame.Rect(pad, self.rect_header.bottom+pad, w-pad*2, h-(self.rect_header.bottom+pad*2))
        bw,bh = 120,36
        self.btn_back = pygame.Rect(self.rect_header.right-bw-12, self.rect_header.y+6, bw, bh)

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.app.pop_state(); return
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.btn_back.collidepoint(ev.pos): self.app.pop_state()

    def update(self, dt): pass

    def draw(self, screen):
        screen.fill((16,16,20))
        pygame.draw.rect(screen,(42,44,52),self.rect_header,border_radius=12)
        pygame.draw.rect(screen,(24,24,28),self.rect_header,2,border_radius=12)
        t = self.h1.render("Table", True, (235,235,240))
        screen.blit(t,(self.rect_header.x+12, self.rect_header.y + (self.rect_header.h - t.get_height())//2))
        # back button
        pygame.draw.rect(screen,(58,60,70),self.btn_back,border_radius=10)
        pygame.draw.rect(screen,(24,24,28),self.btn_back,2,border_radius=10)
        tb = self.font.render("Back", True, (235,235,240))
        screen.blit(tb,(self.btn_back.x+14, self.btn_back.y + (self.btn_back.h - tb.get_height())//2))

        # body
        pygame.draw.rect(screen,(42,44,52),self.rect_body,border_radius=12)
        pygame.draw.rect(screen,(24,24,28),self.rect_body,2,border_radius=12)
        rows = _build_table(self.car)
        x = self.rect_body.x + 14
        y = self.rect_body.y + 12
        line_h = self.font.get_height() + 8
        header = self.font.render("Pos  Team                                Pts  W  D  L  GF  GA  GD", True, (210,210,215))
        screen.blit(header, (x, y)); y += line_h
        for i, r in enumerate(rows, start=1):
            name = r.get("name", _team_name(self.car, r.get("tid", i)))
            pts = r.get("pts",0); w=r.get("w",0); d=r.get("d",0); l=r.get("l",0)
            gf = r.get("gf",0); ga=r.get("ga",0); gd=r.get("gd", gf-ga)
            label = f"{i:>2}.  {name:34.34}  {pts:>3}  {w:>2} {d:>2} {l:>2}  {gf:>2}  {ga:>2}  {gd:>3}"
            surf = self.font.render(label, True, (230,230,235))
            screen.blit(surf, (x, y)); y += line_h
