from __future__ import annotations

import pygame
from pygame import Rect
from typing import Any, Dict, Optional

try:
    from ui.uiutil import Button, draw_text, panel
except Exception:
    class Button:
        def __init__(self, rect, label, cb, enabled=True):
            self.rect, self.label, self.cb, self.enabled = rect, label, cb, enabled
        def draw(self, screen):
            pygame.draw.rect(screen, (60,60,70) if self.enabled else (40,40,48), self.rect, border_radius=8)
            font = pygame.font.SysFont("arial", 18)
            txt = font.render(self.label, True, (255,255,255) if self.enabled else (170,170,170))
            screen.blit(txt, (self.rect.x+10, self.rect.y+6))
        def handle(self, ev):
            if self.enabled and ev.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(ev.pos):
                self.cb()
    def draw_text(surface, text, x, y, color=(230,230,235), size=20):
        font = pygame.font.SysFont("arial", size)
        surface.blit(font.render(str(text), True, color), (x, y))
    def panel(surface, rect, color=(30,30,38)):
        pygame.draw.rect(surface, color, rect, border_radius=10)

try:
    from engine.ai import weights as OI
except Exception:
    OI = None

try:
    from ui.state_match import MatchState
except Exception:
    MatchState = None


class PreMatchOIState:
    """
    Simple pre-match panel to configure OI before launching the league match.
    If no fixture passed, tries to find the user's fixture for current week.
    """
    def __init__(self, app, career, fixture: Optional[Dict[str, Any]] = None):
        self.app = app
        self.career = career
        self.fixture = fixture or self._find_user_fixture()
        if self.fixture is None:
            raise RuntimeError("No playable fixture found for this week.")

        self.use_oi = True
        self.focus_low_hp = True
        self.prefer_roles = {"Healer": 20, "Bruiser": 10}

        self.rc_hdr = Rect(20, 20, 860, 50)
        self.rc_body = Rect(20, 80, 860, 460)
        self.rc_btns = Rect(20, 550, 860, 50)

        x = self.rc_btns.x
        self.btn_start = Button(Rect(x, self.rc_btns.y + 8, 160, 34), "Start Match", self._start)
        self.btn_back  = Button(Rect(x + 180, self.rc_btns.y + 8, 120, 34), "Back", self._back)
        self._buttons = [self.btn_start, self.btn_back]

    def _find_user_fixture(self):
        user_tid = getattr(self.career, "user_tid", None)
        if user_tid is None:
            return None
        for fx in self.career.fixtures_for_week(getattr(self.career, "week", 1)):
            if fx.get("played"): 
                continue
            if str(fx.get("home_id")) == str(user_tid) or str(fx.get("away_id")) == str(user_tid):
                return fx
        return None

    # events
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self._back(); return
        if ev.type == pygame.MOUSEBUTTONDOWN:
            mx, my = ev.pos
            cb_use = Rect(self.rc_body.x + 20, self.rc_body.y + 60, 18, 18)
            cb_low = Rect(self.rc_body.x + 38, self.rc_body.y + 96, 18, 18)
            if cb_use.collidepoint(mx, my): self.use_oi = not self.use_oi
            if cb_low.collidepoint(mx, my): self.focus_low_hp = not self.focus_low_hp
            for b in self._buttons:
                b.handle(ev)

    def update(self, dt): pass

    def draw(self, screen):
        screen.fill((12,12,16))
        panel(screen, self.rc_hdr)
        hn = self.career.team_name(int(self.fixture["home_id"]))
        an = self.career.team_name(int(self.fixture["away_id"]))
        draw_text(screen, f"Pre-Match OI — {hn} vs {an}", self.rc_hdr.x + 10, self.rc_hdr.y + 12, size=22)

        panel(screen, self.rc_body, color=(24,24,28))
        draw_text(screen, "Opposition Instructions", self.rc_body.x + 16, self.rc_body.y + 20, size=18)
        self._checkbox(screen, self.rc_body.x + 20, self.rc_body.y + 60, self.use_oi, "Enable OI for this match")
        self._checkbox(screen, self.rc_body.x + 38, self.rc_body.y + 96, self.focus_low_hp, "Bias toward low-HP targets")
        draw_text(screen, "Role bias (if targets have role):", self.rc_body.x + 16, self.rc_body.y + 140, size=16)
        draw_text(screen, "Healer +20, Bruiser +10", self.rc_body.x + 32, self.rc_body.y + 164, size=16)

        for b in self._buttons:
            b.draw(screen)

    def _checkbox(self, screen, x, y, state, label):
        rc = Rect(x, y, 18, 18)
        pygame.draw.rect(screen, (40,40,48), rc, border_radius=4)
        if state:
            pygame.draw.rect(screen, (120,220,160), Rect(x+3, y+3, 12, 12), border_radius=3)
        draw_text(screen, label, x + 26, y - 2, size=18)

    def _start(self):
        if self.use_oi and OI is not None:
            OI.set_oi_map({
                "focus_low_hp": bool(self.focus_low_hp),
                "prefer_roles": dict(self.prefer_roles),
            })
        elif OI is not None:
            OI.clear_oi()
        self.app.push_state(MatchState(self.app, self.career, fixture=self.fixture))

    def _back(self):
        self.app.pop_state()
