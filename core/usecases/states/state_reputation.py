from __future__ import annotations
import pygame
from typing import List, Tuple
from core.reputation import Reputation, RepTable

try:
    from ui.uiutil import Theme, Button, draw_text, panel
except Exception:
    Theme = None
    Button = None
    def draw_text(surface, text, x, y, color=(255,255,255), size=20):
        font = pygame.font.SysFont("arial", size)
        surf = font.render(text, True, color)
        surface.blit(surf, (x, y))
    def panel(surface, rect, color=(40,40,40)):
        pygame.draw.rect(surface, color, rect, border_radius=6)

class ReputationState:
    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.rep: Reputation = getattr(career, "reputation", Reputation())
        self.tabs = [("Clubs", RepTable.CLUB), ("Nations", RepTable.NATIONAL), ("Races", RepTable.RACE)]
        self.active_ix = 0
        self.scroll = 0

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_LEFT:
                self.active_ix = max(0, self.active_ix - 1)
            elif ev.key == pygame.K_RIGHT:
                self.active_ix = min(len(self.tabs)-1, self.active_ix + 1)
            elif ev.key == pygame.K_UP:
                self.scroll = max(0, self.scroll - 1)
            elif ev.key == pygame.K_DOWN:
                self.scroll += 1
        elif ev.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - ev.y)

    def update(self, dt):
        pass

    def draw(self, screen):
        w, h = screen.get_size()
        screen.fill((10, 10, 14))
        # Tabs
        x = 20
        for i, (label, _) in enumerate(self.tabs):
            col = (255, 255, 0) if i == self.active_ix else (200, 200, 200)
            draw_text(screen, f"[{label}]", x, 20, col, size=22)
            x += 140

        # Table panel
        panel(screen, pygame.Rect(20, 60, w-40, h-80), color=(30,30,35))
        self._draw_table(screen, pygame.Rect(30, 70, w-60, h-100))

    def _draw_table(self, screen, rect):
        table = self.tabs[self.active_ix][1]
        rows: List[Tuple[str, float]] = self.rep.table_sorted(table)
        row_h = 26
        header = ["#", "ID", "Rating"]
        col_x = [rect.x + 10, rect.x + 50, rect.x + rect.width - 150]
        # Header
        draw_text(screen, header[0], col_x[0], rect.y, (160,160,160), size=20)
        draw_text(screen, header[1], col_x[1], rect.y, (160,160,160), size=20)
        draw_text(screen, header[2], col_x[2], rect.y, (160,160,160), size=20)
        # Rows (scroll)
        start = self.scroll
        end = min(len(rows), start + max(1, rect.height // row_h) - 2)
        y = rect.y + 30
        for i in range(start, end):
            k, r = rows[i]
            draw_text(screen, f"{i+1}", col_x[0], y, (220,220,220), size=18)
            draw_text(screen, k, col_x[1], y, (220,220,220), size=18)
            draw_text(screen, f"{r:.1f}", col_x[2], y, (220,220,220), size=18)
            y += row_h
