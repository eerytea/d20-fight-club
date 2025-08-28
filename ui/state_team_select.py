# ui/state_team_select.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from typing import Callable, List, Optional, Dict, Any, Tuple
import random

try:
    from core.career import Career
except Exception:
    Career = None  # type: ignore

def _import_opt(fullname: str):
    try:
        module_name, class_name = fullname.rsplit(".", 1)
        mod = __import__(module_name, fromlist=[class_name])
        return getattr(mod, class_name)
    except Exception:
        return None

# ----------------- Small UI primitives -----------------
@dataclass
class Button:
    rect: pygame.Rect
    text: str
    action: Callable[[], None]
    hover: bool = False
    disabled: bool = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, selected: bool=False):
        bg = (58, 60, 70) if not self.hover else (76, 78, 90)
        if selected:
            bg = (88, 92, 110)
        if self.disabled:
            bg = (48, 48, 54)
        pygame.draw.rect(surface, bg, self.rect, border_radius=8)
        pygame.draw.rect(surface, (24, 24, 28), self.rect, 2, border_radius=8)
        color = (230, 230, 235) if not self.disabled else (150, 150, 155)
        txt = font.render(self.text, True, color)
        surface.blit(txt, (self.rect.x + 14, self.rect.y + (self.rect.h - txt.get_height()) // 2))

    def handle(self, event: pygame.event.Event):
        if self.disabled:
            return
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.action()

# ----------------- Deterministic world generation -----------------
_COUNTRIES = [
    "Albion", "Valoria", "Karthos", "Eldoria",
    "Norska", "Zafira", "Solheim", "Drakken",
]

_TEAM_WORDS_A = ["Iron", "Golden", "Crimson", "Emerald", "Shadow", "Storm", "Royal", "Wild"]
_TEAM_WORDS_B = ["Wolves", "Falcons", "Titans", "Knights", "Serpents", "Guard", "Ravens", "Bullheads"]

def _rand_name(rng: random.Random) -> str:
    return f"{rng.choice(_TEAM_WORDS_A)} {rng.choice(_TEAM_WORDS_B)}"

def _rand_color(rng: random.Random) -> Tuple[int, int, int]:
    # muted but distinct
    return (rng.randint(60, 220), rng.randint(60, 220), rng.randint(60, 220))

def _ovr(p: Dict[str, Any]) -> int:
    # Simple derived overall; tweak later to match your class assigner
    STR = p.get("STR", 10); DEX = p.get("DEX", 10); CON = p.get("CON", 10)
    INT = p.get("INT", 8);  WIS = p.get("WIS", 8);  CHA = p.get("CHA", 8)
    # Emphasize physical a bit
    score = (STR*0.35 + DEX*0.35 + CON*0.30 + (INT+WIS+CHA)*0.10)
    return int(round(score))

def _make_player(pid: int, team_id: int, rng: random.Random) -> Dict[str, Any]:
    # Jersey number from pid (1..99 loop)
    jersey = (pid % 99) + 1
    # Attributes
    STR = rng.randint(8, 14)
    DEX = rng.randint(8, 14)
    CON = rng.randint(8, 14)
    INT = rng.randint(7, 12)
    WIS = rng.randint(7, 12)
    CHA = rng.randint(7, 12)
    hp = rng.randint(8, 12)
    p = {
        "pid": pid,
        "name": f"#{jersey:02d}",
        "team_id": team_id,
        "hp": hp, "max_hp": hp, "ac": rng.randint(8, 12), "alive": True,
        "STR": STR, "DEX": DEX, "CON": CON, "INT": INT, "WIS": WIS, "CHA": CHA,
    }
    p["OVR"] = _ovr(p)
    return p

def _make_league(country: str, level: int, rng: random.Random, team_size: int = 8) -> Dict[str, Any]:
    # level 1 = top league, level 2 = bottom league
    name = f"{country} {'Premier' if level == 1 else 'Division'}"
    teams = []
    for i in range(20):
        tname = _rand_name(rng)
        color = _rand_color(rng)
        # team_id will be remapped later to 0..19 for the selected league
        tid = i
        fighters = [_make_player(pid=j, team_id=tid, rng=rng) for j in range(team_size)]
        teams.append({"tid": tid, "name": tname, "color": color, "fighters": fighters})
    return {"name": name, "level": level, "teams": teams}

def _build_world(seed: int) -> Dict[str, Any]:
    rng = random.Random(seed)
    world = {"countries": []}
    for cname in _COUNTRIES:
        # independent rng per country for stability
        crng = random.Random((seed << 1) ^ hash(cname))
        leagues = [
            _make_league(cname, level=1, rng=crng),
            _make_league(cname, level=2, rng=crng),
        ]
        world["countries"].append({"name": cname, "leagues": leagues})
    return world

# ----------------- Team Select State -----------------
class TeamSelectState:
    """
    3-column layout:
      - Left: Countries (8)
      - Middle: League toggle (Top / Bottom) + 20-team list
      - Right: Top = players of selected team; Bottom = selected player's stats
    Start Season builds a Career from the selected league (20 teams).
    """
    def __init__(self, app):
        self.app = app
        self.font = pygame.font.SysFont(None, 24)
        self.h1 = pygame.font.SysFont(None, 34)
        self.h2 = pygame.font.SysFont(None, 22)

        # Panels (computed in enter)
        self.rect_countries: Optional[pygame.Rect] = None
        self.rect_league: Optional[pygame.Rect] = None
        self.rect_detail: Optional[pygame.Rect] = None
        self.rect_roster: Optional[pygame.Rect] = None
        self.rect_stats: Optional[pygame.Rect] = None

        # Data
        self.seed = getattr(self.app, "world_seed", 7777)
        self.world = _build_world(self.seed)
        # Persist selections in app for convenience
        self.country_idx = getattr(self.app, "last_country_idx", 0)
        self.league_level = getattr(self.app, "last_league_level", 1)  # 1 or 2
        self.team_idx: Optional[int] = None
        self.player_idx: Optional[int] = None

        # Scroll state (pixels)
        self.scroll_teams = 0
        self.scroll_players = 0

        # Buttons
        self.btns: List[Button] = []
        self.toggle_top: Optional[Button] = None
        self.toggle_bottom: Optional[Button] = None

    def enter(self):
        self._layout()

    # ------------- Layout -------------
    def _layout(self):
        w, h = self.app.screen.get_size()
        pad = 16
        # left column: countries
        left_w = max(220, int(w * 0.22))
        mid_w = max(380, int(w * 0.34))
        right_w = w - (left_w + mid_w + pad*4)

        self.rect_countries = pygame.Rect(pad, 70, left_w, h - 70 - pad)
        self.rect_league    = pygame.Rect(self.rect_countries.right + pad, 70, mid_w, h - 70 - pad)
        self.rect_detail    = pygame.Rect(self.rect_league.right + pad, 70, right_w, h - 70 - pad)

        # right split: roster top, stats bottom
        self.rect_roster = pygame.Rect(self.rect_detail.x, self.rect_detail.y, self.rect_detail.w, int(self.rect_detail.h*0.60))
        self.rect_stats  = pygame.Rect(self.rect_detail.x, self.rect_roster.bottom + pad, self.rect_detail.w, self.rect_detail.bottom - (self.rect_roster.bottom + pad))

        # bottom-right control buttons
        btn_w, btn_h = 160, 44
        by = self.rect_detail.bottom - btn_h - 10
        bx = self.rect_detail.right - btn_w - 10
        self.btns = [
            Button(pygame.Rect(bx, by, btn_w, btn_h), "Start Season", self._start),
            Button(pygame.Rect(bx - btn_w - 10, by, btn_w, btn_h), "Back", self._back),
        ]

        # league toggle buttons at top of middle panel
        tg_w, tg_h = 140, 36
        tgy = self.rect_league.y + 12
        self.toggle_top = Button(pygame.Rect(self.rect_league.x + 12, tgy, tg_w, tg_h), "Top League", lambda: self._set_level(1))
        self.toggle_bottom = Button(pygame.Rect(self.rect_league.x + 12 + tg_w + 10, tgy, tg_w, tg_h), "Bottom League", lambda: self._set_level(2))

    # ------------- Convenience getters -------------
    def _countries(self) -> List[Dict[str, Any]]:
        return self.world["countries"]

    def _country(self) -> Dict[str, Any]:
        return self._countries()[self.country_idx % len(self._countries())]

    def _league(self) -> Dict[str, Any]:
        leagues = self._country()["leagues"]
        return next(l for l in leagues if int(l["level"]) == int(self.league_level))

    def _teams(self) -> List[Dict[str, Any]]:
        return self._league()["teams"]

    def _selected_team(self) -> Optional[Dict[str, Any]]:
        if self.team_idx is None: return None
        ts = self._teams()
        if 0 <= self.team_idx < len(ts): return ts[self.team_idx]
        return None

    def _selected_player(self) -> Optional[Dict[str, Any]]:
        t = self._selected_team()
        if not t: return None
        if self.player_idx is None: return None
        fs = t.get("fighters", [])
        if 0 <= self.player_idx < len(fs): return fs[self.player_idx]
        return None

    # ------------- Actions -------------
    def _set_level(self, level: int):
        if level not in (1, 2): return
        self.league_level = level
        setattr(self.app, "last_league_level", level)
        # keep previous team_idx if in range; else reset
        self.team_idx = None
        self.player_idx = None
        self.scroll_teams = 0
        self.scroll_players = 0

    def _select_country(self, idx: int):
        self.country_idx = idx % len(self._countries())
        setattr(self.app, "last_country_idx", self.country_idx)
        # reset downstream selections
        self.team_idx = None
        self.player_idx = None
        self.scroll_teams = 0
        self.scroll_players = 0

    def _select_team(self, idx: int):
        self.team_idx = idx
        self.player_idx = 0
        self.scroll_players = 0

    def _select_player(self, idx: int):
        self.player_idx = idx

    def _back(self):
        self.app.pop_state()

    def _start(self):
        team = self._selected_team()
        if not team:
            return
        SeasonHubState = _import_opt("ui.state_season_hub.SeasonHubState")
        if SeasonHubState is None:
            return

        # Build a Career for JUST the selected league (20 teams).
        # We remap team IDs to 0..19 for compatibility with schedule/tests.
        league = self._league()
        teams_src = league["teams"]
        # Remap tid → 0..19 and fix player team_id accordingly
        remapped = []
        for i, t in enumerate(teams_src):
            fighters = []
            for j, p in enumerate(t.get("fighters", [])):
                cp = dict(p)
                cp["team_id"] = i
                fighters.append(cp)
            remapped.append({"tid": i, "name": t["name"], "color": t.get("color", (120,120,120)), "fighters": fighters})

        user_tid = self.team_idx if self.team_idx is not None else 0
        if Career is not None:
            # pass correct names so schedule shows proper team names
            names = [t["name"] for t in remapped]
            car = Career.new(seed=self.seed, n_teams=len(remapped), team_size=len(remapped[0]["fighters"]), user_team_id=user_tid, team_names=names)
            # overwrite generated fighters with our world rosters
            for i, t in enumerate(remapped):
                car.teams[i]["fighters"] = t["fighters"]
                car.teams[i]["name"] = t["name"]
        else:
            # tiny fallback
            car = type("MiniCareer", (), {})()
            car.teams = remapped
            car.week = 1; car.user_tid = user_tid
            def _tn(tid):
                for t in car.teams:
                    if int(t.get("tid", -1)) == int(tid): return t.get("name", f"Team {tid}")
                return f"Team {tid}"
            car.team_name = _tn
            car.fixtures_by_week = [[{"week": 1, "home_id": 0, "away_id": 1, "played": False, "k_home": 0, "k_away": 0}]]
            car.fixtures = list(car.fixtures_by_week[0])

        self.app.career = car
        try:
            st = SeasonHubState(self.app, career=car)
        except TypeError:
            st = SeasonHubState(self.app)
        self.app.push_state(st)

    # ------------- Event handling -------------
    def handle(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self._back(); return

        # scroll
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.rect_league and self.rect_league.collidepoint(mx, my):
                self.scroll_teams = max(min(self.scroll_teams - event.y*24, 0), -500)
            elif self.rect_roster and self.rect_roster.collidepoint(mx, my):
                self.scroll_players = max(min(self.scroll_players - event.y*24, 0), -500)

        # buttons
        for b in self.btns:
            b.handle(event)

        if self.toggle_top: self.toggle_top.handle(event)
        if self.toggle_bottom: self.toggle_bottom.handle(event)

        # clicks in lists
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            x, y = event.pos

            # countries list
            if self.rect_countries and self.rect_countries.collidepoint(x, y):
                inner = self.rect_countries.inflate(-16, -58)  # leave room for header
                y0 = inner.y
                row_h = 36
                idx = (y - y0) // row_h
                if 0 <= idx < len(self._countries()):
                    self._select_country(int(idx))
                return

            # team list
            if self.rect_league and self.rect_league.collidepoint(x, y):
                # list area below toggle
                list_area = self.rect_league.inflate(-16, -74)
                list_area.y = self.rect_league.y + 60
                row_h = 34
                y_scroll = y - (list_area.y + self.scroll_teams)
                idx = int(y_scroll // row_h)
                if 0 <= idx < len(self._teams()):
                    self._select_team(idx)
                return

            # player list
            if self.rect_roster and self.rect_roster.collidepoint(x, y):
                list_area = self.rect_roster.inflate(-16, -54)
                row_h = 28
                y_scroll = y - (list_area.y + self.scroll_players)
                t = self._selected_team()
                n = len(t.get("fighters", [])) if t else 0
                idx = int(y_scroll // row_h)
                if 0 <= idx < n:
                    self._select_player(idx)
                return

    # ------------- Update / Draw -------------
    def update(self, dt: float): pass

    def draw(self, screen: pygame.Surface):
        w, h = screen.get_size()
        screen.fill((16, 16, 20))

        # Titles
        title = self.h1.render("Choose Your Team", True, (235, 235, 240))
        screen.blit(title, (16, 20))

        # Countries panel
        self._draw_panel(screen, self.rect_countries, "Countries")
        self._draw_countries(screen)

        # League panel (middle)
        self._draw_panel(screen, self.rect_league, f"{self._country()['name']} League")
        self._draw_league_toggle(screen)
        self._draw_team_list(screen)

        # Detail panel (right)
        self._draw_panel(screen, self.rect_detail, "Roster & Player")
        self._draw_roster(screen)
        self._draw_player_stats(screen)

        # Buttons
        # Disable Start until a team is selected
        for b in self.btns:
            if b.text.startswith("Start"):
                b.disabled = (self.team_idx is None)
            b.draw(screen, self.font)

    # ------ draw helpers ------
    def _draw_panel(self, screen: pygame.Surface, rect: Optional[pygame.Rect], title: str):
        if not rect: return
        pygame.draw.rect(screen, (42, 44, 52), rect, border_radius=12)
        pygame.draw.rect(screen, (24, 24, 28), rect, 2, border_radius=12)
        t = self.h2.render(title, True, (215, 215, 220))
        screen.blit(t, (rect.x + 12, rect.y + 10))

    def _draw_countries(self, screen: pygame.Surface):
        rect = self.rect_countries; 
        if not rect: return
        inner = rect.inflate(-16, -58); inner.y = rect.y + 48
        row_h = 36
        for i, c in enumerate(self._countries()):
            r = pygame.Rect(inner.x, inner.y + i*row_h, inner.w, row_h - 6)
            selected = (i == self.country_idx)
            Button(r, c["name"], lambda: None).draw(screen, self.font, selected=selected)

    def _draw_league_toggle(self, screen: pygame.Surface):
        # buttons already positioned in layout
        if self.toggle_top:
            self.toggle_top.draw(screen, self.font, selected=(self.league_level == 1))
        if self.toggle_bottom:
            self.toggle_bottom.draw(screen, self.font, selected=(self.league_level == 2))

    def _draw_team_list(self, screen: pygame.Surface):
        rect = self.rect_league
        if not rect: return
        list_area = rect.inflate(-16, -74)
        list_area.y = rect.y + 60
        row_h = 34
        teams = self._teams()

        # clip
        prev = screen.get_clip()
        screen.set_clip(list_area)

        y = list_area.y + self.scroll_teams
        for i, t in enumerate(teams):
            r = pygame.Rect(list_area.x, y + i*row_h, list_area.w, row_h - 6)
            selected = (self.team_idx == i)
            label = t["name"]
            Button(r, label, lambda: None).draw(screen, self.font, selected=selected)

        screen.set_clip(prev)

    def _draw_roster(self, screen: pygame.Surface):
        rect = self.rect_roster
        if not rect: return
        # header
        head = self.h2.render("Players", True, (210, 210, 215))
        screen.blit(head, (rect.x + 12, rect.y + 8))

        list_area = rect.inflate(-16, -54)
        list_area.y = rect.y + 36
        row_h = 28

        team = self._selected_team()
        fighters = team.get("fighters", []) if team else []

        prev = screen.get_clip()
        screen.set_clip(list_area)

        y0 = list_area.y + self.scroll_players
        for i, p in enumerate(fighters):
            r = pygame.Rect(list_area.x, y0 + i*row_h, list_area.w, row_h - 4)
            selected = (self.player_idx == i)
            label = f"{p.get('name','P'):<5}  OVR {p.get('OVR', _ovr(p))}"
            Button(r, label, lambda: None).draw(screen, self.font, selected=selected)

        screen.set_clip(prev)

    def _draw_player_stats(self, screen: pygame.Surface):
        rect = self.rect_stats
        if not rect: return
        head = self.h2.render("Player", True, (210, 210, 215))
        screen.blit(head, (rect.x + 12, rect.y + 8))

        p = self._selected_player()
        if not p:
            txt = self.font.render("Select a player to see stats.", True, (190, 190, 195))
            screen.blit(txt, (rect.x + 12, rect.y + 40))
            return

        # Basic grid
        y = rect.y + 36
        line = lambda k, v: screen.blit(self.font.render(f"{k}: {v}", True, (220, 220, 225)), (rect.x + 12, vline()))
        def vline():
            nonlocal y
            py = y
            y += 24
            return py

        ovr = p.get("OVR", _ovr(p))
        screen.blit(self.font.render(f"Name: {p.get('name')}", True, (220,220,225)), (rect.x + 12, vline()))
        screen.blit(self.font.render(f"OVR: {ovr}", True, (220,220,225)), (rect.x + 12, vline()))
        screen.blit(self.font.render(f"HP: {p.get('hp')}/{p.get('max_hp')}", True, (220,220,225)), (rect.x + 12, vline()))
        y += 6
        for k in ("STR","DEX","CON","INT","WIS","CHA"):
            screen.blit(self.font.render(f"{k}: {p.get(k)}", True, (220,220,225)), (rect.x + 12, vline()))
