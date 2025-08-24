# ui/state_schedule.py
from __future__ import annotations
from typing import List

try:
    import pygame
except Exception:
    pygame = None  # type: ignore

try:
    from .uiutil import Button
except Exception:
    Button = None  # type: ignore

from .state_message import MessageState


class ScheduleState:
    def __init__(self, app, career=None):
        self.app = app
        self.career = career or app.data.get("career")
        self._title_font = None
        self._font = None
        self._small = None
        self._btn_prev = self._btn_next = self._btn_back = None
        self._week = self.career.week if self.career else 0

    def enter(self):
        if pygame is None:
            return
        pygame.font.init()
        self._title_font = pygame.font.SysFont("consolas", 26)
        self._font = pygame.font.SysFont("consolas", 18)
        self._small = pygame.font.SysFont("consolas", 14)
        self._layout()

    def _layout(self):
        w, h = self.app.width, self.app.height
        btn_w, btn_h, gap = 150, 40, 10
        by = h - 64
        bx = w - 24 - btn_w
        mk = lambda label, fn, x: (Button(pygame.Rect(x, by, btn_w, btn_h), label, on_click=fn)
                                   if Button else _SimpleButton(pygame.Rect(x, by, btn_w, btn_h), label, fn))
        self._btn_back = mk("Back", self._back, bx); bx -= (btn_w + gap)
        self._btn_next = mk("Next Week", self._next_week, bx); bx -= (btn_w + gap)
        self._btn_prev = mk("Prev Week", self._prev_week, bx)

    def handle_event(self, e):
        if pygame is None:
            return False
        for b in (self._btn_prev, self._btn_next, self._btn_back):
            if b and b.handle_event(e):
                return True
        return False

    def update(self, dt): pass

    def draw(self, surf):
        if pygame is None: return
        w, h = surf.get_size()
        title = self._title_font.render(f"Schedule — Week {self._week+1}", True, (255,255,255))
        surf.blit(title, (24, 24))

        lines = []
        if self.career:
            you = self.career.user_team_id
            for fx in self.career.fixtures:
                if fx.week != self._week: continue
                H = self.career.team_names[fx.home_id]
                A = self.career.team_names[fx.away_id]
                you_tag = []
                if fx.home_id == you: you_tag.append("(YOU)")
                if fx.away_id == you: you_tag.append("(YOU)")
                tag = " ".join(you_tag)
                if fx.played:
                    lines.append(f"[P] {H} {fx.home_goals}-{fx.away_goals} {A} {tag}")
                else:
                    lines.append(f"[ ] {H} vs {A} {tag}")
        y = 80
        for s in lines:
            surf.blit(self._font.render(s, True, (230,230,230)), (40, y))
            y += 24

        for b in (self._btn_prev, self._btn_next, self._btn_back):
            if b: b.draw(surf)

    # actions
    def _back(self): self.app.pop_state()
    def _prev_week(self): self._week = max(0, self._week-1)
    def _next_week(self):
        if self.career:
            maxw = max(f.week for f in self.career.fixtures)
            self._week = min(maxw, self._week+1)


class _SimpleButton:
    def __init__(self, rect, label, on_click):
        self.rect, self.label, self.on_click = rect, label, on_click
        self.hover=False; self._font=pygame.font.SysFont("consolas",18) if pygame else None
    def handle_event(self,e):
        if e.type==pygame.MOUSEMOTION: self.hover=self.rect.collidepoint(e.pos)
        elif e.type==pygame.MOUSEBUTTONDOWN and e.button==1 and self.rect.collidepoint(e.pos):
            self.on_click(); return True
        return False
    def draw(self,surf):
        bg=(120,120,120) if self.hover else (98,98,98)
        pygame.draw.rect(surf,bg,self.rect,border_radius=6)
        pygame.draw.rect(surf,(50,50,50),self.rect,2,border_radius=6)
        t=self._font.render(self.label,True,(20,20,20))
        surf.blit(t,(self.rect.x+(self.rect.w-t.get_width())//2,self.rect.y+(self.rect.h-t.get_height())//2))
