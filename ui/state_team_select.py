# ui/state_team_select.py — clipped team list; split roster/details; full-row highlight; compact details that fit
from __future__ import annotations

from typing import Any, Optional, List, Tuple

import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_text, draw_panel, get_font
from core.career import Career

# ---------- robust getters ----------

def _get(r: Any, keys, default=None):
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
    return _get(team, "name", "Team")

def _fighter_line(f: dict | Any) -> str:
    name = _get(f, "name", "?")
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

def _stat_val(f: Any, names: Tuple[str, ...], default=None):
    return _get(f, names, default)

def _equip_name(f: Any, candidates: Tuple[str, ...]) -> str:
    item = _get(f, candidates, None)
    if not item:
        return "—"
    if isinstance(item, str):
        return item
    nm = _get(item, ("name", "Name", "id", "kind"), None)
    return str(nm) if nm is not None else "—"

def _text_width(font, text: str, size: Optional[int] = None) -> int:
    """Safe width measure for pygame.freetype.Font (avoid size=None TypeError)."""
    try:
        if size is None:
            return font.get_rect(text).width
        return font.get_rect(text, size=size).width
    except TypeError:
        return font.get_rect(text).width

def _ellipsize(font, text: str, max_w: int, size: Optional[int] = None) -> str:
    if _text_width(font, text, size=size) <= max_w:
        return text
    s = text
    while s and _text_width(font, s + "…", size=size) > max_w:
        s = s[:-1]
    return (s + "…") if s else "…"

# ---------- state ----------

