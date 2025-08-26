# ui/state_team_select.py
from __future__ import annotations

import pygame
from typing import List, Dict, Any

from .app import BaseState
from .uiutil import Theme, Button, ListView, draw_text, draw_panel

from core.config import LEAGUE_TEAMS, TEAM_SIZE, DEFAULT_SEED
from core.career import Career


class TeamSelectState(BaseState):
    def __init__(self, app):
        self.app = app
        self.theme = Theme()
        self._built = False

        # data
        self.preview_career: Career | None = None
        self.teams: List[Dict[str, Any]] = []
        self.team_names: List[str] = []
        self.sel_idx: int = 0

        # widgets
        self.teams_lv: ListView | None = None
        self.btn_start: Button | None = None
        self.btn_back: Button | None = None

    def enter(self) -> None:
        self._rebuild_data()
        self._build_ui()

    # --- Build ---------------------------------------------------------------
    def _rebuild_data(self) -> None:
        self.preview_career = Career.new(
            seed=DEFAULT_SEED,
            n_teams=LEAGUE_TEAMS,
            team_size=TEAM_SIZE,
            user_team_id=None,
        )
        self.teams = self.preview_career.teams
        self.team_names = [t.get("name", f"Team {t.get('tid', i)}") for i, t in enumerate(self.teams)]
        self.sel_idx = 0

    def _build_ui(self) -> None:
        W, H = self.app.screen.get_size()
        pad = 16
        col_w = (W - pad * 3) // 2
        left = pygame.Rect(pad, pad + 40, col_w, H - pad * 2 - 40)
        right = pygame.Rect(left.right + pad, pad + 40, col_w, H - pad * 2 - 40)

        self.left_rect = left
        self.right_rect = right

        self.teams_lv = ListView(
            pygame.Rect(left.x + 10, left.y + 34, left.w - 20, left.h - 44),
            self.team_names,
            row_h=28,
            on_select=self._on_pick_team
        )

        btn_w, btn_h = 180, 42
        yb = right.bottom - (btn_h + 12)
        self.btn_start = Button(pygame.Rect(right.x + 12, yb, btn_w, btn_h), "Start Season", self._start)
        self.btn_back = Button(pygame.Rect(right.right - (btn_w + 12), yb, btn_w, btn_h), "Back", self._back)

        self._built = True

    # --- Events --------------------------------------------------------------
    def _on_pick_team(self, idx: int) -> None:
        self.sel_idx = int(idx)

    def _start(self) -> None:
        # Create a new career with the chosen user team id
        try:
            team_id = int(self.teams[self.sel_idx]["tid"])
            car = Career.new(
                seed=DEFAULT_SEED,
                n_teams=LEAGUE_TEAMS,
                team_size=TEAM_SIZE,
                user_team_id=team_id,
            )
            from .state_season_hub import SeasonHubState
            self.app.push_state(SeasonHubState(self.app, career=car))
        except Exception as e:
            print("[TeamSelect] Could not start season:", e)

    def _back(self) -> None:
        self.app.pop_state()

    # --- State interface -----------------------------------------------------
    def handle(self, event) -> None:
        if not self._built:
            return
        self.teams_lv.handle(event)
        self.btn_start.handle(event)
        self.btn_back.handle(event)

    def update(self, dt: float) -> None:
        if not self._built:
            self.enter(); return
        mx, my = pygame.mouse.get_pos()
        self.btn_start.update((mx, my))
        self.btn_back.update((mx, my))

    def _draw_roster(self, surf, rect):
        draw_panel(surf, rect, self.theme)
        draw_text(surf, "Your Team", (rect.centerx, rect.y + 6), 20, self.theme.subt, align="center")
        if not self.teams:
            return
        t = self.teams[self.sel_idx]
        draw_text(surf, t.get("name", "Team"), (rect.x + 12, rect.y + 34), 22, self.theme.text)
        roster = t.get("roster") or t.get("fighters") or []
        y = rect.y + 64
        for f in roster[:12]:
            nm = f.get("name", "Unknown"); cls = f.get("class", "Fighter")
            lvl = int(f.get("level", 1)); ovr = int(f.get("ovr", 40))
            draw_text(surf, f"{nm} — {cls}  L{lvl}  OVR {ovr}", (rect.x + 12, y), 18, self.theme.text)
            y += 22

    def draw(self, surface) -> None:
        if not self._built:
            self.enter()
        surface.fill(self.theme.bg)
        draw_text(surface, "Choose Your Team", (surface.get_width() // 2, 12), size=32, color=self.theme.text, align="center")

        # Left: teams list
        draw_panel(surface, self.left_rect, self.theme)
        draw_text(surface, "Teams", (self.left_rect.centerx, self.left_rect.y + 6), 20, self.theme.subt, align="center")
        self.teams_lv.draw(surface, self.theme)  # title already drawn above

        # Right: roster preview + buttons
        self._draw_roster(surface, self.right_rect)
        self.btn_start.draw(surface, self.theme)
        self.btn_back.draw(surface, self.theme)
