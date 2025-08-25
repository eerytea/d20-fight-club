# ui/state_season_hub.py
from __future__ import annotations

from typing import Optional, List, Tuple

try:
    import pygame
except Exception:  # pragma: no cover
    pygame = None  # type: ignore

from .uiutil import Theme, Button, draw_panel, draw_text
from .app import App
from core.sim import simulate_week_full_except, simulate_week_ai
from core.save import save_career
from core import config


class SeasonHubState:
    """
    Minimal but functional season hub:
      - Play My Match: finds user's unplayed fixture this week and opens MatchState
      - Sim Rest: simulates the rest of the week except the user's fixture
      - Roster / Schedule / Table: open respective screens (mouse UI kit)
      - Save
    """
    def __init__(self, app: Optional[App] = None, *, career=None) -> None:
        self.app: App | None = app
        self.career = career
        self._buttons: List[Button] = []
        self._panel_rect = None

    def enter(self) -> None:
        if pygame is None or self.app is None:
            return
        W, H = self.app.width, self.app.height
        pad = 16

        btn_w, btn_h = 200, 44
        y0 = H // 3
        x = pad

        def r(i: int) -> "pygame.Rect":
            return pygame.Rect(x, y0 + i * (btn_h + 12), btn_w, btn_h)

        def _msg(text: str) -> None:
            try:
                from .state_message import MessageState
                self.app.safe_push(MessageState, message=text)
            except Exception:
                print(text)

        def play_my_match():
            fx_list = [f for f in self.career.fixtures if f.week == self.career.week]
            if not fx_list:
                _msg("No fixtures this week")
                return
            # find the user fixture
            my_tid = getattr(self.career, "user_team_id", None)
            if my_tid is None:
                _msg("No user team set")
                return
            try:
                idx = next(i for i, fx in enumerate(fx_list) if (fx.home_id == my_tid or fx.away_id == my_tid))
            except StopIteration:
                _msg("No match for your team this week")
                return
            fx = fx_list[idx]
            if fx.played:
                _msg("Your fixture is already played")
                return

            home_tid, away_tid = fx.home_id, fx.away_id
            # derive deterministic seed
            try:
                seed = self.app.derive_seed("season", fx.week, home_tid, away_tid)
            except Exception:
                seed = None
            try:
                from .state_match import MatchState
                self.app.safe_push(MatchState, career=self.career, home_team_id=home_tid, away_team_id=away_tid, seed=seed, title=f"Week {fx.week}: {self.career.team_names[home_tid]} vs {self.career.team_names[away_tid]}")
            except Exception:
                _msg("Match viewer not available")

        def sim_rest():
            fx_list = [f for f in self.career.fixtures if f.week == self.career.week]
            if not fx_list:
                _msg("No fixtures this week")
                return
            my_tid = getattr(self.career, "user_team_id", None)
            if my_tid is None:
                _msg("No user team set")
                return
            try:
                idx = next(i for i, fx in enumerate(fx_list) if (fx.home_id == my_tid or fx.away_id == my_tid))
            except StopIteration:
                idx = -1
            simulate_week_full_except(self.career, idx if idx >= 0 else 10_000)
            _msg("Simulated the rest of the week.")

        def open_roster():
            try:
                from .state_roster import RosterState
                self.app.safe_push(RosterState, career=self.career)
            except Exception:
                _msg("Roster screen not available")

        def open_schedule():
            try:
                from .state_schedule import ScheduleState
                self.app.safe_push(ScheduleState, career=self.career)
            except Exception:
                _msg("Schedule screen not available")

        def open_table():
            try:
                from .state_table import TableState
                self.app.safe_push(TableState, career=self.career)
            except Exception:
                _msg("Table screen not available")

        def save_now():
            save_career(self.career)
            _msg("Game saved.")

        self._buttons = [
            Button(r(0), "Play My Match", on_click=play_my_match),
            Button(r(1), "Sim Rest of Week", on_click=sim_rest),
            Button(r(2), "Roster", on_click=open_roster),
            Button(r(3), "Schedule", on_click=open_schedule),
            Button(r(4), "Table", on_click=open_table),
            Button(r(5), "Save", on_click=save_now),
            Button(r(6), "Back", on_click=lambda: self.app.pop_state()),
        ]

        self._panel_rect = pygame.Rect(self._buttons[0].rect.right + 24, 24, self.app.width - self._buttons[0].rect.right - 24 - 16, self.app.height - 48)

    def exit(self) -> None:
        self._buttons.clear()

    def handle_event(self, event: "pygame.event.Event") -> bool:
        for b in self._buttons:
            if b.handle_event(event):
                return True
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: "pygame.Surface") -> None:
        th = Theme()
        surface.fill(th.bg)
        title = f"Season Hub — Week {self.career.week}"
        draw_text(surface, title, (surface.get_width() // 2, 12), size=28, align="center")
        for b in self._buttons:
            b.draw(surface)

        draw_panel(surface, self._panel_rect, title="Overview")
        x = self._panel_rect.x + 12
        y = self._panel_rect.y + 8
        draw_text(surface, f"Teams: {len(self.career.team_names)}", (x, y), size=18, color=th.fg); y += 22
        draw_text(surface, f"Fixtures this week: {sum(1 for f in self.career.fixtures if f.week == self.career.week)}", (x, y), size=18, color=th.fg); y += 22
        my_tid = getattr(self.career, "user_team_id", None)
        if my_tid is not None:
            draw_text(surface, f"My Team: {self.career.team_names[my_tid]}", (x, y), size=18, color=th.fg); y += 22
