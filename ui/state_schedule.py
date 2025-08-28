# ui/state_schedule.py
from __future__ import annotations
import pygame
from pygame import Rect

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


class ScheduleState:
    """
    Minimal schedule list for the CURRENT week.
    Expects a `career` with .week, .fixtures_for_week(week), and .team_name(tid).
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
        wk = int(getattr(self.career, "week", 1))
        panel(screen, self.rc_hdr)
        draw_text(screen, f"Week {wk} Fixtures", self.rc_hdr.x + 12, self.rc_hdr.y + 12, size=22)
        panel(screen, self.rc_list, color=(24, 24, 30))

        x = self.rc_list.x + 10
        y = self.rc_list.y + 10

        try:
            fixtures = list(self.career.fixtures_for_week(wk))
        except Exception:
            fixtures = []

        area_h = self.rc_list.h - 40
        max_rows = area_h // self.row_h
        start = self.scroll

        for fx in fixtures[start:start + max_rows]:
            hid = int(fx.get("home_id", fx.get("home_tid", fx.get("A", 0))))
            aid = int(fx.get("away_id", fx.get("away_tid", fx.get("B", 1))))
            try:
                h = self.career.team_name(hid)  # type: ignore[attr-defined]
                a = self.career.team_name(aid)  # type: ignore[attr-defined]
            except Exception:
                h = f"Team {hid}"
                a = f"Team {aid}"

            if fx.get("played"):
                line = f"{h} {int(fx.get('k_home', 0))} - {int(fx.get('k_away', 0))} {a}"
            else:
                line = f"{h} vs {a}"
            draw_text(screen, line, x, y, (230, 230, 235), 18)
            y += self.row_h

        for b in self._buttons:
            b.draw(screen)

    def _back(self):
        self.app.pop_state()
