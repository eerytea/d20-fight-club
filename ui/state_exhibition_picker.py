from __future__ import annotations

import pygame
from pygame import Rect
from typing import Any, Dict, List, Optional

try:
    from ui.uiutil import Theme, Button, draw_text, panel
except Exception:
    Theme = None
    class Button:
        def __init__(self, rect, label, cb, enabled=True):
            self.rect, self.label, self.cb, self.enabled = rect, label, cb, enabled
        def draw(self, screen):
            pygame.draw.rect(screen, (60,60,70) if self.enabled else (40,40,48), self.rect, border_radius=8)
            font = pygame.font.SysFont("arial", 18)
            screen.blit(font.render(self.label, True, (255,255,255) if self.enabled else (170,170,170)),
                        (self.rect.x+10, self.rect.y+6))
        def handle(self, ev):
            if self.enabled and ev.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(ev.pos):
                self.cb()
    def draw_text(surface, text, x, y, color=(230,230,235), size=20):
        font = pygame.font.SysFont("arial", size)
        surface.blit(font.render(str(text), True, color), (x, y))
    def panel(surface, rect, color=(30,30,38)):
        pygame.draw.rect(surface, color, rect, border_radius=10)

# Match screen
try:
    from ui.state_match import MatchState
except Exception:
    MatchState = None

# Optional OI weights
try:
    from engine.ai import weights as OI
except Exception:
    OI = None

def _team_name(t: Dict[str, Any]) -> str:
    return t.get("name", f"Team {t.get('tid', t.get('id','?'))}")

