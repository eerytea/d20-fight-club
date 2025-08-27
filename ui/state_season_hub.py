# ui/state_season_hub.py
from __future__ import annotations

import pygame
from pygame import Rect
from typing import Any, Dict, List, Optional

# ---- UI kit (fallbacks if missing) ----
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

# ---- Child states (optional) ----
try:
    from ui.state_match import MatchState
except Exception:
    MatchState = None
try:
    from ui.state_schedule import ScheduleState
except Exception:
    ScheduleState = None
try:
    from ui.state_table import TableState
except Exception:
    TableState = None
try:
    from ui.state_roster import RosterState
except Exception:
    RosterState = None
try:
    from ui.state_pre_match_oi import PreMatchOIState
except Exception:
    PreMatchOIState = None

# ---- Career (type only) ----
try:
    from core.career import Career
except Exception:
    Career = None  # type: ignore


class SeasonHubState:
    """
    Season Hub:
      - Header: Your Team, Week N
      - This Week's Matchups (scroll list)
      - Buttons: Play, Sim Week, Schedule, Table, Roster, Back
    """
    def __init__(self, app, career):
        self.app = app
        self.career = career

        self.rc_hdr   = Rect(20, 20, 860, 60)
        self.rc_list  = Rect(20, 90, 620, 460)
        self.rc_btns  = Rect(660, 90, 220, 180)
        self.rc_back  = Rect(660, 280, 220, 270)

        self.row_h = 26
        self.scroll = 0
        self._toast = ""
        self._toast_t = 0.0

        # Buttons
        x, y = self.rc_btns.x + 10, self.rc_btns.y + 10
        w, h, g = 200, 36, 10
        self.btn_play = Button(Rect(x, y, w, h), "Play", self._play); y += h + g
        self.btn_sim  = Button(Rect(x, y, w, h), "Sim Week", self._sim_week); y += h + g
        self.btn_sched= Button(Rect(x, y, w, h), "Schedule", self._open_schedule); y += h + g
        self.btn_table= Button(Rect(x, y, w, h), "Table", self._open_table); y += h + g

        x, y = self.rc_back.x + 10, self.rc_back.y + 10
        self.btn_roster= Button(Rect(x, y, w, h), "Roster", self._open_roster); y += h + g
        self.btn_back  = Button(Rect(x, y, w, h), "Back", self._back)

        self._buttons = [self.btn_play, self.btn_sim, self.btn_sched, self.btn_table, self.btn_roster, self.btn_back]

    # ---------------- events ----------------
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self._back(); return
        if ev.type == pygame.MOUSEWHEEL and self.rc_list.collidepoint(pygame.mouse.get_pos()):
            self.scroll = max(0, self.scroll - ev.y)
        if ev.type == pygame.MOUSEBUTTONDOWN:
            for b in self._buttons:
                b.handle(ev)

    def update(self, dt):
        if self._toast_t > 0:
            self._toast_t -= dt
            if self._toast_t <= 0:
                self._toast = ""

        # Enable/disable Play based on presence of user's unplayed fixture
        self.btn_play.enabled = (self._find_user_fixture() is not None)

    def draw(self, screen):
        screen.fill((12,12,16))

        # Header
        panel(screen, self.rc_hdr)
        tid = getattr(self.career, "user_tid", 0)
        draw_text(screen, f"Your Team: {self.career.team_name(tid)}", self.rc_hdr.x + 10, self.rc_hdr.y + 10, size=22)
        draw_text(screen, f"Week {getattr(self.career, 'week', 1)}", self.rc_hdr.x + 620, self.rc_hdr.y + 12, size=20)

        # Fixtures list
        panel(screen, self.rc_list, color=(24,24,28))
        draw_text(screen, "This Week's Matchups", self.rc_list.x + 10, self.rc_list.y + 10, size=18)
        self._draw_fixtures(screen)

        # Buttons
        panel(screen, self.rc_btns, color=(24,24,28))
        for b in self._buttons:
            b.draw(screen)

        if self._toast:
            draw_text(screen, self._toast, self.rc_hdr.x + 480, self.rc_hdr.y + 12, (230,230,240), 18)

    # ---------------- helpers ----------------
    def _draw_fixtures(self, screen):
        area = Rect(self.rc_list.x + 8, self.rc_list.y + 36, self.rc_list.w - 16, self.rc_list.h - 44)
        pygame.draw.rect(screen, (18,18,22), area, border_radius=6)

        wk = getattr(self.career, "week", 1)
        fixtures = list(self.career.fixtures_for_week(wk))
        start = self.scroll
        max_rows = area.h // self.row_h
        rows = fixtures[start:start+max_rows]

        for i, fx in enumerate(rows):
            y = area.y + i*self.row_h
            hn = self.career.team_name(int(fx["home_id"]))
            an = self.career.team_name(int(fx["away_id"]))
            status = "FINAL" if fx.get("played") else "—"
            draw_text(screen, f"{hn}  vs  {an}    {status}", area.x + 8, y + 4, size=18)

    def _find_user_fixture(self) -> Optional[Dict[str, Any]]:
        user_tid = getattr(self.career, "user_tid", None)
        if user_tid is None:
            return None
        wk = getattr(self.career, "week", 1)
        for fx in self.career.fixtures_for_week(wk):
            if fx.get("played"):
                continue
            if str(fx.get("home_id")) == str(user_tid) or str(fx.get("away_id")) == str(user_tid):
                return fx
        return None

    def _toast_set(self, text: str):
        # Use app toast if available; else draw in header for ~2s.
        cb = getattr(self.app, "set_toast", None)
        if callable(cb):
            cb(text)
        else:
            self._toast = text
            self._toast_t = 2.0

    # ---------------- actions ----------------
    def _play(self):
        fx = self._find_user_fixture()
        if fx is None:
            self._toast_set("No match to play this week.")
            return
        # Prefer Pre-Match OI panel; fallback to direct match
        if PreMatchOIState is not None:
            self.app.push_state(PreMatchOIState(self.app, self.career, fixture=fx))
        elif MatchState is not None:
            self.app.push_state(MatchState(self.app, self.career, fixture=fx))
        else:
            self._toast_set("Match screen not available.")

    def _sim_week(self):
        try:
            self.career.simulate_week_ai()
            self._toast_set("Week simulated.")
        except Exception:
            self._toast_set("Sim failed.")

    def _open_schedule(self):
        if ScheduleState is not None:
            self.app.push_state(ScheduleState(self.app, self.career))

    def _open_table(self):
        if TableState is not None:
            self.app.push_state(TableState(self.app, self.career))

    def _open_roster(self):
        if RosterState is not None:
            tid = getattr(self.career, "user_tid", 0)
            self.app.push_state(RosterState(self.app, self.career, tid=tid))

    def _back(self):
        self.app.pop_state()
