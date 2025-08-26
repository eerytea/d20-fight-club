# ui/state_exhibition_picker.py
from __future__ import annotations

import pygame
from typing import List, Dict, Any

from .app import BaseState
from .uiutil import Theme, Button, ListView, draw_text, draw_panel

from core.config import LEAGUE_TEAMS, TEAM_SIZE, DEFAULT_SEED
from core.career import Career


class ExhibitionPickerState(BaseState):
    def __init__(self, app):
        self.app = app
        self.theme = Theme()
        self._built = False

        self.preview_career: Career | None = None
        self.teams: List[Dict[str, Any]] = []
        self.team_names: List[str] = []

        self.sel_home: int = 0
        self.sel_away: int = 1

        self.home_lv: ListView | None = None
        self.away_lv: ListView | None = None
        self.btn_start: Button | None = None
        self.btn_back: Button | None = None

    def enter(self) -> None:
        self._rebuild_data()
        self._build_ui()

    def _rebuild_data(self) -> None:
        self.preview_career = Career.new(
            seed=DEFAULT_SEED,
            n_teams=LEAGUE_TEAMS,
            team_size=TEAM_SIZE,
            user_team_id=None,
        )
        self.teams = self.preview_career.teams
        self.team_names = [t.get("name", f"Team {t.get('tid', i)}") for i, t in enumerate(self.teams)]
        if len(self.team_names) >= 2:
            self.sel_home, self.sel_away = 0, 1
        else:
            self.sel_home = self.sel_away = 0

    def _build_ui(self) -> None:
        W, H = self.app.screen.get_size()
        pad = 16
        col_w = (W - pad * 3) // 2
        left = pygame.Rect(pad, pad + 40, col_w, H - pad * 2 - 40)
        right = pygame.Rect(left.right + pad, pad + 40, col_w, H - pad * 2 - 40)

        self.left_rect = left
        self.right_rect = right

        self.home_lv = ListView(
            pygame.Rect(left.x + 10, left.y + 34, left.w - 20, left.h - 44),
            self.team_names,
            row_h=28,
            on_select=self._on_pick_home
        )
        self.away_lv = ListView(
            pygame.Rect(right.x + 10, right.y + 34, right.w - 20, right.h - 100),
            self.team_names,
            row_h=28,
            on_select=self._on_pick_away
        )

        btn_w, btn_h = 180, 42
        yb = right.bottom - (btn_h + 12)
        self.btn_start = Button(pygame.Rect(right.x + 12, yb, btn_w, btn_h), "Start Match", self._start)
        self.btn_back = Button(pygame.Rect(right.right - (btn_w + 12), yb, btn_w, btn_h), "Back", self._back)

        self._built = True

    # --- Events --------------------------------------------------------------
    def _on_pick_home(self, idx: int) -> None:
        self.sel_home = int(idx)
        if self.sel_home == self.sel_away and len(self.team_names) > 1:
            self.sel_away = (self.sel_home + 1) % len(self.team_names)

    def _on_pick_away(self, idx: int) -> None:
        self.sel_away = int(idx)
        if self.sel_home == self.sel_away and len(self.team_names) > 1:
            self.sel_home = (self.sel_away + 1) % len(self.team_names)

    def _start(self) -> None:
        try:
            th = self.teams[self.sel_home]
            ta = self.teams[self.sel_away]
            # Try to open a match viewer if present; otherwise just log
            try:
                from .state_match import MatchState
                self.app.push_state(MatchState(self.app, th, ta))
            except Exception:
                print(f"[Exhibition] Would start: {th.get('name')} vs {ta.get('name')} (viewer not wired)")
        except Exception as e:
            print("[Exhibition] Could not start match:", e)

    def _back(self) -> None:
        self.app.pop_state()

    # --- State interface -----------------------------------------------------
    def handle(self, event) -> None:
        if not self._built:
            return
        self.home_lv.handle(event)
        self.away_lv.handle(event)
        self.btn_start.handle(event)
        self.btn_back.handle(event)

    def update(self, dt: float) -> None:
        if not self._built:
            self.enter(); return
        mx, my = pygame.mouse.get_pos()
        self.btn_start.update((mx, my))
        self.btn_back.update((mx, my))

    def _draw_team_preview(self, surf, rect, label: str, idx: int):
        draw_panel(surf, rect, self.theme)
        draw_text(surf, label, (rect.centerx, rect.y + 6), 20, self.theme.subt, align="center")
        # left list already occupies left; on right we put roster preview for away team
        if 0 <= idx < len(self.teams):
            t = self.teams[idx]
            draw_text(surf, t.get("name", "Team"), (rect.x + 12, rect.y + 34), 22, self.theme.text)
            roster = t.get("roster") or t.get("fighters") or []
            y = rect.y + 64
            for f in roster[:10]:
                nm = f.get("name", "Unknown"); cls = f.get("class", "Fighter")
                lvl = int(f.get("level", 1)); ovr = int(f.get("ovr", 40))
                draw_text(surf, f"{nm} — {cls}  L{lvl}  OVR {ovr}", (rect.x + 12, y), 18, self.theme.text)
                y += 22

    def draw(self, surface) -> None:
        if not self._built:
            self.enter()
        surface.fill(self.theme.bg)
        draw_text(surface, "Exhibition — Pick Home & Away", (surface.get_width() // 2, 12), size=30, color=self.theme.text, align="center")

        # Left: Home list
        draw_panel(surface, self.left_rect, self.theme)
        draw_text(surface, "Home — Teams", (self.left_rect.centerx, self.left_rect.y + 6), 20, self.theme.subt, align="center")
        self.home_lv.draw(surface, self.theme)

        # Right: Away list (top) + preview below
        draw_panel(surface, self.right_rect, self.theme)
        draw_text(surface, "Away — Teams", (self.right_rect.centerx, self.right_rect.y + 6), 20, self.theme.subt, align="center")
        self.away_lv.draw(surface, self.theme)
        self.btn_start.draw(surface, self.theme)
        self.btn_back.draw(surface, self.theme)
