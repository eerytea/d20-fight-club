from __future__ import annotations

import pygame
from pygame import Rect
from typing import Any, Dict, List, Optional

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

# Exhibition screen we push
try:
    from ui.state_exhibition import ExhibitionState
except Exception:
    ExhibitionState = None

class ExhibitionPickerState:
    """
    Pick Home and Away teams, then start a friendly match.
    """
    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.teams: List[Dict[str, Any]] = getattr(career, "teams", [])
        self.sel_home_ix = 0
        self.sel_away_ix = 1 if len(self.teams) > 1 else 0

        # layout
        self.rc_hdr = Rect(20, 20, 860, 40)
        self.rc_home = Rect(20, 70, 420, 440)
        self.rc_away = Rect(460, 70, 420, 440)
        self.rc_btns = Rect(20, 530, 860, 60)
        self._build_buttons()

    def _build_buttons(self):
        bw, bh, gap = 140, 36, 10
        x = self.rc_btns.x
        self.btn_start = Button(Rect(x, self.rc_btns.y, bw, bh), "Start Match", self._start)
        self.btn_swap = Button(Rect(x + bw + gap, self.rc_btns.y, bw, bh), "Swap Sides", self._swap)
        self.btn_back = Button(Rect(x + 2*(bw+gap), self.rc_btns.y, bw, bh), "Back", self._back)
        self._buttons = [self.btn_start, self.btn_swap, self.btn_back]

    # events
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self._back(); return
        if ev.type == pygame.MOUSEBUTTONDOWN:
            if self.rc_home.collidepoint(ev.pos):
                ix = self._row_at_y(self.rc_home, ev.pos[1])
                if 0 <= ix < len(self.teams):
                    self.sel_home_ix = ix
            elif self.rc_away.collidepoint(ev.pos):
                ix = self._row_at_y(self.rc_away, ev.pos[1])
                if 0 <= ix < len(self.teams):
                    self.sel_away_ix = ix
            for b in self._buttons:
                b.handle(ev)

    def update(self, dt): pass

    def draw(self, screen):
        screen.fill((12,12,16))
        panel(screen, self.rc_hdr)
        draw_text(screen, "Exhibition — pick teams", self.rc_hdr.x+10, self.rc_hdr.y+8, size=22)

        # left/right lists
        self._draw_list(screen, self.rc_home, "Home", self.sel_home_ix)
        self._draw_list(screen, self.rc_away, "Away", self.sel_away_ix)

        for b in self._buttons:
            b.draw(screen)

    def _draw_list(self, screen, rect, title, sel_ix):
        panel(screen, rect, color=(24,24,28))
        draw_text(screen, title, rect.x+10, rect.y+8, (220,220,230), 18)
        y = rect.y + 32
        line_h = 24
        for i, t in enumerate(self.teams):
            name = t.get("name", f"Team {t.get('tid','?')}")
            col_bg = (38,38,46) if i == sel_ix else (24,24,28)
            pygame.draw.rect(screen, col_bg, Rect(rect.x+8, y-2, rect.w-16, line_h), border_radius=4)
            draw_text(screen, f"{i+1:>2}. {name}", rect.x+14, y, (220,220,230), 18)
            y += line_h

    def _row_at_y(self, rect, y) -> int:
        line_h = 24
        start_y = rect.y + 32
        ix = (y - start_y) // line_h
        return int(ix)

    # actions
    def _swap(self):
        self.sel_home_ix, self.sel_away_ix = self.sel_away_ix, self.sel_home_ix

    def _start(self):
        if not self.teams or ExhibitionState is None:
            return
        if self.sel_home_ix == self.sel_away_ix:
            return
        home = self.teams[self.sel_home_ix]
        away = self.teams[self.sel_away_ix]
        self.app.push_state(ExhibitionState(self.app, self.career, home_tid=home.get("tid"), away_tid=away.get("tid")))

    def _back(self):
        self.app.pop_state()
