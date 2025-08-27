from __future__ import annotations

import pygame
from pygame import Rect
from typing import List, Dict, Any

# Tiny UI kit (use your real uiutil if present)
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

COLUMNS = [
    ("POS", 56),
    ("Team", 280),
    ("P", 48),
    ("W", 48),
    ("D", 48),
    ("L", 48),
    ("K", 56),
    ("KD", 56),
    ("PTS", 64),
]

class TableState:
    """
    Standings table viewer:
      - Uses career.table_rows_sorted() (canonical row shape)
      - Fixed grid with headers and dividing lines
    """
    def __init__(self, app, career):
        self.app = app
        self.career = career
        # Layout
        self.rc_hdr = Rect(20, 20, 860, 40)
        self.rc_grid = Rect(20, 70, 860, 480)
        self.rc_btns = Rect(20, 560, 860, 40)
        self._build_buttons()

    def _build_buttons(self):
        self.btn_back = Button(Rect(self.rc_btns.x, self.rc_btns.y, 120, 32), "Back", self._back)
        self._buttons = [self.btn_back]

    # --- events ---
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self._back()
            return
        if ev.type == pygame.MOUSEBUTTONDOWN:
            for b in self._buttons:
                b.handle(ev)

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill((12,12,16))
        panel(screen, self.rc_hdr)
        draw_text(screen, "Standings", self.rc_hdr.x+10, self.rc_hdr.y+8, size=22)

        panel(screen, self.rc_grid, color=(24,24,28))
        # grid metrics
        x = self.rc_grid.x + 10
        y = self.rc_grid.y + 10
        row_h = 24

        # header
        cx = x
        for name, w in COLUMNS:
            draw_text(screen, name, cx, y, (220,220,230), 18)
            cx += w
        y += row_h
        # horizontal line under header
        pygame.draw.line(screen, (48,48,56), (self.rc_grid.x+8, y-4), (self.rc_grid.x + self.rc_grid.w - 8, y-4), 1)

        # rows
        rows: List[Dict[str, Any]] = self.career.table_rows_sorted()
        for idx, r in enumerate(rows, start=1):
            cx = x
            vals = [
                idx, r.get("name","?"), r.get("P",0), r.get("W",0), r.get("D",0),
                r.get("L",0), r.get("K",0), r.get("KD",0), r.get("PTS",0),
            ]
            for (val, (_, w)) in zip(vals, COLUMNS):
                draw_text(screen, str(val), cx, y, (220,220,230), 18)
                cx += w
            # row line
            pygame.draw.line(screen, (40,40,48), (self.rc_grid.x+8, y+row_h-6), (self.rc_grid.x + self.rc_grid.w - 8, y+row_h-6), 1)
            y += row_h

        # vertical column lines (visual aid)
        cx = x
        for _, w in COLUMNS:
            pygame.draw.line(screen, (40,40,48), (cx-4, self.rc_grid.y+8), (cx-4, self.rc_grid.y + self.rc_grid.h - 8), 1)
            cx += w

        for b in self._buttons:
            b.draw(screen)

    def _back(self):
        self.app.pop_state()
