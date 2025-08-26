# ui/state_season_hub.py — Season hub with weekly matchups + scroll for large weeks
from __future__ import annotations

from typing import Optional

import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_text, draw_panel

from core.career import Career
from core.sim import simulate_week_ai


def _team_name(career: Career, tid: int) -> str:
    try:
        return next(t.get("name", f"Team {tid}") for t in career.teams if int(t.get("tid")) == int(tid))
    except StopIteration:
        return f"Team {tid}"


class SeasonHubState(BaseState):
    def __init__(self, app, career: Career):
        self.app = app
        self.theme = Theme()
        self.career = career

        self.rect_toolbar = pygame.Rect(0, 0, 0, 0)
        self.rect_panel = pygame.Rect(0, 0, 0, 0)
        self.rect_buttons = pygame.Rect(0, 0, 0, 0)

        self.btn_play: Button | None = None
        self.btn_sim: Button | None = None
        self.btn_sched: Button | None = None
        self.btn_table: Button | None = None
        self.btn_roster: Button | None = None
        self.btn_back: Button | None = None

        self._built = False
        self._flash: Optional[str] = None
        self._list_scroll: int = 0
        self._line_h: int = 24

    # lifecycle
    def enter(self) -> None:
        self._build()

    # layout
    def _build(self) -> None:
        W, H = self.app.width, self.app.height
        pad = 16
        toolbar_h = 60
        btn_h = 60

        self.rect_toolbar = pygame.Rect(pad, pad, W - pad * 2, toolbar_h)
        self.rect_panel   = pygame.Rect(pad, self.rect_toolbar.bottom + pad, W - pad * 2, H - (toolbar_h + pad * 3 + btn_h))
        self.rect_buttons = pygame.Rect(pad, self.rect_panel.bottom + pad, W - pad * 2, btn_h)

        labels = ["Play", "Sim Week", "Schedule", "Table", "Roster", "Back"]
        handlers = [self._play, self._sim_week, self._schedule, self._table, self._roster, self._back]
        bw = max(130, self.rect_buttons.w // len(labels) - 10)
        gap = max(8, (self.rect_buttons.w - bw * len(labels)) // (len(labels) - 1))
        x = self.rect_buttons.x
        y = self.rect_buttons.y
        btns = []
        for lab, fn in zip(labels, handlers):
            btns.append(Button(pygame.Rect(x, y, bw, self.rect_buttons.h), lab, fn))
            x += bw + gap

        (self.btn_play,
         self.btn_sim,
         self.btn_sched,
         self.btn_table,
         self.btn_roster,
         self.btn_back) = btns

        self._built = True

    # helpers
    def _user_team_name(self) -> str:
        tid = getattr(self.career, "user_team_id", None)
        return _team_name(self.career, tid) if tid is not None else "—"

    def _week_fixtures(self):
        return self.career.fixtures_in_week(self.career.week)

    def _user_fixture_this_week(self):
        return self.career.user_fixture_this_week()

    # actions
    def _play(self) -> None:
        fx = self._user_fixture_this_week()
        if not fx:
            self._flash = "No user match available this week."
            return
        try:
            home = self.career.team_by_id(fx.home_id)
            away = self.career.team_by_id(fx.away_id)
            from .state_match import MatchState

            def _on_finish(ms: "MatchState"):
                eng = getattr(ms, "engine", None)
                kills_home = kills_away = 0
                if eng and hasattr(eng, "fighters"):
                    fighters = list(getattr(eng, "fighters"))
                    kills_home = sum(1 for f in fighters if getattr(f, "team_id", 0) == 1 and not getattr(f, "alive", True))
                    kills_away = sum(1 for f in fighters if getattr(f, "team_id", 0) == 0 and not getattr(f, "alive", True))
                try:
                    self.career.record_result(fx.id, kills_home, kills_away)
                    self.career.advance_week_if_done()
                    self._flash = f"Result saved: {_team_name(self.career, fx.home_id)} {kills_home}-{kills_away} {_team_name(self.career, fx.away_id)}"
                except Exception as e:
                    self._flash = f"Save failed: {e}"

            self.app.push_state(MatchState(self.app, home, away, on_finish=_on_finish))
        except Exception as e:
            self._flash = f"Play failed: {e}"

    def _sim_week(self) -> None:
        try:
            simulate_week_ai(self.career)
            self._flash = "Simulated this week."
        except Exception as e:
            self._flash = f"Sim failed: {e}"

    def _schedule(self) -> None:
        try:
            from .state_schedule import ScheduleState
            self.app.push_state(ScheduleState(self.app, self.career))
        except Exception as e:
            self._flash = f"Schedule open failed: {e}"

    def _table(self) -> None:
        try:
            from .state_table import TableState
            self.app.push_state(TableState(self.app, self.career))
        except Exception as e:
            self._flash = f"Table open failed: {e}"

    def _roster(self) -> None:
        try:
            from .state_roster_browser import RosterBrowserState
            self.app.push_state(RosterBrowserState(self.app))
        except Exception as e:
            self._flash = f"Roster open failed: {e}"

    def _back(self) -> None:
        self.app.pop_state()

    # pygame hooks
    def handle(self, event) -> None:
        if not self._built:
            return
        for b in (self.btn_play, self.btn_sim, self.btn_sched, self.btn_table, self.btn_roster, self.btn_back):
            if b:
                b.handle(event)
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.rect_panel.collidepoint(mx, my):
                self._list_scroll = max(0, self._list_scroll - event.y * (self._line_h * 3))
                self._clamp_scroll()

    def update(self, dt: float) -> None:
        if not self._built:
            return
        mx, my = pygame.mouse.get_pos()
        for b in (self.btn_play, self.btn_sim, self.btn_sched, self.btn_table, self.btn_roster, self.btn_back):
            if b:
                b.update((mx, my))

    def draw(self, surf) -> None:
        th = self.theme
        surf.fill(th.bg)

        # Toolbar
        draw_panel(surf, self.rect_toolbar, th)
        draw_text(surf, f"Your Team: {self._user_team_name()}",
                  (self.rect_toolbar.x + 12, self.rect_toolbar.centery), 26, th.text, align="midleft")
        draw_text(surf, f"Week {getattr(self.career, 'week', 1)}",
                  (self.rect_toolbar.right - 12, self.rect_toolbar.centery), 26, th.subt, align="midright")
        if self._flash:
            draw_text(surf, self._flash, (self.rect_toolbar.centerx, self.rect_toolbar.bottom + 6), 18, th.subt, align="center")

        # Matchups list (scrollable)
        draw_panel(surf, self.rect_panel, th)
        title_y = self.rect_panel.y + 12
        draw_text(surf, "This Week's Matchups", (self.rect_panel.centerx, title_y), 22, th.text, align="center")

        inner = self.rect_panel.inflate(-12*2, -12*2)
        inner.y += 18  # below title
        inner.h -= 18

        fixtures = list(self._week_fixtures())
        user_tid = getattr(self.career, "user_team_id", None)
        def _is_user_fx(fx) -> int:
            return 0 if (user_tid is not None and (fx.home_id == user_tid or fx.away_id == user_tid)) else 1
        fixtures.sort(key=_is_user_fx)

        # clip & draw
        clip = surf.get_clip()
        surf.set_clip(inner)
        y = inner.y - self._list_scroll
        for fx in fixtures:
            hn = _team_name(self.career, fx.home_id)
            an = _team_name(self.career, fx.away_id)
            is_user = user_tid is not None and (fx.home_id == user_tid or fx.away_id == user_tid)
            text = f"{hn}  {fx.kills_home}-{fx.kills_away}  {an}" if fx.played else f"{hn}  vs  {an}"
            if is_user:
                text = "▶  " + text
            draw_text(surf, text, (inner.x, y), 20, th.text)
            y += self._line_h
        surf.set_clip(clip)

        # Bottom buttons
        for b in (self.btn_play, self.btn_sim, self.btn_sched, self.btn_table, self.btn_roster, self.btn_back):
            if b:
                b.draw(surf, th)

    def _clamp_scroll(self):
        inner_h = self.rect_panel.h - 12*2 - 18
        total_h = max(0, len(list(self._week_fixtures())) * self._line_h)
        max_scroll = max(0, total_h - inner_h)
        self._list_scroll = max(0, min(self._list_scroll, max_scroll))
