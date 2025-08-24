# ui/state_table.py
from __future__ import annotations

try:
    import pygame
except Exception:
    pygame = None  # type: ignore

try:
    from .uiutil import Button
except Exception:
    Button = None  # type: ignore

class TableState:
    def __init__(self, app, career=None):
        self.app = app
        self.career = career or app.data.get("career")
        self._title_font = None
        self._font = None
        self._small = None
        self._btn_back = None

    def enter(self):
        if pygame is None: return
        pygame.font.init()
        self._title_font = pygame.font.SysFont("consolas", 26)
        self._font = pygame.font.SysFont("consolas", 18)
        self._small = pygame.font.SysFont("consolas", 14)
        w, h = self.app.width, self.app.height
        btn_w, btn_h = 150, 40
        self._btn_back = (Button(pygame.Rect(w-24-btn_w, h-64, btn_w, btn_h), "Back", on_click=self._back)
                          if Button else _SimpleButton(pygame.Rect(w-24-btn_w, h-64, btn_w, btn_h), "Back", self._back))

    def handle_event(self, e):
        if pygame is None: return False
        if self._btn_back and self._btn_back.handle_event(e): return True
        return False

    def update(self, dt): pass

    def draw(self, surf):
        if pygame is None: return
        w, h = surf.get_size()
        title = self._title_font.render("Standings", True, (255,255,255))
        surf.blit(title, (24, 24))

        rows = []
        if self.career:
            tbl = self.career.table
            for tid, row in tbl.items():
                gd = row.goals_for - row.goals_against
                rows.append((tid, row.points, gd, row.goals_for, row))
            rows.sort(key=lambda t: (t[1], t[2], t[3]), reverse=True)

        x = 40; y = 80
        header = self._font.render("Pos Team                P  W  D  L  GF GA  GD  Pts", True, (220,220,220))
        surf.blit(header, (x, y)); y += 26
        you = self.career.user_team_id if self.career else -1
        for i, (tid, _p, _gd, _gf, row) in enumerate(rows, start=1):
            mark = "  ← YOU" if tid == you else ""
            name = row.name
            gd = row.goals_for - row.goals_against
            line = f"{i:>2}. {name:18} {row.played:>2} {row.wins:>2} {row.draws:>2} {row.losses:>2} {row.goals_for:>3} {row.goals_against:>3} {gd:>3} {row.points:>3}{mark}"
            surf.blit(self._font.render(line, True, (240,240,240)), (x, y))
            y += 22

        if self._btn_back: self._btn_back.draw(surf)

    def _back(self): self.app.pop_state()


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
