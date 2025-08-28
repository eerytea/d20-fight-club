# ui/state_table.py
from __future__ import annotations
import pygame
from pygame import Rect

# Try to use shared UI helpers if available; otherwise provide tiny fallbacks
try:
    from ui.uiutil import Button, draw_text, panel
except Exception:
    class Button:
        def __init__(self, rect: Rect, label: str, cb, enabled: bool = True):
            self.rect = rect
            self.label = label
            self.cb = cb
            self.enabled = enabled
        def draw(self, s):
            pygame.draw.rect(s, (60, 60, 75) if self.enabled else (40, 40, 50), self.rect, border_radius=8)
            f = pygame.font.SysFont("arial", 18)
            s.blit(f.render(self.label, True, (255, 255, 255)), (self.rect.x + 10, self.rect.y + 8))
        def handle(self, e):
            if e.type == pygame.MOUSEBUTTONDOWN and self.enabled and self.rect.collidepoint(e.pos):
                self.cb()

    def draw_text(s, text, x, y, color=(230, 230, 235), size=18):
        f = pygame.font.SysFont("arial", size)
        s.blit(f.render(str(text), True, color), (x, y))

    def panel(surf, rect, color=(28, 28, 34)):
        pygame.draw.rect(surf, color, rect, border_radius=12)


class TableState:
    """
    Minimal, dependency-light standings screen.
    Expects a `career` object with .table_rows_sorted()
    """
    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.rc_hdr = Rect(20, 20, 860, 50)
        self.rc_list = Rect(20, 80, 860, 460)
        self.rc_btns = Rect(20, 550, 860, 50)
        self.scroll = 0
        self.row_h = 26

        x = self.rc_btns.x
        self.btn_back = Button(Rect(x, self.rc_btns.y + 8, 140, 34), "Back", self._back)
        self._buttons = [self.btn_back]

    def handle(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self._back(); return
        if e.type == pygame.MOUSEWHEEL and self.rc_list.collidepoint(pygame.mouse.get_pos()):
            self.scroll = max(0, self.scroll - e.y)
        if e.type == pygame.MOUSEBUTTONDOWN:
            for b in self._buttons:
                b.handle(e)

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill((12, 12, 16))
        panel(screen, self.rc_hdr)
        draw_text(screen, "League Table", self.rc_hdr.x + 12, self.rc_hdr.y + 12, size=22)
        panel(screen, self.rc_list, color=(24, 24, 30))

        # Headers
        cols = [("Pos", 50), ("Team", 260), ("P", 60), ("W", 60), ("D", 60), ("L", 60), ("K", 60), ("KD", 70), ("PTS", 80)]
        x = self.rc_list.x + 10
        y = self.rc_list.y + 10
        cx = x
        for title, w in cols:
            draw_text(screen, title, cx, y, (220, 220, 230), 18); cx += w
        y += 26

        # Rows
        try:
            rows = self.career.table_rows_sorted()
        except Exception:
            rows = []

        area_h = self.rc_list.h - 40
        max_rows = area_h // self.row_h
        start = self.scroll

        for i, r in enumerate(rows[start:start + max_rows], start=1 + start):
            cx = x
            vals = [
                i,
                r.get("name", ""),
                r.get("P", 0), r.get("W", 0), r.get("D", 0), r.get("L", 0),
                r.get("K", 0), r.get("KD", 0), r.get("PTS", 0)
            ]
            for (_, w), val in zip(cols, vals):
                draw_text(screen, str(val), cx, y, (230, 230, 235), 18)
                cx += w
            y += self.row_h

        for b in self._buttons:
            b.draw(screen)

    def _back(self):
        self.app.pop_state()
