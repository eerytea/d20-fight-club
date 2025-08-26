# ui/state_team_select.py — scrollable team list + split roster/details with clickable players
from __future__ import annotations

from typing import Any, Optional, List

import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_text, draw_panel, get_font
from core.career import Career


# ---------- small helpers ----------

def _get(r: Any, keys, default=None):
    """Safely fetch a value from dict/obj via any of several possible keys."""
    if isinstance(keys, str):
        keys = (keys,)
    if isinstance(r, dict):
        for k in keys:
            if k in r:
                return r.get(k, default)
        return default
    for k in keys:
        if hasattr(r, k):
            return getattr(r, k)
    return default


def _team_name(team: dict | Any) -> str:
    return _get(team, ("name",), "Team")


def _fighter_line(f: dict | Any) -> str:
    name = _get(f, ("name",), "?")
    role = _get(f, ("role", "cls", "class"), "")
    lvl  = _get(f, ("level", "lvl", "L"), None)
    ovr  = _get(f, ("ovr", "OVR"), None)

    parts = [name]
    if role:
        parts.append(f"— {role}")
    tail = []
    if lvl is not None:
        tail.append(f"L{int(lvl)}")
    if ovr is not None:
        tail.append(f"OVR {int(ovr)}")
    if tail:
        parts.append("  " + "  ".join(tail))
    return " ".join(parts)


def _fighter_detail_lines(f: dict | Any) -> List[str]:
    lines = []
    # Basic identity
    lines.append(_fighter_line(f))
    # Common stats if present
    hp  = _get(f, ("hp", "HP"), None)
    mhp = _get(f, ("max_hp", "MaxHP", "maxHP"), None)
    ac  = _get(f, ("ac", "AC", "def", "DEF"), None)
    atk = _get(f, ("atk", "ATK", "attack"), None)
    spd = _get(f, ("spd", "SPD", "speed"), None)
    xp  = _get(f, ("xp", "XP"), None)

    stat_pairs = [
        ("HP", f"{hp}/{mhp}" if (hp is not None and mhp is not None) else (str(hp) if hp is not None else None)),
        ("AC", ac),
        ("ATK", atk),
        ("SPD", spd),
        ("XP", xp),
    ]
    for k, v in stat_pairs:
        if v is not None:
            lines.append(f"{k}: {v}")
    # Any traits list?
    traits = _get(f, ("traits", "perks"), None)
    if isinstance(traits, (list, tuple)) and traits:
        lines.append("Traits: " + ", ".join(map(str, traits)))
    return lines


# ---------- state ----------

