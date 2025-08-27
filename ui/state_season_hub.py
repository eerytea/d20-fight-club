from __future__ import annotations

import pygame
from pygame import Rect
from typing import List, Dict, Any

# ---- Optional real UI kit ----
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
    from ui.state_match import MatchState
except Exception:
    MatchState = None
try:
    from ui.state_message import MessageState
except Exception:
    MessageState = None


class SeasonHubState:
    """
    Season Hub:
      - Header: Your Team, Week
      - This Week's Matchups (list)
      - Buttons: Play, Sim Week, Schedule, Table, Roster, Back
    """
    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.toast_text = ""
        self.toast_timer = 0.0

        # layout
        self.rc_hdr   = Rect(20, 20, 860, 60)
        self.rc_match = Rect(20, 90, 860, 380)
        self.rc_btns  = Rect(20, 480, 860, 120)

        self._build_buttons()
        self._refresh_button_states()

    # ---------------- UI plumbing ----------------
    def _build_buttons(self):
        x = self.rc_btns.x
        y = self.rc_btns.y + 10
        w, h, gap = 140, 36, 10
        self.btn_play   = Button(Rect(x, y, w, h), "Play", self._play)
        self.btn_sim    = Button(Rect(x + (w+gap), y, w, h), "Sim Week", self._sim_week)
        self.btn_sched  = Button(Rect(x + 2*(w+gap), y, w, h), "Schedule", self._open_schedule)
        self.btn_table  = Button(Rect(x + 3*(w+gap), y, w, h), "Table", self._open_table)
        self.btn_roster = Button(Rect(x + 4*(w+gap), y, w, h), "Roster", self._open_roster)
        self.btn_back   = Button(Rect(x + 5*(w+gap), y, w, h), "Back", self._back)
        self._buttons = [self.btn_play, self.btn_sim, self.btn_sched, self.btn_table, self.btn_roster, self.btn_back]

    def _refresh_button_states(self):
        # Enable Play only if a user fixture exists this week and is unplayed
        self.btn_play.enabled = self._find_user_fixture() is not None

    # ---------------- events ----------------
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self._back(); return
        if ev.type == pygame.MOUSEBUTTONDOWN:
            for b in self._buttons:
                b.handle(ev)

    def update(self, dt):
        if self.toast_timer > 0:
            self.toast_timer -= dt
            if self.toast_timer <= 0:
                self.toast_text = ""

    def draw(self, screen):
        screen.fill((12,12,16))
        # header
        panel(screen, self.rc_hdr)
        user_tid = getattr(self.career, "user_tid", 0)
        draw_text(screen, f"Your Team: {self.career.team_name(user_tid)}", self.rc_hdr.x + 10, self.rc_hdr.y + 10, size=22)
        draw_text(screen, f"Week {self.career.week}", self.rc_hdr.x + 10, self.rc_hdr.y + 34, size=18)

        # matchups
        panel(screen, self.rc_match, color=(24,24,28))
        draw_text(screen, "This Week's Matchups", self.rc_match.x+10, self.rc_match.y+10, size=20)
        y = self.rc_match.y + 40
        line_h = 24
        fixtures = self.career.fixtures_for_week(getattr(self.career, "week", 1))
        if not fixtures:
            draw_text(screen, "No fixtures this week.", self.rc_match.x+12, y, (210,210,220), 18)
        else:
            for fx in fixtures:
                h = int(fx.get("home_id", fx.get("home_tid", fx.get("A", 0))))
                a = int(fx.get("away_id", fx.get("away_tid", fx.get("B", 0))))
                hn = self.career.team_name(h)
                an = self.career.team_name(a)
                played = bool(fx.get("played", False))
                row = f"{hn} vs {an}"
                color = (220,220,230)
                if played:
                    row = f"{hn}  {fx.get('k_home',0)}–{fx.get('k_away',0)}  {an}"
                    color = (210,235,210)
                # highlight user's fixture
                if str(h) == str(user_tid) or str(a) == str(user_tid):
                    color = (255,220,140) if not played else (230,250,180)
                draw_text(screen, row, self.rc_match.x + 12, y, color, 18)
                y += line_h

        # buttons
        for b in self._buttons:
            b.draw(screen)

        # toast
        if self.toast_text:
            tx = self.toast_text
            rect = Rect(self.rc_hdr.x + 540, self.rc_hdr.y + 12, 320, 32)
            panel(screen, rect, color=(32,32,40))
            draw_text(screen, tx, rect.x + 10, rect.y + 6, (240,240,240), 18)

    # ---------------- helpers ----------------
    def _find_user_fixture(self):
        """Return (fixture dict) if user's team has an unplayed match this week."""
        user_tid = getattr(self.career, "user_tid", None)
        if user_tid is None:
            return None
        fixtures = self.career.fixtures_for_week(getattr(self.career, "week", 1))
        for fx in fixtures:
            if fx.get("played"):
                continue
            h = int(fx.get("home_id", fx.get("home_tid", fx.get("A", -1))))
            a = int(fx.get("away_id", fx.get("away_tid", fx.get("B", -1))))
            if str(h) == str(user_tid) or str(a) == str(user_tid):
                return fx
        return None

    def _toast(self, text: str, seconds: float = 2.0):
        self.toast_text = text
        self.toast_timer = seconds

    # ---------------- actions ----------------
    def _play(self):
        fx = self._find_user_fixture()
        if fx is None:
            self._toast("No playable fixture this week.")
            return
        if MatchState is None:
            # fallback toast if match viewer not available
            self._toast("Match screen not available.")
            return
        # Push MatchState; state_match.py should handle on_finish() and saving
        try:
            self.app.push_state(MatchState(self.app, self.career, fixture=fx))
        except TypeError:
            # if your MatchState signature differs, try the legacy form
            try:
                self.app.push_state(MatchState(self.app, self.career))
            except Exception:
                self._toast("Unable to start match (constructor mismatch).")

    def _sim_week(self):
        try:
            self.career.simulate_week_ai()
            self._toast("Simulated AI fixtures.")
            self._refresh_button_states()
        except Exception:
            self._toast("Sim failed.")

    def _open_schedule(self):
        if ScheduleState is not None:
            self.app.push_state(ScheduleState(self.app, self.career, start_week=getattr(self.career, "week", 1)))

    def _open_table(self):
        if TableState is not None:
            self.app.push_state(TableState(self.app, self.career))

    def _open_roster(self):
        if RosterState is not None:
            tid = getattr(self.career, "user_tid", 0)
            self.app.push_state(RosterState(self.app, self.career, tid=tid))

    def _back(self):
        self.app.pop_state()
