# ui/state_team_select.py
from __future__ import annotations
import pygame
from typing import Any, Dict, List, Optional, Tuple

from core.constants import RACE_DISPLAY
# Your project likely has helpers to compute team OVR/POT etc.
# We keep imports minimal and rely on fields present on the roster dicts.


def _pretty(s: Any) -> str:
    if s is None:
        return "-"
    t = str(s)
    if "_" in t:
        t = t.replace("_", " ")
    return t.title()


def _short_name(full: str) -> str:
    parts = str(full).split()
    if len(parts) == 1:
        return parts[0][:14]
    return f"{parts[0]} {parts[-1]}"[:18]


class TeamTile:
    def __init__(self, team: Dict[str, Any], rect: pygame.Rect, font: pygame.font.Font):
        self.team = team
        self.rect = rect
        self.font = font
        self.hover = False

    @property
    def avg_ovr(self) -> int:
        roster = self.team.get("roster", [])
        if not roster:
            return 0
        return int(sum(int(p.get("OVR", p.get("ovr", 50))) for p in roster) / len(roster))

    @property
    def avg_pot(self) -> int:
        roster = self.team.get("roster", [])
        if not roster:
            return 0
        return int(sum(int(p.get("potential", p.get("POT", 60))) for p in roster) / len(roster))

    def draw(self, screen: pygame.Surface):
        bg = (58, 60, 70) if not self.hover else (76, 78, 96)
        pygame.draw.rect(screen, bg, self.rect, border_radius=12)
        pygame.draw.rect(screen, (28, 30, 36), self.rect, width=2, border_radius=12)
        name = self.team.get("name", "Team")
        country = self.team.get("country", "")
        text1 = self.font.render(_pretty(name), True, (235, 236, 240))
        text2 = self.font.render(_pretty(country), True, (180, 182, 190))
        screen.blit(text1, (self.rect.x + 12, self.rect.y + 10))
        screen.blit(text2, (self.rect.x + 12, self.rect.y + 36))
        # OVR/POT right-justified
        ovp = self.font.render(f"OVR {self.avg_ovr} • POT {self.avg_pot}", True, (210, 212, 220))
        screen.blit(ovp, (self.rect.right - ovp.get_width() - 12, self.rect.y + 10))

    def hit(self, pos: Tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)