class TeamSelectState(BaseState):
    """
    New Game -> Team Select:
      * Left: scrollable list of all teams (click to preview)
      * Right top: roster for selected team (click a player)
      * Right bottom: details for the clicked player
    """

    def __init__(self, app):
        self.app = app
        self.theme = Theme()

        # Build a fresh career (uses LEAGUE_TEAMS / TEAM_SIZE from core.config)
        self.career: Career = Career.new()

        # Selection state
        self.selected_tid: int = int(self.career.teams[0]["tid"]) if self.career.teams else 0
        self.selected_player_idx: Optional[int] = None

        # Layout rects
        self.rect_title = pygame.Rect(0, 0, 0, 0)
        self.rect_left  = pygame.Rect(0, 0, 0, 0)  # teams list (scrollable)
        self.rect_rtop  = pygame.Rect(0, 0, 0, 0)  # roster list (clickable)
        self.rect_rbot  = pygame.Rect(0, 0, 0, 0)  # player detail

        # Buttons
        self.btn_start: Button | None = None
        self.btn_back:  Button | None = None

        # Scrolling
        self.team_scroll: int = 0
        self.team_line_h: int = 28
        self.roster_scroll: int = 0
        self.roster_line_h: int = 26

        self._built = False

        # Fonts
        self.font_title = get_font(44)
        self.font_list  = get_font(22)
        self.font_small = get_font(18)

    # ---- lifecycle ----
    def enter(self) -> None:
        self._build()

    # ---- layout ----
    def _build(self) -> None:
        W, H = self.app.width, self.app.height
        pad = 16
        title_h = 64
        right_gap = 18
        right_w = int(W * 0.52)

        # Areas
        self.rect_title = pygame.Rect(0, 0, W, title_h)
        self.rect_left  = pygame.Rect(pad, title_h + pad, W - right_w - pad * 3, H - (title_h + pad * 2) - 78)
        r_x = self.rect_left.right + pad
        r_h_total = self.rect_left.h
        r_top_h = int(r_h_total * 0.58)
        self.rect_rtop = pygame.Rect(r_x, self.rect_left.y, right_w, r_top_h - right_gap // 2)
        self.rect_rbot = pygame.Rect(r_x, self.rect_rtop.bottom + right_gap, right_w, r_h_total - r_top_h - right_gap)

        # Buttons at bottom-right
        bw, bh = 200, 56
        by = self.rect_left.bottom + pad
        self.btn_start = Button(pygame.Rect(self.rect_rbot.right - (bw * 2 + pad), by, bw, bh), "Start Season", self._start)
        self.btn_back  = Button(pygame.Rect(self.rect_rbot.right - bw, by, bw, bh), "Back", self._back)

        self._built = True

    # ---- helpers ----
    def _teams_sorted(self) -> List[dict]:
        return sorted(self.career.teams, key=lambda t: str(t.get("name", "")))

    def _team_by_id(self, tid: int) -> dict:
        for t in self.career.teams:
            if int(t.get("tid")) == int(tid):
                return t
        return self.career.teams[0]

    def _selected_team(self) -> dict:
        return self._team_by_id(self.selected_tid)

    # ---- actions ----
    def _start(self):
        self.career.user_team_id = int(self.selected_tid)
        from .state_season_hub import SeasonHubState
        self.app.push_state(SeasonHubState(self.app, self.career))

    def _back(self):
        self.app.pop_state()

    # ---- events ----
    def handle(self, event) -> None:
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.rect_left.collidepoint(mx, my):
                self.team_scroll = max(0, self.team_scroll - event.y * (self.team_line_h * 3))
                self._clamp_team_scroll()
            elif self.rect_rtop.collidepoint(mx, my):
                self.roster_scroll = max(0, self.roster_scroll - event.y * (self.roster_line_h * 3))
                self._clamp_roster_scroll()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Click in teams list
            if self.rect_left.collidepoint(mx, my):
                inner = self.rect_left.inflate(-12*2, -12*2)
                idx = (my - (inner.y - self.team_scroll)) // self.team_line_h
                teams = self._teams_sorted()
                if 0 <= idx < len(teams):
                    self.selected_tid = int(teams[int(idx)].get("tid"))
                    self.selected_player_idx = None  # reset
            # Click in roster list
            elif self.rect_rtop.collidepoint(mx, my):
                inner = self.rect_rtop.inflate(-12*2, -12*2)
                idx = (my - (inner.y - self.roster_scroll)) // self.roster_line_h
                roster = self._selected_team().get("fighters", [])
                if 0 <= idx < len(roster):
                    self.selected_player_idx = int(idx)

        # Buttons
        self.btn_start.handle(event)
        self.btn_back.handle(event)

    def update(self, dt: float) -> None:
        mx, my = pygame.mouse.get_pos()
        self.btn_start.update((mx, my))
        self.btn_back.update((mx, my))

    # ---- drawing ----
    def draw(self, surf) -> None:
        th = self.theme
        surf.fill(th.bg)

        # Title
        title = "Choose Your Team"
        r = self.font_title.get_rect(title)
        r.center = (self.app.width // 2, self.rect_title.centery + 6)
        self.font_title.render_to(surf, r.topleft, title, th.text)

        # Left: Teams (scroll + clipped)
        draw_panel(surf, self.rect_left, th)
        draw_text(surf, "Teams", (self.rect_left.x + 12, self.rect_left.y - 10), 20, th.subt, align="midleft")

        inner = self.rect_left.inflate(-12*2, -12*2)
        clip = surf.get_clip()
        surf.set_clip(inner)

        teams = self._teams_sorted()
        y = inner.y - self.team_scroll
        for t in teams:
            nm = _team_name(t)
            self.font_list.render_to(surf, (inner.x, int(y)), nm, th.text)
            y += self.team_line_h

        surf.set_clip(clip)
        self._clamp_team_scroll()  # keep tidy after draws

        # Right top: roster box (clickable)
        draw_panel(surf, self.rect_rtop, th)
        team = self._selected_team()
        draw_text(surf, _team_name(team), (self.rect_rtop.x + 12, self.rect_rtop.y + 8), 28, th.text, align="topleft")

        inner_r = self.rect_rtop.inflate(-12*2, -12*2)
        inner_r.y += 30
        clip = surf.get_clip()
        surf.set_clip(inner_r)

        roster = team.get("fighters", [])
        y = inner_r.y - self.roster_scroll
        for i, f in enumerate(roster):
            line = _fighter_line(f)
            # highlight selected player
            if self.selected_player_idx == i:
                # subtle underline bar
                pygame.draw.rect(surf, (80, 120, 200), (inner_r.x, int(y) + self.roster_line_h - 4, inner_r.w, 3), border_radius=2)
            self.font_list.render_to(surf, (inner_r.x, int(y)), line, th.text)
            y += self.roster_line_h

        surf.set_clip(clip)
        self._clamp_roster_scroll()

        # Right bottom: player details
        draw_panel(surf, self.rect_rbot, th)
        draw_text(surf, "Player Details", (self.rect_rbot.x + 12, self.rect_rbot.y + 8), 22, th.subt, align="topleft")

        if isinstance(self.selected_player_idx, int) and 0 <= self.selected_player_idx < len(roster):
            f = roster[self.selected_player_idx]
            lines = _fighter_detail_lines(f)
            y = self.rect_rbot.y + 34
            for ln in lines:
                self.font_small.render_to(surf, (self.rect_rbot.x + 12, y), ln, th.text)
                y += 22
        else:
            self.font_small.render_to(surf, (self.rect_rbot.x + 12, self.rect_rbot.y + 40),
                                      "Click a player above to view stats.", th.subt)

        # Buttons
        self.btn_start.draw(surf, th)
        self.btn_back.draw(surf, th)

    # ---- scroll clamp ----
    def _clamp_team_scroll(self):
        inner_h = self.rect_left.h - 12*2
        total_h = max(0, len(self._teams_sorted()) * self.team_line_h)
        max_scroll = max(0, total_h - inner_h)
        self.team_scroll = max(0, min(self.team_scroll, max_scroll))

    def _clamp_roster_scroll(self):
        inner_h = self.rect_rtop.h - 12*2 - 30
        total_h = max(0, len(self._selected_team().get("fighters", [])) * self.roster_line_h)
        max_scroll = max(0, total_h - inner_h)
        self.roster_scroll = max(0, min(self.roster_scroll, max_scroll))


# convenience factory if anything imports it
def create(app):
    return TeamSelectState(app)
