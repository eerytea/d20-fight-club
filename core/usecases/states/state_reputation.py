from __future__ import annotations
import pygame
from pygame import Rect

try:
    from ui.uiutil import Button, draw_text, panel
except Exception:
    class Button:
        def __init__(self, rect, label, cb, enabled=True):
            self.rect, self.label, self.cb, self.enabled = rect, label, cb, enabled
        def draw(self, screen):
            pygame.draw.rect(screen, (60,60,70) if self.enabled else (40,40,48), self.rect, border_radius=6)
            font = pygame.font.SysFont("arial", 18)
            screen.blit(font.render(self.label, True, (255,255,255)), (self.rect.x+8, self.rect.y+6))
        def handle(self, ev):
            if self.enabled and ev.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(ev.pos):
                self.cb()
    def draw_text(surface, text, x, y, color=(230,230,235), size=20):
        font = pygame.font.SysFont("arial", size)
        surface.blit(font.render(str(text), True, color), (x, y))
    def panel(surface, rect, color=(30,30,38)):
        pygame.draw.rect(surface, color, rect, border_radius=8)

from core import reputation as _rep

class ReputationState:
    """
    Simple viewer for Clubs / Nations / Races Elo tables.
    """
    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.tab = "clubs"  # 'clubs' | 'nations' | 'races'
        self.rc_hdr = Rect(20, 20, 860, 40)
        self.rc_grid = Rect(20, 70, 860, 480)
        self.rc_btns = Rect(20, 560, 860, 40)
        self._build_buttons()

    def _build_buttons(self):
        x, y, w, h, g = self.rc_btns.x, self.rc_btns.y, 120, 36, 10
        self.btn_clubs = Button(Rect(x, y, w, h), "Clubs", lambda: self._set_tab("clubs"))
        self.btn_nats  = Button(Rect(x + (w+g), y, w, h), "Nations", lambda: self._set_tab("nations"))
        self.btn_race  = Button(Rect(x + 2*(w+g), y, w, h), "Races", lambda: self._set_tab("races"))
        self.btn_back  = Button(Rect(x + 3*(w+g), y, w, h), "Back", self._back)
        self._buttons = [self.btn_clubs, self.btn_nats, self.btn_race, self.btn_back]

    def _set_tab(self, t): self.tab = t

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self._back(); return
        if ev.type == pygame.MOUSEBUTTONDOWN:
            for b in self._buttons:
                b.handle(ev)

    def update(self, dt): pass

    def draw(self, screen):
        screen.fill((12,12,16))
        panel(screen, self.rc_hdr)
        draw_text(screen, f"Reputation — {self.tab.title()}", self.rc_hdr.x+10, self.rc_hdr.y+8, size=22)

        panel(screen, self.rc_grid, color=(24,24,28))
        rows = _rep.table(self.tab, self.career)
        x, y = self.rc_grid.x + 12, self.rc_grid.y + 12
        draw_text(screen, "POS", x, y, size=18); draw_text(screen, "ID", x+60, y, size=18); draw_text(screen, "Rating", x+420, y, size=18)
        y += 24
        for i, (id_, rating) in enumerate(rows, start=1):
            draw_text(screen, str(i), x, y, size=18)
            draw_text(screen, str(id_), x+60, y, size=18)
            draw_text(screen, f"{rating:.1f}", x+420, y, size=18)
            y += 22

        for b in self._buttons:
            b.draw(screen)

    def _back(self):
        self.app.pop_state()
