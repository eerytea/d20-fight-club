# ui/state_roster_browser.py
from __future__ import annotations

import pygame
from typing import List, Dict, Any, Optional
import random

from .app import BaseState
from .uiutil import Theme, Button, ListView, draw_text, draw_panel

# Core bits
from core.config import LEAGUE_TEAMS, TEAM_SIZE, DEFAULT_SEED
from core.career import Career


class RosterBrowserState(BaseState):
    """
    Simple two-pane browser:
      - Left: list of teams
      - Right: roster preview for the selected team
    Bottom right has "Generate All" (regenerates rosters) and "Back".
    """

    def __init__(self, app):
        self.app = app
        self.theme = Theme()
        self._built = False

        # Data
        self.preview_career: Optional[Career] = None
        self.teams: List[Dict[str, Any]] = []
        self.team_names: List[str] = []
        self.sel_idx: int = 0

        # UI
        self.rect_left: pygame.Rect | None = None
        self.rect_right: pygame.Rect | None = None

        self.teams_lv: ListView | None = None
        self.btn_generate: Button | None = None
        self.btn_back: Button | None = None

    # --- Lifecycle -----------------------------------------------------------
    def enter(self) -> None:
        self._rebuild_data()
        self._build_ui()

    # --- Data ----------------------------------------------------------------
    def _rebuild_data(self) -> None:
        # Build a preview league (safe for smoke tests and interactive browsing)
        self.preview_career = Career.new(
            seed=DEFAULT_SEED,
            n_teams=LEAGUE_TEAMS,
            team_size=TEAM_SIZE,
            user_team_id=None,
        )
        self.teams = self.preview_career.teams
        self.team_names = [t.get("name", f"Team {t.get('tid', i)}") for i, t in enumerate(self.teams)]
        self.sel_idx = 0 if self.team_names else -1

    # --- UI ------------------------------------------------------------------
    def _build_ui(self) -> None:
        W, H = self.app.width, self.app.height
        pad = 16
        col_w = (W - pad * 3) // 2

        self.rect_left = pygame.Rect(pad, pad, col_w, H - pad * 2)
        self.rect_right = pygame.Rect(self.rect_left.right + pad, pad, col_w, H - pad * 2)

        # List of teams on the left
        self.teams_lv = ListView(
            pygame.Rect(self.rect_left.x + 10, self.rect_left.y + 34, self.rect_left.w - 20, self.rect_left.h - 44),
            self.team_names,
            row_h=28,
            on_select=self._on_pick_team,
        )

        # Buttons (bottom-right, inside right panel)
        btn_w, btn_h, gap = 180, 42, 10
        yb = self.rect_right.bottom - (btn_h + 12)
        self.btn_generate = Button(pygame.Rect(self.rect_right.x + 12, yb, btn_w, btn_h), "Generate All", self._generate_all)
        self.btn_back = Button(pygame.Rect(self.rect_right.right - (btn_w + 12), yb, btn_w, btn_h), "Back", self._back)

        self._built = True

    # --- Actions -------------------------------------------------------------
    def _on_pick_team(self, idx: int) -> None:
        self.sel_idx = int(idx)

    def _generate_all(self) -> None:
        """
        Clear and regenerate every team roster. Keep team names/colors stable,
        but roll a fresh seed for variety.
        """
        try:
            if self.preview_career is None:
                self._rebuild_data()
                return
            # Roll a new seed but keep current names/colors
            new_seed = (getattr(self.preview_career, "seed", DEFAULT_SEED) * 1103515245 + 12345) & 0x7fffffff
            # Some builds name field differently; we capture names/colors directly
            names = [t.get("name") for t in self.preview_career.teams]
            colors = [tuple(t.get("color", (180, 180, 220))) for t in self.preview_career.teams]

            # Create a fresh career with same count/size (new rosters)
            fresh = Career.new(
                seed=new_seed,
                n_teams=len(self.preview_career.teams),
                team_size=TEAM_SIZE,
                user_team_id=None,
                team_names=names if all(isinstance(n, str) for n in names) else None,
                team_colors=colors if all(isinstance(c, tuple) and len(c) == 3 for c in colors) else None,
            )
            self.preview_career = fresh
            self.teams = fresh.teams
            self.team_names = [t.get("name", f"Team {t.get('tid', i)}") for i, t in enumerate(self.teams)]
            if self.teams_lv:
                self.teams_lv.set_items(self.team_names)
            self.sel_idx = 0 if self.team_names else -1
        except Exception as e:
            print("[RosterBrowser] Generate failed:", e)

    def _back(self) -> None:
        self.app.pop_state()

    # --- State interface -----------------------------------------------------
    def handle(self, event) -> None:
        if not self._built:
            return
        if self.teams_lv:
            self.teams_lv.handle(event)
        if self.btn_generate:
            self.btn_generate.handle(event)
        if self.btn_back:
            self.btn_back.handle(event)

    def update(self, dt: float) -> None:
        if not self._built:
            self.enter(); return
        mx, my = pygame.mouse.get_pos()
        if self.btn_generate:
            self.btn_generate.update((mx, my))
        if self.btn_back:
            self.btn_back.update((mx, my))

    def _draw_team_preview(self, surf: pygame.Surface, rect: pygame.Rect) -> None:
        if not self.teams or self.sel_idx < 0 or self.sel_idx >= len(self.teams):
            draw_text(surf, "No team selected.", (rect.centerx, rect.centery), 20, self.theme.subt, align="center")
            return
        t = self.teams[self.sel_idx]
        draw_text(surf, t.get("name", "Team"), (rect.x + 12, rect.y + 34), 22, self.theme.text)
        roster = t.get("roster") or t.get("fighters") or []
        y = rect.y + 64
        for f in roster[:16]:
            nm = f.get("name", "Unknown"); cls = f.get("class", "Fighter")
            lvl = int(f.get("level", 1)); ovr = int(f.get("ovr", 40))
            draw_text(surf, f"{nm} — {cls}  L{lvl}  OVR {ovr}", (rect.x + 12, y), 18, self.theme.text)
            y += 22

    def draw(self, surf: pygame.Surface) -> None:
        if not self._built:
            self.enter()
        th = self.theme
        surf.fill(th.bg)

        # Header
        draw_text(surf, "Roster Browser", (surf.get_width() // 2, 12), 30, th.text, align="center")

        # Left panel: Teams
        draw_panel(surf, self.rect_left, th)
        draw_text(surf, "Teams", (self.rect_left.centerx, self.rect_left.y + 6), 20, th.subt, align="center")
        if self.teams_lv:
            self.teams_lv.draw(surf, th)

        # Right panel: Roster preview
        draw_panel(surf, self.rect_right, th)
        draw_text(surf, "Roster", (self.rect_right.centerx, self.rect_right.y + 6), 20, th.subt, align="center")
        self._draw_team_preview(surf, self.rect_right)

        # Buttons
        if self.btn_generate:
            self.btn_generate.draw(surf, th)
        if self.btn_back:
            self.btn_back.draw(surf, th)
