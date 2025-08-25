# ui/state_exhibition_picker.py
from __future__ import annotations

from typing import Optional

try:
    import pygame
except Exception:  # pragma: no cover
    pygame = None  # type: ignore

from .uiutil import Theme, Button, ListView, draw_panel, draw_text
from .app import App
from core.career import new_career


class ExhibitionPickerState:
    def __init__(self, app: Optional[App] = None) -> None:
        self.app: App | None = app
        self.career = None

        self.home_lv: ListView | None = None
        self.away_lv: ListView | None = None
        self.home_roster_lv: ListView | None = None
        self.away_roster_lv: ListView | None = None

        self.home_team: int | None = None
        self.away_team: int | None = None

        self.btn_start: Button | None = None
        self.btn_back: Button | None = None

    # ------------- lifecycle -------------

    def enter(self) -> None:
        if pygame is None or self.app is None:
            return
        self.career = new_career(seed=getattr(self.app, "seed", None), user_team_id=None)

        W, H = self.app.width, self.app.height
        pad = 16
        col_w = (W - pad * 3) // 2
        list_h = int(H * 0.5) - 60

        # Home column
        home_list_rect = pygame.Rect(pad, pad, col_w, list_h)
        home_roster_rect = pygame.Rect(pad, home_list_rect.bottom + pad, col_w, list_h)

        # Away column
        away_list_rect = pygame.Rect(home_list_rect.right + pad, pad, col_w, list_h)
        away_roster_rect = pygame.Rect(away_list_rect.x, away_list_rect.bottom + pad, col_w, list_h)

        self.home_lv = ListView(home_list_rect, self.career.team_names, row_h=28)
        self.away_lv = ListView(away_list_rect, self.career.team_names, row_h=28)

        self.home_roster_lv = ListView(home_roster_rect, [], row_h=24)
        self.away_roster_lv = ListView(away_roster_rect, [], row_h=24)

        # Buttons
        btn_w, btn_h = 220, 44
        self.btn_start = Button(pygame.Rect(W - pad - btn_w, H - pad - btn_h, btn_w, btn_h), "Start Match", on_click=self._start_match)
        self.btn_back = Button(pygame.Rect(pad, H - pad - btn_h, btn_w, btn_h), "Back", on_click=lambda: self.app.pop_state())

    def exit(self) -> None:
        pass

    # ------------- events -------------

    def handle_event(self, event: "pygame.event.Event") -> bool:
        consumed = False

        if self.home_lv and self.home_lv.handle_event(event):
            self.home_team = self.home_lv.selected
            self._refresh_roster(is_home=True)
            consumed = True

        if self.away_lv and self.away_lv.handle_event(event):
            self.away_team = self.away_lv.selected
            self._refresh_roster(is_home=False)
            consumed = True

        if self.home_roster_lv and self.home_roster_lv.handle_event(event):
            consumed = True
        if self.away_roster_lv and self.away_roster_lv.handle_event(event):
            consumed = True

        if self.btn_start and self.btn_start.handle_event(event):
            consumed = True
        if self.btn_back and self.btn_back.handle_event(event):
            consumed = True

        return consumed

    def update(self, dt: float) -> None:
        pass

    # ------------- rendering -------------

    def draw(self, surface: "pygame.Surface") -> None:
        th = Theme()
        surface.fill(th.bg)
        draw_text(surface, "Exhibition — Pick Home & Away", (surface.get_width() // 2, 20), size=30, align="center")

        self.home_lv.draw(surface, title="Home — Teams")
        self.away_lv.draw(surface, title="Away — Teams")
        self.home_roster_lv.draw(surface, title="Home — Roster")
        self.away_roster_lv.draw(surface, title="Away — Roster")

        self.btn_start.draw(surface)
        self.btn_back.draw(surface)

        # Small hint
        draw_text(surface, "Tip: mouse wheel scrolls lists", (surface.get_width() // 2, surface.get_height() - 28),
                  size=16, align="center", color=th.muted)

    # ------------- helpers -------------

    def _refresh_roster(self, *, is_home: bool) -> None:
        if self.career is None:
            return
        tid = self.home_team if is_home else self.away_team
        if tid is None:
            (self.home_roster_lv if is_home else self.away_roster_lv).set_items([])
            return
        roster = self.career.rosters[tid]
        labels = [f"{f['name']}  (OVR {f.get('ovr', 50)})" for f in roster]
        (self.home_roster_lv if is_home else self.away_roster_lv).set_items(labels)

    def _start_match(self) -> None:
        if self.home_team is None or self.away_team is None:
            self._msg("Pick both Home and Away teams")
            return

        # seed for exhibition (deterministic wrt app.seed and selection)
        try:
            seed = self.app.derive_seed("exhibition", self.home_team, self.away_team)
        except Exception:
            seed = None

        # Try to push your exhibition/match viewer if present; otherwise show a message
        try:
            from .state_exhibition import ExhibitionState
            self.app.replace_state(ExhibitionState(home_team_id=self.home_team, away_team_id=self.away_team, seed=seed))
        except Exception:
            self._msg("Exhibition viewer not wired yet")

    def _msg(self, text: str) -> None:
        try:
            from .state_message import MessageState
            self.app.safe_push(MessageState, message=text)
        except Exception:
            print(text)
