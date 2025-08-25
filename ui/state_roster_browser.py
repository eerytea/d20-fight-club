# ui/state_roster_browser.py
from __future__ import annotations

import pygame
from typing import List, Dict, Optional, Any, Tuple
import random

# ----- Try to use your UI kit. Provide simple fallbacks if it's missing. -----
try:
    from .uiutil import Theme, Button, ListView, draw_panel, draw_text
    HAS_UIKIT = True
except Exception:
    HAS_UIKIT = False
    class Theme:
        def __init__(self):
            self.bg = (20, 24, 28)
            self.panel = (32, 36, 44)
            self.text = (230, 230, 235)
            self.accent = (90, 140, 255)
            self.btn_bg = (50, 55, 64)
            self.btn_bg_hover = (70, 75, 84)
            self.btn_text = (240, 240, 245)
        @staticmethod
        def default():
            return Theme()
    def draw_panel(surf, rect, title=None):
        pygame.draw.rect(surf, (32, 36, 44), rect, border_radius=8)
        if title:
            font = pygame.font.SysFont(None, 20)
            txt = font.render(title, True, (220, 220, 225))
            surf.blit(txt, (rect.x + 10, rect.y + 8))
    # match ui/uiutil API: size first, then color
    def draw_text(surf, text, pos, size=18, color=(230, 230, 235)):
        font = pygame.font.SysFont(None, size)
        surf.blit(font.render(text, True, color), pos)
    class Button:
        def __init__(self, rect: pygame.Rect, text: str, on_click):
            self.rect = pygame.Rect(rect)
            self.text = text
            self.on_click = on_click
            self._hover = False
            self._font = pygame.font.SysFont(None, 22)
        def handle_event(self, ev):
            if ev.type == pygame.MOUSEMOTION:
                self._hover = self.rect.collidepoint(ev.pos)
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                if self.rect.collidepoint(ev.pos):
                    if callable(self.on_click):
                        self.on_click()
        def draw(self, surf, theme: Theme):
            pygame.draw.rect(surf, theme.btn_bg_hover if self._hover else theme.btn_bg, self.rect, border_radius=8)
            txt = self._font.render(self.text, True, theme.btn_text)
            surf.blit(txt, txt.get_rect(center=self.rect.center))
    class ListView:
        def __init__(self, rect: pygame.Rect, items: List[str], on_select=None, row_height: int = 28):
            self.rect = pygame.Rect(rect)
            self.items = items[:]
            self.on_select = on_select
            self.row_height = row_height
            self.selected = 0 if items else -1
            self.scroll = 0
            self._font = pygame.font.SysFont(None, 20)
        def set_items(self, items: List[str]):
            self.items = items[:]
            self.selected = 0 if items else -1
            self.scroll = 0
        def handle_event(self, ev):
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if self.rect.collidepoint(ev.pos) and ev.button == 1:
                    idx = (ev.pos[1] - self.rect.y) // self.row_height + self.scroll
                    if 0 <= idx < len(self.items):
                        self.selected = idx
                        if callable(self.on_select):
                            self.on_select(idx)
                elif self.rect.collidepoint(ev.pos) and ev.button in (4, 5):
                    if ev.button == 4:
                        self.scroll = max(0, self.scroll - 1)
                    else:
                        max_scroll = max(0, len(self.items) - self.rect.height // self.row_height)
                        self.scroll = min(max_scroll, self.scroll + 1)
        def draw(self, surf, theme: Theme):
            pygame.draw.rect(surf, (30, 34, 40), self.rect, border_radius=8)
            visible = self.rect.height // self.row_height
            start = self.scroll
            end = min(len(self.items), start + visible)
            y = self.rect.y
            for i in range(start, end):
                r = pygame.Rect(self.rect.x + 2, y + 2, self.rect.w - 4, self.row_height - 4)
                if i == self.selected:
                    pygame.draw.rect(surf, (55, 60, 75), r, border_radius=6)
                txt = self._font.render(str(self.items[i]), True, (230, 230, 235))
                surf.blit(txt, (r.x + 8, r.y + 4))
                y += self.row_height

# ----- Core imports for generating teams/rosters -------------------------------
from core.config import LEAGUE_TEAMS, TEAM_SIZE, DEFAULT_SEED
from core.career import Career
from core.rng import child_seed


class RosterBrowserState:
    def __init__(self, app):
        self.app = app
        self.theme: Theme = Theme.default() if hasattr(Theme, "default") else Theme()
        self.screen = app.screen
        self.W, self.H = self.screen.get_size()

        self._seed_counter = 0
        self._build_league(self._derive_seed("init"))

        self.selected_team_index: int = 0
        self._build_ui()

    def _derive_seed(self, label: str) -> int:
        if hasattr(self.app, "derive_seed") and callable(getattr(self.app, "derive_seed")):
            return int(self.app.derive_seed(f"roster:{label}:{self._seed_counter}"))
        return child_seed(DEFAULT_SEED, f"roster:{label}:{self._seed_counter}")

    def _build_league(self, seed: int):
        career = Career.new(seed=seed, n_teams=LEAGUE_TEAMS, team_size=TEAM_SIZE, user_team_id=None)
        self.teams: List[Dict[str, Any]] = career.teams
        self.team_names = [t.get("name", f"Team {t.get('tid', i)}") for i, t in enumerate(self.teams)]

    def _regenerate(self):
        self._seed_counter += 1
        self._build_league(self._derive_seed("regen"))
        self._refresh_lists()

    def _build_ui(self):
        pad = 16
        col_w = (self.W - pad * 3) // 2
        left_x = pad
        right_x = left_x + col_w + pad

        self.rect_left = pygame.Rect(left_x, pad, col_w, self.H - pad * 2)
        self.rect_right = pygame.Rect(right_x, pad, col_w, self.H - pad * 2)

        team_list_rect = pygame.Rect(self.rect_left.x + 12, self.rect_left.y + 36, self.rect_left.w - 24, self.rect_left.h - 48)
        self.lv_teams = ListView(team_list_rect, self.team_names, on_select=self._on_pick_team)

        roster_rect = pygame.Rect(self.rect_right.x + 12, self.rect_right.y + 36, self.rect_right.w - 24, self.rect_right.h - 100)
        self.lv_roster = ListView(roster_rect, self._format_roster_lines(self.teams[self.selected_team_index]))

        btn_w, btn_h = 160, 40
        btn_y = self.rect_right.bottom - (btn_h + 16)

        self.btn_generate = Button(
            pygame.Rect(self.rect_right.x + 12, btn_y, btn_w, btn_h),
            "Generate",
            self._regenerate
        )
        self.btn_back = Button(
            pygame.Rect(self.rect_right.right - (btn_w + 12), btn_y, btn_w, btn_h),
            "Back",
            self._go_back
        )

    def _refresh_lists(self):
        self.team_names = [t.get("name", f"Team {t.get('tid', i)}") for i, t in enumerate(self.teams)]
        self.lv_teams.set_items(self.team_names)
        self.selected_team_index = 0 if self.teams else -1
        if self.selected_team_index >= 0:
            self.lv_roster.set_items(self._format_roster_lines(self.teams[self.selected_team_index]))
        else:
            self.lv_roster.set_items([])

    def _go_back(self):
        if hasattr(self.app, "pop_state"):
            self.app.pop_state()

    def _on_pick_team(self, idx: int):
        self.selected_team_index = idx
        team = self.teams[idx]
        self.lv_roster.set_items(self._format_roster_lines(team))

    def _format_roster_lines(self, team: Dict[str, Any]) -> List[str]:
        roster = team.get("roster") or team.get("fighters") or []
        out: List[str] = []
        for f in roster:
            nm = f.get("name", "Unknown")
            cls = f.get("class", "Fighter")
            lvl = int(f.get("level", 1))
            ovr = int(f.get("ovr", 40))
            out.append(f"{nm}  —  {cls}  L{lvl}  OVR {ovr}")
        if not out:
            out = ["(empty roster)"]
        return out

    def handle_event(self, ev):
        if ev.type == pygame.KEYUP and ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self._go_back(); return
        self.lv_teams.handle_event(ev)
        self.lv_roster.handle_event(ev)
        self.btn_generate.handle_event(ev)
        self.btn_back.handle_event(ev)

    def update(self, dt: float):
        pass

    def draw(self, surf):
        surf.fill(self.theme.bg if hasattr(self.theme, "bg") else (20, 24, 28))
        draw_panel(surf, self.rect_left, "Teams")
        self.lv_teams.draw(surf, self.theme)
        draw_panel(surf, self.rect_right, "Roster")
        self.lv_roster.draw(surf, self.theme)
        self.btn_generate.draw(surf, self.theme)
        self.btn_back.draw(surf, self.theme)
        # size first, then color
        draw_text(surf, "Browse all teams and regenerate league rosters.", (16, 8), 20, (200, 210, 220))
