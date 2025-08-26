# ui/state_season_hub.py
from __future__ import annotations

from typing import Optional

import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_text, draw_panel

try:
    from core.career import Career
except Exception:
    Career = object  # type: ignore


class SeasonHubState(BaseState):
    def __init__(self, app, career: Optional[Career] = None):
        self.app = app
        self.career: Optional[Career] = career
        self.theme = Theme()
        self.buttons: list[Button] = []
        self._layout_built = False

    def enter(self) -> None:
        self._build_layout()

    # --- Layout --------------------------------------------------------------
    def _build_layout(self) -> None:
        self.buttons.clear()
        W, H = self.app.width, self.app.height

        panel = pygame.Rect(16, 80, W - 32, H - 96)
        self.panel_rect = panel

        # Buttons along bottom-right
        btn_w, btn_h, gap = 180, 42, 10
        x = panel.right - (btn_w + gap)
        y = panel.bottom - (btn_h + gap)

        def add(label, fn):
            nonlocal x, y
            self.buttons.append(Button(pygame.Rect(x, y, btn_w, btn_h), label, fn))
            x -= btn_w + gap
            if x < panel.x + 12:
                x = panel.right - (btn_w + gap)
                y -= btn_h + gap

        add("Back", self._back)
        add("Save (soon)", self._save)
        add("Table", self._table)
        add("Schedule", self._schedule)
        add("Roster", self._roster)
        add("Sim Rest of Week", self._sim_rest)
        add("Play My Match", self._play_my_match)

        self._layout_built = True

    # --- Button actions ------------------------------------------------------
    def _back(self):
        self.app.pop_state()

    def _save(self):
        print("[SeasonHub] Save coming soon.")

    def _table(self):
        if self.career is None:
            print("[SeasonHub] No career loaded.")
            return
        try:
            from .state_table import TableState
            self.app.push_state(TableState(self.app, self.career))
        except Exception as e:
            print("[SeasonHub] Table open failed:", e)

    def _schedule(self):
        if self.career is None:
            print("[SeasonHub] No career loaded.")
            return
        try:
            from .state_schedule import ScheduleState
            self.app.push_state(ScheduleState(self.app, self.career))
        except Exception as e:
            print("[SeasonHub] Schedule open failed:", e)

    def _roster(self):
        try:
            from .state_roster_browser import RosterBrowserState
            self.app.push_state(RosterBrowserState(self.app))
        except Exception as e:
            print("[SeasonHub] Roster open failed:", e)

    def _sim_rest(self):
        if self.career is None:
            print("[SeasonHub] No career loaded.")
            return
        try:
            from core.sim import simulate_week_ai
            simulate_week_ai(self.career)
        except Exception as e:
            print("[SeasonHub] simulate_week_ai failed:", e)

    def _play_my_match(self):
        if self.career is None:
            print("[SeasonHub] No career loaded.")
            return
        try:
            from .state_match import MatchState
            # pick first unplayed fixture; bias to user team if set
            uid = getattr(self.career, "user_team_id", None)
            fixture = None
            for fx in getattr(self.career, "fixtures", []):
                if getattr(fx, "played", False):
                    continue
                if uid is None or fx.home_id == uid or fx.away_id == uid:
                    fixture = fx
                    break
            if fixture is None:
                print("[SeasonHub] No pending fixtures.")
                return
            tH = next(t for t in self.career.teams if t["tid"] == fixture.home_id)
            tA = next(t for t in self.career.teams if t["tid"] == fixture.away_id)
            self.app.push_state(MatchState(self.app, tH, tA))
        except Exception as e:
            print("[SeasonHub] Play failed:", e)

    # --- State interface -----------------------------------------------------
    def handle(self, event) -> None:
        if not self._layout_built:
            return
        for b in self.buttons:
            b.handle(event)

    def update(self, dt: float) -> None:
        if not self._layout_built:
            self._build_layout()
        mx, my = pygame.mouse.get_pos()
        for b in self.buttons:
            b.update((mx, my))

    def draw(self, surface: "pygame.Surface") -> None:
        th = self.theme
        surface.fill(th.bg)

        # Title
        if self.career is None:
            title = "Season Hub — No season loaded"
            subtitle = "Load a save or start a New Season to continue."
        else:
            wk = getattr(self.career, "week", 1)
            title = f"Season Hub — Week {wk}"
            subtitle = getattr(self.career, "league_name", "Single League")

        draw_text(surface, title, (surface.get_width() // 2, 16), 32, th.text, align="center")
        draw_text(surface, subtitle, (surface.get_width() // 2, 52), 20, th.subt, align="center")

        # Main panel
        draw_panel(surface, self.panel_rect, th)

        if self.career:
            try:
                team_count = len(getattr(self.career, "teams", []))
                draw_text(surface, f"Teams: {team_count}", (self.panel_rect.x + 16, self.panel_rect.y + 16), 20, th.text)
                draw_text(surface, f"Fixtures: {len(getattr(self.career, 'fixtures', []))}", (self.panel_rect.x + 16, self.panel_rect.y + 40), 20, th.text)
            except Exception:
                pass

        # Buttons
        for b in self.buttons:
            b.draw(surface, th)