class ExhibitionPickerState:
    """
    Pick Home/Away teams and (optionally) set simple OI biases.
    Then start a friendly match using MatchState.
    """
    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.teams = list(getattr(career, "teams", []))

        self.sel_home = int(getattr(career, "user_tid", 0))
        self.sel_away = (self.sel_home + 1) % max(1, len(self.teams))

        # OI options (very simple); only applied if checkbox is on
        self.use_oi = False
        self.oi_focus_low_hp = True
        self.oi_prefer_roles = {"Healer": 20, "Bruiser": 10}  # +score if target has role

        # Layout
        self.rc_hdr   = Rect(20, 20, 860, 50)
        self.rc_lists = Rect(20, 80, 520, 460)
        self.rc_oi    = Rect(560, 80, 320, 300)
        self.rc_btns  = Rect(560, 400, 320, 140)

        # team list scrolling
        self.scroll_home = 0
        self.scroll_away = 0
        self.row_h = 26

        # Buttons
        self.btn_back   = Button(Rect(self.rc_btns.x,           self.rc_btns.y + 90, 140, 34), "Back", self._back)
        self.btn_start  = Button(Rect(self.rc_btns.x + 160,     self.rc_btns.y + 90, 140, 34), "Start", self._start)
        self._buttons = [self.btn_back, self.btn_start]

    # --------------- events ----------------
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self._back(); return
        if ev.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            # Left list = home, right list = away
            left = Rect(self.rc_lists.x, self.rc_lists.y + 30, self.rc_lists.w//2 - 10, self.rc_lists.h - 40)
            right = Rect(self.rc_lists.x + self.rc_lists.w//2 + 10, self.rc_lists.y + 30, self.rc_lists.w//2 - 10, self.rc_lists.h - 40)
            if left.collidepoint(mx, my):
                self.scroll_home = max(0, self.scroll_home - ev.y)
            elif right.collidepoint(mx, my):
                self.scroll_away = max(0, self.scroll_away - ev.y)
        if ev.type == pygame.MOUSEBUTTONDOWN:
            mx, my = ev.pos
            # Oy toggles
            cb_oi = Rect(self.rc_oi.x + 10, self.rc_oi.y + 36, 18, 18)
            cb_low = Rect(self.rc_oi.x + 28, self.rc_oi.y + 70, 18, 18)
            if cb_oi.collidepoint(mx, my):
                self.use_oi = not self.use_oi
            if cb_low.collidepoint(mx, my):
                self.oi_focus_low_hp = not self.oi_focus_low_hp

            # Team picks
            left = Rect(self.rc_lists.x, self.rc_lists.y + 30, self.rc_lists.w//2 - 10, self.rc_lists.h - 40)
            right = Rect(self.rc_lists.x + self.rc_lists.w//2 + 10, self.rc_lists.y + 30, self.rc_lists.w//2 - 10, self.rc_lists.h - 40)

            if left.collidepoint(mx, my):
                idx = (my - left.y) // self.row_h + self.scroll_home
                if 0 <= idx < len(self.teams):
                    self.sel_home = int(self.teams[idx].get("tid", self.teams[idx].get("id", 0)))
                    if self.sel_home == self.sel_away:
                        self.sel_away = (self.sel_home + 1) % len(self.teams)

            if right.collidepoint(mx, my):
                idx = (my - right.y) // self.row_h + self.scroll_away
                if 0 <= idx < len(self.teams):
                    self.sel_away = int(self.teams[idx].get("tid", self.teams[idx].get("id", 0)))
                    if self.sel_home == self.sel_away:
                        self.sel_home = (self.sel_away + 1) % len(self.teams)

            for b in self._buttons:
                b.handle(ev)

    def update(self, dt): pass

    def draw(self, screen):
        screen.fill((12,12,16))
        panel(screen, self.rc_hdr)
        draw_text(screen, "Exhibition — pick Home / Away", self.rc_hdr.x + 10, self.rc_hdr.y + 12, size=22)

        # Team lists
        panel(screen, self.rc_lists, color=(24,24,28))
        draw_text(screen, "Home", self.rc_lists.x + 12, self.rc_lists.y + 6, size=18)
        draw_text(screen, "Away", self.rc_lists.x + self.rc_lists.w//2 + 22, self.rc_lists.y + 6, size=18)

        self._draw_team_list(screen,
                             Rect(self.rc_lists.x, self.rc_lists.y + 30, self.rc_lists.w//2 - 10, self.rc_lists.h - 40),
                             self.scroll_home, self.sel_home)
        self._draw_team_list(screen,
                             Rect(self.rc_lists.x + self.rc_lists.w//2 + 10, self.rc_lists.y + 30, self.rc_lists.w//2 - 10, self.rc_lists.h - 40),
                             self.scroll_away, self.sel_away)

        # OI panel
        panel(screen, self.rc_oi, color=(24,24,28))
        draw_text(screen, "Opposition Instructions", self.rc_oi.x + 10, self.rc_oi.y + 8, size=18)
        # master toggle
        self._checkbox(screen, self.rc_oi.x + 10, self.rc_oi.y + 36, self.use_oi, "Enable OI for this match")
        # simple options
        self._checkbox(screen, self.rc_oi.x + 28, self.rc_oi.y + 70, self.oi_focus_low_hp, "Bias towards low HP targets")
        draw_text(screen, "Role bias (if targets have role):", self.rc_oi.x + 10, self.rc_oi.y + 104, size=16)
        draw_text(screen, "Healer +20, Bruiser +10", self.rc_oi.x + 24, self.rc_oi.y + 126, size=16, color=(210,210,220))

        # buttons
        for b in self._buttons:
            b.draw(screen)

        # current selection banner
        sel_txt = f"Home: {_team_name(self._team_by_id(self.sel_home))}    vs    Away: {_team_name(self._team_by_id(self.sel_away))}"
        draw_text(screen, sel_txt, self.rc_btns.x, self.rc_btns.y + 10, size=18)

    # --------------- helpers ----------------
    def _team_by_id(self, tid: int) -> Dict[str, Any]:
        for t in self.teams:
            if int(t.get("tid", t.get("id", -1))) == int(tid):
                return t
        return {"tid": tid, "name": f"Team {tid}", "fighters": []}

    def _draw_team_list(self, screen, rect: Rect, scroll: int, selected_tid: int):
        # header row bounds
        x, y = rect.x, rect.y
        pygame.draw.rect(screen, (18,18,22), rect, border_radius=8)
        start = scroll
        max_rows = rect.h // self.row_h
        data = self.teams[start:start+max_rows]
        for i, t in enumerate(data):
            ty = y + i*self.row_h
            tid = int(t.get("tid", t.get("id", -1)))
            if tid == selected_tid:
                pygame.draw.rect(screen, (60,60,90), Rect(x+2, ty+1, rect.w-4, self.row_h-2), border_radius=4)
            draw_text(screen, f"{tid:02d}  {_team_name(t)}", x + 8, ty + 4, size=18)

    def _checkbox(self, screen, x, y, state: bool, label: str):
        rc = Rect(x, y, 18, 18)
        pygame.draw.rect(screen, (40,40,48), rc, border_radius=4)
        if state:
            pygame.draw.rect(screen, (120,220,160), Rect(x+3, y+3, 12, 12), border_radius=3)
        draw_text(screen, label, x + 24, y - 2, size=18)

    # --------------- actions ----------------
    def _back(self):
        self.app.pop_state()

    def _start(self):
        if self.sel_home == self.sel_away or MatchState is None:
            return
        # Apply OI if enabled
        if self.use_oi and OI is not None:
            oi_map = {
                "focus_low_hp": bool(self.oi_focus_low_hp),
                "prefer_roles": dict(self.oi_prefer_roles),
            }
            OI.set_oi_map(oi_map)
        elif OI is not None:
            OI.clear_oi()

        # Build a friendly fixture dict and push MatchState
        fixture = {
            "week": getattr(self.career, "week", 1),
            "home_id": self.sel_home,
            "away_id": self.sel_away,
            "played": False,
            "k_home": 0, "k_away": 0, "winner": None,
            "comp_kind": "friendly",
        }
        try:
            self.app.push_state(MatchState(self.app, self.career, fixture=fixture))
        except Exception:
            # Fall back: if constructor differs, try without fixture
            try:
                self.app.push_state(MatchState(self.app, self.career))
            except Exception:
                pass
