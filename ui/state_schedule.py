from __future__ import annotations

import pygame
from pygame import Rect
from typing import Any, Dict, List, Optional

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

def _total_weeks(career) -> int:
    fbw = getattr(career, "fixtures_by_week", None)
    if isinstance(fbw, list) and fbw:
        return len(fbw)
    # Fallback: highest week in flat fixtures
    fx = getattr(career, "fixtures", [])
    mx = 0
    for m in fx:
        try:
            mx = max(mx, int(m.get("week", 0)))
        except Exception:
            pass
    return max(1, mx)

class ScheduleState:
    """
    Simple schedule browser:
      - Prev / Next week
      - Uses career.fixtures_for_week(week) and career.team_name(tid)
      - Draw-only; no side effects
    """
    def __init__(self, app, career, start_week: Optional[int] = None):
        self.app = app
        self.career = career
        self.week = int(start_week if start_week is not None else getattr(career, "week", 1))
        self.weeks_total = max(1, _total_weeks(career))
        # Layout
        self.rc_hdr = Rect(20, 20, 860, 40)
        self.rc_list = Rect(20, 70, 860, 450)
        self.rc_btns = Rect(20, 530, 860, 60)
        self._build_buttons()

    def _build_buttons(self):
        bx, by, bw, bh, gap = self.rc_btns.x, self.rc_btns.y, 120, 36, 10
        self.btn_prev = Button(Rect(bx, by, bw, bh), "Prev Week", self._prev)
        self.btn_next = Button(Rect(bx + (bw+gap), by, bw, bh), "Next Week", self._next)
        self.btn_back = Button(Rect(bx + 2*(bw+gap), by, bw, bh), "Back", self._back)
        self._buttons = [self.btn_prev, self.btn_next, self.btn_back]
        self._update_button_states()

    def _update_button_states(self):
        self.btn_prev.enabled = self.week > 1
        self.btn_next.enabled = self.week < self.weeks_total

    # --- events ---
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self._back()
            return
        if ev.type == pygame.MOUSEBUTTONDOWN:
            for b in self._buttons:
                b.handle(ev)

    def update(self, dt):  # nothing animated
        pass

    # --- draw ---
    def draw(self, screen):
        screen.fill((12, 12, 16))
        panel(screen, self.rc_hdr)
        draw_text(screen, f"Week {self.week} / {self.weeks_total}", self.rc_hdr.x+10, self.rc_hdr.y+8, size=22)

        panel(screen, self.rc_list, color=(24,24,28))
        y = self.rc_list.y + 12
        line_h = 26
        fixtures = self.career.fixtures_for_week(self.week)
        if not fixtures:
            draw_text(screen, "No fixtures found for this week.", self.rc_list.x+12, y, (200,180,180), 18)
        else:
            for fx in fixtures:
                try:
                    h, a = int(fx["home_id"]), int(fx["away_id"])
                except Exception:
                    # try aliases just in case
                    h = int(fx.get("home_tid", fx.get("A", 0)))
                    a = int(fx.get("away_tid", fx.get("B", 0)))
                hn = self.career.team_name(h)
                an = self.career.team_name(a)
                played = fx.get("played", False)
                k_home = fx.get("k_home", 0); k_away = fx.get("k_away", 0)
                if played:
                    row = f"{hn}  {k_home}–{k_away}  {an}"
                    col = (220, 235, 210)
                else:
                    row = f"{hn}  vs  {an}"
                    col = (220, 220, 230)
                draw_text(screen, row, self.rc_list.x+12, y, col, 18)
                y += line_h

        for b in self._buttons:
            b.draw(screen)

    # --- actions ---
    def _prev(self):
        if self.week > 1:
            self.week -= 1
            self._update_button_states()

    def _next(self):
        if self.week < self.weeks_total:
            self.week += 1
            self._update_button_states()

    def _back(self):
        self.app.pop_state()
