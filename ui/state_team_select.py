# ui/state_team_select.py — robust scrolling with ListView (no bleed), selectable roster
from __future__ import annotations
from typing import Any, List, Optional
import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_text, draw_panel, get_font, ListView
from core.career import Career


def _get(r: Any, key: str, default=None):
    if isinstance(r, dict):
        return r.get(key, default)
    return getattr(r, key, default)


def _team_name(t: Any) -> str:
    return _get(t, "name", "Team")


def _fighter_line(f: Any) -> str:
    name = _get(f, "name", "?")
    role = _get(f, "class", _get(f, "role", ""))
    lvl  = _get(f, "level", 1)
    ovr  = _get(f, "ovr", _get(f, "OVR", None))
    bits = [name]
    if role: bits += ["—", str(role)]
    if lvl is not None: bits += ["  L", str(lvl)]
    if ovr is not None: bits += ["  OVR", str(ovr)]
    return " ".join(map(str, bits))


class TeamSelectState(BaseState):
    def __init__(self, app, career: Optional[Career] = None):
        self.app = app
        self.theme = Theme()
        self.career: Career = career or Career.new()

        # Layout rects
        self.rect_title = pygame.Rect(0, 0, 0, 0)
        self.rect_left  = pygame.Rect(0, 0, 0, 0)
        self.rect_rtop  = pygame.Rect(0, 0, 0, 0)
        self.rect_rbot  = pygame.Rect(0, 0, 0, 0)

        # Widgets
        self.btn_start: Button | None = None
        self.btn_back: Button | None = None
        self.lv_teams: ListView | None = None
        self.lv_roster: ListView | None = None

        # Selection
        first_tid = _get(self.career.teams[0], "tid", 0) if self.career.teams else 0
        self.selected_tid: int = int(first_tid)
        self.selected_player_idx: int = -1

        # Fonts
        self.font_title = get_font(56)
        self.font_head  = get_font(30)
        self.font_det_h = get_font(20)
        self.font_det   = get_font(16)

    # lifecycle
    def enter(self) -> None:
        self._build()

    def _build(self) -> None:
        W, H = self.app.width, self.app.height
        pad = 16
        title_h = 80
        right_w = int(W * 0.55)

        self.rect_title = pygame.Rect(0, 0, W, title_h)
        self.rect_left  = pygame.Rect(pad, title_h + pad, W - right_w - pad * 3, H - (title_h + pad * 2))
        right_all       = pygame.Rect(self.rect_left.right + pad, self.rect_left.y, right_w, self.rect_left.h)

        # split right into top (roster) + bottom (details)
        split = int(right_all.h * 0.55)
        self.rect_rtop = pygame.Rect(right_all.x, right_all.y, right_all.w, split - pad // 2)
        self.rect_rbot = pygame.Rect(right_all.x, self.rect_rtop.bottom + pad, right_all.w, right_all.bottom - (self.rect_rtop.bottom + pad))

        # Buttons
        bw, bh = 220, 56
        bx = self.rect_rbot.centerx - bw - 10
        by = self.rect_rbot.bottom + pad
        self.btn_start = Button(pygame.Rect(bx, by, bw, bh), "Start Season", self._start)
        self.btn_back  = Button(pygame.Rect(bx + bw + 20, by, bw, bh), "Back", self._back)

        # ListViews
        team_items = [_team_name(t) for t in self.career.teams]
        self.lv_teams = ListView(self.rect_left.inflate(-24, -24), team_items, row_h=28, on_select=self._on_team_pick)
        # Pre-select current team id
        try:
            idx = next(i for i, t in enumerate(self.career.teams) if int(_get(t, "tid", -1)) == self.selected_tid)
            self.lv_teams.selected = idx
        except StopIteration:
            pass

        roster = self._roster_for_tid(self.selected_tid)
        self.lv_roster = ListView(self.rect_rtop.inflate(-24, -48), [_fighter_line(f) for f in roster], row_h=28, on_select=self._on_player_pick)

    def _roster_for_tid(self, tid: int) -> List[Any]:
        team = next((t for t in self.career.teams if int(_get(t, "tid", -1)) == int(tid)), None)
        return list(_get(team, "fighters", _get(team, "roster", []))) if team else []

    # actions
    def _on_team_pick(self, index: int) -> None:
        if 0 <= index < len(self.career.teams):
            self.selected_tid = int(_get(self.career.teams[index], "tid", self.selected_tid))
            # Refresh roster list for the new team
            roster = self._roster_for_tid(self.selected_tid)
            self.lv_roster.set_items([_fighter_line(f) for f in roster])
            self.selected_player_idx = -1

    def _on_player_pick(self, index: int) -> None:
        self.selected_player_idx = index

    def _start(self) -> None:
        self.career.user_team_id = int(self.selected_tid)
        from .state_season_hub import SeasonHubState
        self.app.push_state(SeasonHubState(self.app, self.career))

    def _back(self) -> None:
        self.app.pop_state()

    # events
    def handle(self, event) -> None:
        if self.lv_teams:  self.lv_teams.handle(event)
        if self.lv_roster: self.lv_roster.handle(event)
        self.btn_start.handle(event)
        self.btn_back.handle(event)

    def update(self, dt: float) -> None:
        mp = pygame.mouse.get_pos()
        if self.lv_teams:  self.lv_teams.update(mp)
        if self.lv_roster: self.lv_roster.update(mp)
        self.btn_start.update(mp)
        self.btn_back.update(mp)

    # draw
    def draw(self, surf) -> None:
        th = self.theme
        surf.fill(th.bg)

        # Title
        title = "Choose Your Team"
        tr = self.font_title.get_rect(title)
        tr.center = (self.app.width // 2, self.rect_title.centery + 6)
        self.font_title.render_to(surf, tr.topleft, title, th.text)

        # Left teams panel
        draw_panel(surf, self.rect_left, th)
        draw_text(surf, "Teams", (self.rect_left.x + 12, self.rect_left.y + 10), 22, th.subt, align="topleft")
        if self.lv_teams:
            self.lv_teams.draw(surf, th)

        # Right top: roster
        draw_panel(surf, self.rect_rtop, th)
        team_name = next((t for t in self.career.teams if int(_get(t, "tid", -1)) == self.selected_tid), None)
        draw_text(surf, _team_name(team_name) if team_name else "—", (self.rect_rtop.x + 12, self.rect_rtop.y + 10), 28, th.text, align="topleft")
        if self.lv_roster:
            self.lv_roster.draw(surf, th)

        # Right bottom: player details
        draw_panel(surf, self.rect_rbot, th)
        inner = self.rect_rbot.inflate(-24, -24)
        roster = self._roster_for_tid(self.selected_tid)
        if 0 <= self.selected_player_idx < len(roster):
            f = roster[self.selected_player_idx]
            header = _fighter_line(f)
            self.font_head.render_to(surf, (inner.x, inner.y), header, th.text)

            y = inner.y + 24
            # Compact details layout you requested
            hp = _get(f, "hp", _get(f, "HP", 0))
            mhp = _get(f, "max_hp", _get(f, "MaxHP", hp))
            ac = _get(f, "ac", _get(f, "AC", 10))
            spd = _get(f, "speed", _get(f, "SPD", 6))
            line = f"HP: {hp}/{mhp}    AC: {ac}    Movement: {spd}"
            self.font_det_h.render_to(surf, (inner.x, y), line, th.text)
            y += 24

            labels = ["STR","DEX","CON","INT","WIS","CHA"]
            vals = [str(_get(f,k.lower(), _get(f,k,10))) for k in labels]
            # grid of 6 labels/values
            col_w = max(64, inner.w // 6)
            for i,lbl in enumerate(labels):
                lx = inner.x + i * col_w
                self.font_det.render_to(surf, (lx, y), lbl, th.subt)
            y += 18
            for i,val in enumerate(vals):
                vx = inner.x + i * col_w
                r = self.font_det.get_rect(val); r.midtop = (vx + col_w//2, y)
                self.font_det.render_to(surf, r.topleft, val, th.text)
            y += 28

            arm = _get(f, "armor", "—")
            wep = _get(f, "weapon", "—")
            self.font_det.render_to(surf, (inner.x, y), f"Armor: {arm}    Weapon: {wep}", th.text)
        else:
            self.font_det.render_to(surf, (inner.x, inner.y), "Click a player above to view stats.", th.subt)

        # Buttons
        self.btn_start.draw(surf, th)
        self.btn_back.draw(surf, th)


def create(app):
    return TeamSelectState(app)