class TeamSelectState(BaseState):
    """
    New Game -> Team Select:
      * Left: scrollable list of teams (hard-clipped to content area; no overlap)
      * Right top: roster (click a player)
      * Right bottom: compact details that always fit the box
    """

    def __init__(self, app):
        self.app = app
        self.theme = Theme()

        self.career: Career = Career.new()

        self.selected_tid: int = int(self.career.teams[0]["tid"]) if self.career.teams else 0
        self.selected_player_idx: Optional[int] = None

        self.rect_title = pygame.Rect(0, 0, 0, 0)
        self.rect_left  = pygame.Rect(0, 0, 0, 0)
        self.rect_rtop  = pygame.Rect(0, 0, 0, 0)
        self.rect_rbot  = pygame.Rect(0, 0, 0, 0)

        self.btn_start: Button | None = None
        self.btn_back:  Button | None = None

        self.team_scroll: int = 0
        self.team_line_h: int = 28
        self.roster_scroll: int = 0
        self.roster_line_h: int = 28

        self._built = False

        # Fonts (slightly smaller in details so everything fits)
        self.font_title = get_font(48)
        self.font_list  = get_font(24)
        self.font_sub   = get_font(22)
        self.font_det_h1 = get_font(20)  # header in details
        self.font_det    = get_font(16)  # HP/AC/Move + armor/weapon
        self.font_det_s  = get_font(14)  # attribute labels

    # ---- lifecycle ----
    def enter(self) -> None:
        self._build()

    # ---- layout ----
    def _build(self) -> None:
        W, H = self.app.width, self.app.height
        pad = 16
        title_h = 72
        right_gap = 14
        right_w = int(W * 0.54)

        self.rect_title = pygame.Rect(0, 0, W, title_h)
        bottom_h = 74
        self.rect_left  = pygame.Rect(pad, title_h + pad, W - right_w - pad * 3, H - (title_h + pad * 2) - bottom_h)

        r_x = self.rect_left.right + pad
        r_h_total = self.rect_left.h
        r_top_h = int(r_h_total * 0.58)
        self.rect_rtop = pygame.Rect(r_x, self.rect_left.y, right_w, r_top_h - right_gap // 2)
        self.rect_rbot = pygame.Rect(r_x, self.rect_rtop.bottom + right_gap, right_w, r_h_total - r_top_h - right_gap)

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
            # Click in teams list (respect the same inner content rect used for drawing)
            if self.rect_left.collidepoint(mx, my):
                content = self._left_content_rect()
                if content.collidepoint(mx, my):
                    idx = (my - (content.y - self.team_scroll)) // self.team_line_h
                    teams = self._teams_sorted()
                    if 0 <= idx < len(teams):
                        self.selected_tid = int(teams[int(idx)].get("tid"))
                        self.selected_player_idx = None
            # Click in roster list
            elif self.rect_rtop.collidepoint(mx, my):
                inner = self.rect_rtop.inflate(-12*2, -12*2)
                inner.y += 36
                idx = (my - (inner.y - self.roster_scroll)) // self.roster_line_h
                roster = self._selected_team().get("fighters", [])
                if 0 <= idx < len(roster):
                    self.selected_player_idx = int(idx)

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

        # Left: Teams (draw with clip to CONTENT area so it never overlaps the header)
        draw_panel(surf, self.rect_left, th)
        draw_text(surf, "Teams", (self.rect_left.x + 12, self.rect_left.y + 10), 20, th.subt, align="topleft")

        content = self._left_content_rect()  # strictly inside the panel, below "Teams"
        saved = surf.get_clip()
        surf.set_clip(content)

        teams = self._teams_sorted()
        y = content.y - self.team_scroll
        for t in teams:
            nm = _team_name(t)
            self.font_list.render_to(surf, (content.x, int(y)), nm, th.text)
            y += self.team_line_h

        surf.set_clip(saved)
        self._clamp_team_scroll()

        # Right top: roster box (clickable)
        draw_panel(surf, self.rect_rtop, th)
        team = self._selected_team()
        draw_text(surf, _team_name(team), (self.rect_rtop.x + 12, self.rect_rtop.y + 10), 30, th.text, align="topleft")

        inner_r = self.rect_rtop.inflate(-12*2, -12*2)
        inner_r.y += 36
        saved = surf.get_clip()
        surf.set_clip(inner_r)

        roster = team.get("fighters", [])
        y = inner_r.y - self.roster_scroll
        row_w = inner_r.w
        for i, f in enumerate(roster):
            row_rect = pygame.Rect(inner_r.x, int(y), row_w, self.roster_line_h)
            if self.selected_player_idx == i:
                pygame.draw.rect(surf, (70, 110, 190), row_rect, border_radius=6)
            self.font_list.render_to(surf, (row_rect.x + 8, row_rect.y + 2), _fighter_line(f), th.text)
            y += self.roster_line_h

        surf.set_clip(saved)
        self._clamp_roster_scroll()

        # Right bottom: compact details (always fits)
        draw_panel(surf, self.rect_rbot, th)
        draw_text(surf, "Player Details", (self.rect_rbot.x + 12, self.rect_rbot.y + 10), 22, th.subt, align="topleft")

        inner_d = self.rect_rbot.inflate(-12*2, -12*2)
        inner_d.y += 30

        if isinstance(self.selected_player_idx, int) and 0 <= self.selected_player_idx < len(roster):
            f = roster[self.selected_player_idx]

            # 1) Header line (ellipsized)
            header = _fighter_line(f)
            header_fit = _ellipsize(self.font_det_h1, header, inner_d.w)
            self.font_det_h1.render_to(surf, (inner_d.x, inner_d.y), header_fit, self.theme.text)

            y = inner_d.y + 22

            # 2) HP X/X, AC, Movement
            hp  = _stat_val(f, ("hp", "HP"))
            mhp = _stat_val(f, ("max_hp", "MaxHP", "maxHP", "mhp"))
            ac  = _stat_val(f, ("ac", "AC", "def", "DEF"))
            spd = _stat_val(f, ("spd", "SPD", "speed", "move", "movement"))

            hp_txt = f"HP: {int(hp)}/{int(mhp)}" if (hp is not None and mhp is not None) else ("HP: —" if hp is None else f"HP: {int(hp)}")
            ac_txt = f"AC: {int(ac)}" if ac is not None else "AC: —"
            mv_txt = f"Movement: {int(spd)}" if spd is not None else "Movement: —"

            x = inner_d.x
            self.font_det.render_to(surf, (x, y), hp_txt, self.theme.text)
            x += _text_width(self.font_det, hp_txt) + 18
            self.font_det.render_to(surf, (x, y), ac_txt, self.theme.text)
            x += _text_width(self.font_det, ac_txt) + 18
            self.font_det.render_to(surf, (x, y), mv_txt, self.theme.text)

            y += 22

            # 3) Six-attribute grid (labels then centered values)
            labels = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
            name_map = {
                "STR": ("str", "STR", "strength"),
                "DEX": ("dex", "DEX", "dexterity"),
                "CON": ("con", "CON", "constitution"),
                "INT": ("int", "INT", "intelligence"),
                "WIS": ("wis", "WIS", "wisdom"),
                "CHA": ("cha", "CHA", "charisma"),
            }
            col_w = inner_d.w // 6
            row_x = inner_d.x
            # labels
            for i, lab in enumerate(labels):
                cx = row_x + i * col_w + col_w // 2
                rlab = self.font_det_s.get_rect(lab)
                rlab.midtop = (cx, y)
                self.font_det_s.render_to(surf, rlab.topleft, lab, self.theme.subt)
            y += 14
            # values
            for i, lab in enumerate(labels):
                val = _stat_val(f, name_map[lab], "—")
                txt = str(val if val is not None else "—")
                rvl = self.font_list.get_rect(txt)
                cx = row_x + i * col_w + col_w // 2
                rvl.midtop = (cx, y)
                self.font_list.render_to(surf, rvl.topleft, txt, self.theme.text)

            y += 26

            # 4) Armor and Weapon (split halves, ellipsized)
            armor = _equip_name(f, ("equipped_armor", "armor", "armour", "gear_armor"))
            weapon = _equip_name(f, ("equipped_weapon", "weapon", "main_hand", "wpn"))

            arm_left = "Armor: "
            wep_left = "Weapon: "
            half_w = inner_d.w // 2 - 8
            arm_fit = arm_left + _ellipsize(self.font_det, armor, half_w - _text_width(self.font_det, arm_left))
            wep_fit = wep_left + _ellipsize(self.font_det, weapon, half_w - _text_width(self.font_det, wep_left))

            self.font_det.render_to(surf, (inner_d.x, y), arm_fit, self.theme.text)
            self.font_det.render_to(surf, (inner_d.x + half_w + 16, y), wep_fit, self.theme.text)
        else:
            self.font_det.render_to(surf, (inner_d.x, inner_d.y), "Click a player above to view stats.", self.theme.subt)

        # Buttons
        self.btn_start.draw(surf, self.theme)
        self.btn_back.draw(surf, self.theme)

    # ---- content rect for left list (used for both draw & click) ----
    def _left_content_rect(self) -> pygame.Rect:
        inner = self.rect_left.inflate(-12*2, -12*2)
        inner.y += 24  # space below "Teams"
        inner.h -= 24  # keep bottom margin symmetric
        return inner

    # ---- scroll clamp ----
    def _clamp_team_scroll(self):
        inner_h = self._left_content_rect().h
        total_h = max(0, len(self._teams_sorted()) * self.team_line_h)
        max_scroll = max(0, total_h - inner_h)
        self.team_scroll = max(0, min(self.team_scroll, max_scroll))

    def _clamp_roster_scroll(self):
        inner_h = self.rect_rtop.h - 12*2 - 36
        total_h = max(0, len(self._selected_team().get("fighters", [])) * self.roster_line_h)
        max_scroll = max(0, total_h - inner_h)
        self.roster_scroll = max(0, min(self.roster_scroll, max_scroll))

def create(app):
    return TeamSelectState(app)
