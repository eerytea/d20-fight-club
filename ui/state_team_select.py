# ui/state_team_select.py — robust team/roster lists with ListView (no bleed), tidy details
from __future__ import annotations

from typing import Any, List, Optional
import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_text, draw_panel, get_font, ListView
from core.career import Career


def _get(obj: Any, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _team_name(t: Any) -> str:
    return _get(t, "name", "Team")


def _fighter_line(f: Any) -> str:
    name = _get(f, "name", "?")
    role = _get(f, "class", _get(f, "role", ""))
    lvl  = _get(f, "level", 1)
    ovr  = _get(f, "ovr", _get(f, "OVR", None))
    parts: List[str] = [str(name)]
    if role:
        parts += ["—", str(role)]
    if lvl is not None:
        parts += ["  L", str(lvl)]
    if ovr is not None:
        parts += ["  OVR", str(ovr)]
    return " ".join(parts)


class TeamSelectState(BaseState):
    """
    New Game -> Team Select:
      * Left panel: scrollable list of all teams (clip-safe), click to select.
      * Right top: roster list of the selected team, click a player.
      * Right bottom: player details (HP/AC/Move, 6 attrs, Armor/Weapon).
      * Start Season / Back buttons along the bottom.
    """

    def __init__(self, app, career: Optional[Career] = None):
        self.app = app
        self.theme = Theme()
        self.career: Career = career or Career.new()

        # Selection
        self.selected_tid: int = int(_get(self.career.teams[0], "tid", 0)) if self.career.teams else 0
        self.selected_player_idx: int = -1

        # Layout rects
        self.rect_title = pygame.Rect(0, 0, 0, 0)
        self.rect_left  = pygame.Rect(0, 0, 0, 0)
        self.rect_rtop  = pygame.Rect(0, 0, 0, 0)
        self.rect_rbot  = pygame.Rect(0, 0, 0, 0)
        self.rect_buttons = pygame.Rect(0, 0, 0, 0)

        # Widgets
        self.btn_start: Button | None = None
        self.btn_back: Button | None  = None
        self.lv_teams: ListView | None = None
        self.lv_roster: ListView | None = None

        # Fonts
        self.font_title = get_font(48)
        self.font_head  = get_font(28)
        self.font_det_h = get_font(20)
        self.font_det   = get_font(16)

    # ---------- lifecycle ----------
    def enter(self) -> None:
        self._build()

    def _build(self) -> None:
        W, H = self.app.width, self.app.height
        pad = 16
        title_h = 72
        self.rect_title = pygame.Rect(0, 0, W, title_h)

        # Left list panel
        right_w = int(W * 0.54)
        self.rect_left = pygame.Rect(pad, title_h + pad, W - right_w - pad * 3, H - (title_h + pad * 3) - 60)

        # Right combined area, split into roster/details
        right_all = pygame.Rect(self.rect_left.right + pad, self.rect_left.y, right_w, self.rect_left.h)
        split = int(right_all.h * 0.56)
        self.rect_rtop = pygame.Rect(right_all.x, right_all.y, right_all.w, split - pad // 2)
        self.rect_rbot = pygame.Rect(right_all.x, self.rect_rtop.bottom + pad, right_all.w, right_all.bottom - (self.rect_rtop.bottom + pad))

        # Buttons row
        self.rect_buttons = pygame.Rect(right_all.x, self.rect_left.bottom + pad, right_all.w, 52)
        bw, bh = 200, 52
        bx = self.rect_buttons.right - (bw * 2 + pad)
        by = self.rect_buttons.y
        self.btn_start = Button(pygame.Rect(bx, by, bw, bh), "Start Season", self._start)
        self.btn_back  = Button(pygame.Rect(bx + bw + pad, by, bw, bh), "Back", self._back)

        # ListViews (clip area inside panels; we leave header space via top_offset in draw)
        team_items = [_team_name(t) for t in self.career.teams]
        self.lv_teams = ListView(self.rect_left.inflate(-16, -16), team_items, row_h=28, on_select=self._on_team_pick)
        # Pre-select by tid
        try:
            self.lv_teams.selected = next(i for i, t in enumerate(self.career.teams) if int(_get(t, "tid", -1)) == self.selected_tid)
        except StopIteration:
            self.lv_teams.selected = 0 if self.career.teams else -1

        roster = self._roster_for_tid(self.selected_tid)
        self.lv_roster = ListView(self.rect_rtop.inflate(-16, -48), [_fighter_line(f) for f in roster], row_h=28, on_select=self._on_player_pick)

    # ---------- helpers ----------
    def _roster_for_tid(self, tid: int) -> List[Any]:
        team = next((t for t in self.career.teams if int(_get(t, "tid", -1)) == int(tid)), None)
        return list(_get(team, "fighters", _get(team, "roster", []))) if team else []

    # ---------- actions ----------
    def _on_team_pick(self, index: int) -> None:
        if 0 <= index < len(self.career.teams):
            self.selected_tid = int(_get(self.career.teams[index], "tid", self.selected_tid))
            roster = self._roster_for_tid(self.selected_tid)
            if self.lv_roster:
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

    # ---------- events/update ----------
    def handle(self, event) -> None:
        if self.lv_teams:  self.lv_teams.handle(event)
        if self.lv_roster: self.lv_roster.handle(event)
        self.btn_start.handle(event)
        self.btn_back.handle(event)

    def update(self, dt: float) -> None:
        mp = pygame.mouse.get_pos()
        # ListView.update is a no-op (kept for API compatibility)
        self.btn_start.update(mp)
        self.btn_back.update(mp)

    # ---------- draw ----------
    def draw(self, surf) -> None:
        th = self.theme
        surf.fill(th.bg)

        # Title
        title = "Choose Your Team"
        r = self.font_title.get_rect(title)
        r.center = (self.app.width // 2, self.rect_title.centery + 6)
        self.font_title.render_to(surf, r.topleft, title, th.text)

        # Left: Teams
        draw_panel(surf, self.rect_left, th)
        draw_text(surf, "Teams", (self.rect_left.x + 12, self.rect_left.y + 10), 20, th.subt, align="topleft")
        if self.lv_teams:
            # Leave space for header: start rows at y + 32
            self.lv_teams.draw(surf, th, top_offset=32, font_size=20)

        # Right top: roster
        draw_panel(surf, self.rect_rtop, th)
        team_obj = next((t for t in self.career.teams if int(_get(t, "tid", -1)) == self.selected_tid), None)
        draw_text(surf, _team_name(team_obj) if team_obj else "—", (self.rect_rtop.x + 12, self.rect_rtop.y + 10), 26, th.text, align="topleft")
        if self.lv_roster:
            # a bit more header space for longer team names
            self.lv_roster.draw(surf, th, top_offset=40, font_size=20)

        # Right bottom: player details
        draw_panel(surf, self.rect_rbot, th)
        inner = self.rect_rbot.inflate(-16, -16)
        roster = self._roster_for_tid(self.selected_tid)
        if 0 <= self.selected_player_idx < len(roster):
            f = roster[self.selected_player_idx]
            header = _fighter_line(f)
            self.font_head.render_to(surf, (inner.x, inner.y), header, th.text)

            y = inner.y + 24
            hp  = _get(f, "hp", _get(f, "HP", 0))
            mhp = _get(f, "max_hp", _get(f, "MaxHP", hp))
            ac  = _get(f, "AC", _get(f, "ac", 10))
            mv  = _get(f, "speed", _get(f, "SPD", _get(f, "move", 6)))
            self.font_det_h.render_to(surf, (inner.x, y), f"HP: {hp}/{mhp}    AC: {ac}    Movement: {mv}", th.text)
            y += 22

            labels = ["STR","DEX","CON","INT","WIS","CHA"]
            vals = [str(_get(f, k.lower(), _get(f, k, "—"))) for k in labels]
            col_w = inner.w // 6
            for i, lab in enumerate(labels):
                lx = inner.x + i * col_w + col_w // 2
                rlab = self.font_det.get_rect(lab); rlab.midtop = (lx, y)
                self.font_det.render_to(surf, rlab.topleft, lab, th.subt)
            y += 16
            for i, val in enumerate(vals):
                lx = inner.x + i * col_w + col_w // 2
                rvl = self.font_det.get_rect(val); rvl.midtop = (lx, y)
                self.font_det.render_to(surf, rvl.topleft, val, th.text)
            y += 26

            arm = _get(f, "armor", _get(f, "equipped_armor", "—"))
            wep = _get(f, "weapon", _get(f, "equipped_weapon", "—"))
            self.font_det.render_to(surf, (inner.x, y), f"Armor: {arm}    Weapon: {wep}", th.text)
        else:
            self.font_det.render_to(surf, (inner.x, inner.y), "Click a player above to view stats.", th.subt)

        # Buttons
        self.btn_start.draw(surf, th)
        self.btn_back.draw(surf, th)


def create(app):
    return TeamSelectState(app)