class TeamSelectState:
    """
    Team Select:
      - Left: teams grid of tiles (shows average OVR/POT).
      - Right: roster list + player card panel.
      - Start button to begin a new career with selected team.
      - Player card shows SPD (speed) next to AC per your request.
    """

    def __init__(self, app):
        self.app = app
        self.font = None
        self.small = None

        self.teams: List[Dict[str, Any]] = []  # each team has 'name','country','roster':[players]
        self.tiles: List[TeamTile] = []
        self.selected_team_idx: int = 0

        self.roster_scroll = 0
        self.stats_scroll = 0
        self.selected_player_idx: int = 0

        # layout rects
        self.rect_left = pygame.Rect(0, 0, 0, 0)
        self.rect_right = pygame.Rect(0, 0, 0, 0)
        self.rect_roster = pygame.Rect(0, 0, 0, 0)
        self.rect_stats = pygame.Rect(0, 0, 0, 0)
        self.rect_start = pygame.Rect(0, 0, 0, 0)

        # computed heights for scroll clamps
        self.roster_content_h = 0
        self.stats_content_h = 0

    # -------- lifecycle --------
    def enter(self, ctx: Dict[str, Any]):
        if self.font is None:
            pygame.font.init()
            self.font = pygame.font.SysFont("consolas", 20)
            self.small = pygame.font.SysFont("consolas", 16)

        # Expect ctx['teams'] as a list with roster dicts
        self.teams = list(ctx.get("teams", []))
        self.selected_team_idx = 0
        self.selected_player_idx = 0
        self._layout_tiles()

    def exit(self):
        pass

    # -------- layout --------
    def _layout_tiles(self):
        self.tiles.clear()
        # Create tiles in a 2-column grid on the left panel
        w, h = self.app.screen.get_size()
        left_w = int(w * 0.52)
        self.rect_left = pygame.Rect(12, 12, left_w - 18, h - 24)
        self.rect_right = pygame.Rect(left_w, 12, w - left_w - 12, h - 24)

        # Right panel split
        self.rect_roster = pygame.Rect(self.rect_right.x + 12, self.rect_right.y + 12,
                                       self.rect_right.w - 24, int(self.rect_right.h * 0.48))
        self.rect_stats = pygame.Rect(self.rect_right.x + 12, self.rect_roster.bottom + 12,
                                      self.rect_right.w - 24, self.rect_right.bottom - (self.rect_roster.bottom + 84))
        self.rect_start = pygame.Rect(self.rect_right.x + 12, self.rect_right.bottom - 60,
                                      self.rect_right.w - 24, 48)

        # Build tiles
        pad = 12
        tile_w = (self.rect_left.w - pad * 3) // 2
        tile_h = 86
        x = self.rect_left.x + pad
        y = self.rect_left.y + pad
        for i, tm in enumerate(self.teams):
            r = pygame.Rect(x, y, tile_w, tile_h)
            self.tiles.append(TeamTile(tm, r, self.small))
            if i % 2 == 1:
                x = self.rect_left.x + pad
                y += tile_h + pad
            else:
                x += tile_w + pad

    # -------- input --------
    def handle(self, event):
        if event.type == pygame.VIDEORESIZE:
            self._layout_tiles()
            return
        if event.type == pygame.MOUSEMOTION:
            for i, tile in enumerate(self.tiles):
                tile.hover = tile.hit(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # tile click
            for i, tile in enumerate(self.tiles):
                if tile.hit(event.pos):
                    self.selected_team_idx = i
                    self.selected_player_idx = 0
                    return
            # start button
            if self.rect_start.collidepoint(event.pos):
                self._press_start()
                return
            # roster click
            if self.rect_roster.collidepoint(event.pos):
                idx = self._roster_index_at(event.pos)
                if idx is not None:
                    self.selected_player_idx = idx
                    return
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.rect_roster.collidepoint((mx, my)):
                self.roster_scroll += -event.y * 24
            elif self.rect_stats.collidepoint((mx, my)):
                self.stats_scroll += -event.y * 24
        # keyboard quick nav
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._press_start()
            if event.key == pygame.K_UP:
                self.selected_player_idx = max(0, self.selected_player_idx - 1)
            if event.key == pygame.K_DOWN:
                self.selected_player_idx = min(max(0, len(self._roster()) - 1), self.selected_player_idx + 1)

    # -------- drawing --------
    def draw(self, screen: pygame.Surface):
        screen.fill((14, 16, 20))
        # Panels
        pygame.draw.rect(screen, (24, 26, 32), self.rect_left, border_radius=12)
        pygame.draw.rect(screen, (24, 26, 32), self.rect_right, border_radius=12)
        pygame.draw.rect(screen, (36, 38, 46), self.rect_roster, border_radius=10)
        pygame.draw.rect(screen, (36, 38, 46), self.rect_stats, border_radius=10)
        pygame.draw.rect(screen, (60, 160, 90), self.rect_start, border_radius=12)
        pygame.draw.rect(screen, (28, 30, 36), self.rect_left, width=2, border_radius=12)
        pygame.draw.rect(screen, (28, 30, 36), self.rect_right, width=2, border_radius=12)

        # Left: tiles
        for i, tile in enumerate(self.tiles):
            tile.draw(screen)
            if i == self.selected_team_idx:
                pygame.draw.rect(screen, (120, 200, 120), tile.rect, width=3, border_radius=12)

        # Roster
        self._draw_roster(screen)
        # Stats
        self._draw_player_stats(screen)
        # Start button label
        label = self.font.render("START  ▶", True, (15, 22, 16))
        screen.blit(label, (self.rect_start.centerx - label.get_width() // 2,
                            self.rect_start.centery - label.get_height() // 2))

    # -------- roster & stats helpers --------
    def _team(self) -> Dict[str, Any]:
        if not self.teams:
            return {}
        return self.teams[self.selected_team_idx % len(self.teams)]

    def _roster(self) -> List[Dict[str, Any]]:
        return list(self._team().get("roster", []))

    def _country(self) -> Dict[str, Any]:
        return {"name": self._team().get("country", "-")}

    def _selected_player(self) -> Optional[Dict[str, Any]]:
        r = self._roster()
        if not r:
            return None
        idx = max(0, min(len(r) - 1, self.selected_player_idx))
        return r[idx]

    def _roster_index_at(self, pos: Tuple[int, int]) -> Optional[int]:
        if not self.rect_roster.collidepoint(pos):
            return None
        x, y = pos
        clip = self.rect_roster.inflate(-12, -12)
        row_h = 28
        first_idx = max(0, self.roster_scroll // row_h)
        y0 = clip.y + 8 - (self.roster_scroll % row_h)
        roster = self._roster()
        for i in range(first_idx, len(roster)):
            row_rect = pygame.Rect(clip.x + 8, y0 + (i - first_idx) * row_h, clip.w - 16, row_h - 4)
            if row_rect.collidepoint(pos):
                return i
        return None

    def _draw_roster(self, screen: pygame.Surface):
        r = self._roster()
        if not r:
            return
        clip = self.rect_roster.inflate(-12, -12)
        prev = screen.get_clip()
        screen.set_clip(clip)

        y = clip.y + 8 - self.roster_scroll
        row_h = 28
        self.roster_content_h = len(r) * row_h

        for i, p in enumerate(r):
            rect = pygame.Rect(clip.x + 8, y + i * row_h, clip.w - 16, row_h - 4)
            bg = (48, 50, 60) if i == self.selected_player_idx else (42, 44, 52)
            pygame.draw.rect(screen, bg, rect, border_radius=6)
            if i == self.selected_player_idx:
                pygame.draw.rect(screen, (110, 180, 120), rect, width=2, border_radius=6)

            nm = _short_name(p.get("name", f"P{i+1}"))
            race = _pretty(p.get("race", "-"))
            cls = _pretty(p.get("class", "Fighter"))
            ovr = int(p.get("OVR", p.get("ovr", 60)))
            pot = int(p.get("potential", p.get("POT", 70)))

            label = self.small.render(f"{nm}  ({race} {cls})", True, (230, 232, 238))
            meta = self.small.render(f"OVR {ovr} • POT {pot}", True, (195, 198, 206))
            screen.blit(label, (rect.x + 8, rect.y + 3))
            screen.blit(meta, (rect.right - meta.get_width() - 8, rect.y + 3))

        screen.set_clip(prev)

    def _pretty_race(self, race_code: str) -> str:
        code = str(race_code or "").lower()
        return RACE_DISPLAY.get(code, _pretty(code))

    def _display_name(self, p: Dict[str, Any]) -> str:
        return str(p.get("name", "Unknown"))

    def _draw_player_stats(self, screen: pygame.Surface):
        rect = self.rect_stats
        if not rect:
            return

        p = self._selected_player()
        if not p:
            self.stats_content_h = 0
            return

        def G(key, default=None):
            return p.get(key, p.get(key.upper(), default))

        ovr = int(G("ovr", G("OVR", 60)))
        lvl_src = G("level", G("lvl", None))
        level = int(lvl_src) if lvl_src is not None else max(1, ovr // 10)

        name = self._display_name(p)
        race = self._pretty_race(G("race", "-"))
        origin = G("origin", self._country().get("name", "-"))
        pot = int(G("potential", 70))
        cls_raw = G("class", "Fighter")
        cls_disp = _pretty(cls_raw)
        hp = int(G("hp", 10))
        max_hp = int(G("max_hp", hp))
        ac = int(G("ac", 12))
        spd = int(G("speed", G("SPD", 4)))

        STR = int(G("str", G("STR", 10)))
        DEX = int(G("dex", G("DEX", 10)))
        CON = int(G("con", G("CON", 10)))
        INT = int(G("int", G("INT", 10)))
        WIS = int(G("wis", G("WIS", 10)))
        CHA = int(G("cha", G("CHA", 10)))
        age = int(G("age", 18))

        wpn = G("weapon", {})
        weapon_name = (wpn.get("name") if isinstance(wpn, dict)
                       else (wpn if isinstance(wpn, str) else "-"))
        armor_val = (G("armor_name", None) or G("equipped_armor", None) or
                     (G("armor", {}).get("name") if isinstance(G("armor", None), dict) else "-"))

        clip = rect.inflate(-12, -12)
        prev = screen.get_clip()
        screen.set_clip(clip)

        x0 = rect.x + 12
        y = rect.y + 12 - self.stats_scroll
        line_h = self.font.get_height() + 6

        def line(text: str):
            nonlocal y
            surf = self.font.render(text, True, (230, 232, 237))
            screen.blit(surf, (x0, y))
            y += line_h

        line(f"{name}    AGE: {age}    LVL: {level}")
        line(f"{race}    {origin}    OVR: {ovr}    POT: {pot}")
        # NEW: add SPD on the same line as AC
        line(f"{cls_disp}    HP: {hp}/{max_hp}    AC: {ac}    SPD: {spd}")

        y += 4
        labels = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
        vals = (STR, DEX, CON, INT, WIS, CHA)
        col_w = (rect.w - 24) // 6
        top_y = y
        for i, lab in enumerate(labels):
            lx = x0 + i * col_w + col_w // 2
            surf = self.small.render(lab, True, (205, 206, 212))
            screen.blit(surf, (lx - surf.get_width() // 2, top_y))
        y = top_y + self.small.get_height() + 8
        for i, v in enumerate(vals):
            lx = x0 + i * col_w + col_w // 2
            surf = self.small.render(str(v), True, (240, 241, 245))
            screen.blit(surf, (lx - surf.get_width() // 2, y))
        y += self.small.get_height() + 12

        line(f"Armor: {armor_val}    Weapon: {weapon_name}")

        self.stats_content_h = max(0, (y - (rect.y + 12)))
        screen.set_clip(prev)

    # -------- start action --------
    def _press_start(self):
        """Start career with currently selected team."""
        team = self._team()
        if not team:
            return
        if hasattr(self.app, "start_career_with_team"):
            try:
                self.app.start_career_with_team(team)
            except Exception:
                pass
        # If your app uses state stack:
        if hasattr(self.app, "push_state"):
            pass  # handled by caller; we just provide the hook

# convenience alias, if you prefer the old name
TeamSelect = TeamSelectState

__all__ = ["TeamSelectState", "TeamSelect"]
