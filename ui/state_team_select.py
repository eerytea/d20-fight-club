# ui/state_team_select.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from typing import Callable, List, Optional, Dict, Any, Tuple
import random
import traceback

# Optional imports (won't crash if missing)
try:
    from core.career import Career  # type: ignore
except Exception:
    Career = None  # type: ignore

try:
    from core.creator import generate_fighter  # type: ignore
except Exception:
    generate_fighter = None  # type: ignore

# ---- UI bits ----
@dataclass
class Button:
    rect: pygame.Rect
    text: str
    action: Callable[[], None]
    hover: bool = False
    disabled: bool = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, selected: bool=False):
        bg = (58, 60, 70) if not self.hover else (76, 78, 90)
        if selected: bg = (88, 92, 110)
        if self.disabled: bg = (48, 48, 54)
        pygame.draw.rect(surface, bg, self.rect, border_radius=8)
        pygame.draw.rect(surface, (24, 24, 28), self.rect, 2, border_radius=8)
        color = (230, 230, 235) if not self.disabled else (150, 150, 155)
        txt = font.render(self.text, True, color)
        surface.blit(txt, (self.rect.x + 14, self.rect.y + (self.rect.h - txt.get_height()) // 2))

    def handle(self, event: pygame.event.Event):
        if self.disabled: return
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.action()

# ---- World names/colors ----
_COUNTRIES = ["Albion","Valoria","Karthos","Eldoria","Norska","Zafira","Solheim","Drakken"]
_TEAM_WORDS_A = ["Iron","Golden","Crimson","Emerald","Shadow","Storm","Royal","Wild"]
_TEAM_WORDS_B = ["Wolves","Falcons","Titans","Knights","Serpents","Guard","Ravens","Bullheads"]
def _rand_name(rng: random.Random) -> str: return f"{rng.choice(_TEAM_WORDS_A)} {rng.choice(_TEAM_WORDS_B)}"
def _rand_color(rng: random.Random) -> Tuple[int,int,int]: return (rng.randint(60,220), rng.randint(60,220), rng.randint(60,220))
def _ovr(p: Dict[str,Any]) -> int: return int(p.get("OVR", p.get("ovr", p.get("OVR_RATING", 60))))

# Fallback content (used only if generator import/call fails)
_FALLBACK_RACES = [
    "Human","Dwarf","Goblin","Orc","High Elf","Sea Elf","Dark Elf","Wood Elf",
    "Golem","Dark Dwarf","Dark Gnome","Gnome","Birdkin","Lizardkin","Catkin","Bullkin",
]
_STD_ARRAY = [15,14,13,12,10,8]
_ABILITY_KEYS = ["STR","DEX","CON","INT","WIS","CHA"]
_ALL_CLASSES = ["fighter","barbarian","ranger","rogue","wizard","sorcerer","paladin","bard","cleric","druid","monk","warlock"]

def _fallback_name(r: random.Random) -> str:
    first = ["Kael","Ryn","Mira","Thorn","Lysa","Doran","Nyra","Kellan","Sera","Jorin",
             "Talia","Bren","Arin","Sel","Vara","Garrin","Orin","Kira","Fen","Zara"]
    last  = ["Stone","Vale","Rook","Ash","Hollow","Black","Bright","Gale","Wolfe","Mire",
             "Thorne","Ridge","Hawk","Frost","Dusk","Iron","Raven","Drake","Storm","Oath"]
    return f"{r.choice(first)} {r.choice(last)}"

def _pick_class_from_abilities(abilities: Dict[str,int], r: random.Random) -> str:
    # Choose a class group based on top ability; random within group for variety.
    items = sorted(abilities.items(), key=lambda kv: kv[1], reverse=True)
    top = items[0][0] if items else "STR"
    top = top.upper()
    if top == "STR":
        return r.choice(["fighter","barbarian","paladin"])
    if top == "DEX":
        return r.choice(["rogue","ranger","monk"])
    if top == "INT":
        return r.choice(["wizard","warlock"])
    if top == "WIS":
        return r.choice(["cleric","druid","ranger"])
    if top == "CHA":
        return r.choice(["bard","sorcerer","paladin","warlock"])
    # CON or fallback:
    return r.choice(_ALL_CLASSES)

def _fallback_fighter(team_tid: int, idx: int, country: str, r: random.Random) -> Dict[str,Any]:
    # Abilities from standard array
    vals = _STD_ARRAY[:]; r.shuffle(vals)
    keys = _ABILITY_KEYS[:]; r.shuffle(keys)
    abilities = dict(zip(keys, vals))
    # Race variety
    race = r.choice(_FALLBACK_RACES)
    # Class from abilities (instead of always 'fighter')
    klass = _pick_class_from_abilities(abilities, r)
    # AC = 10 + floor((DEX-10)/2) + armor_bonus
    dex = abilities.get("DEX", 10)
    ac = 10 + (dex - 10)//2 + 0
    hp = 10 + (abilities.get("CON",10)-10)//2
    # Age 18-38
    age = r.randint(18, 38)
    return {
        "pid": idx,                  # internal id
        "age": age,
        "name": _fallback_name(r),
        "race": race,
        "origin": country,
        "class": klass,
        "level": 1,
        "hp": hp, "max_hp": hp, "ac": ac, "alive": True,
        "armor_bonus": 0,
        **abilities,
        # lowercase mirrors
        "str": abilities.get("STR",10), "dex": abilities.get("DEX",10), "con": abilities.get("CON",10),
        "int": abilities.get("INT",10), "wis": abilities.get("WIS",10), "cha": abilities.get("CHA",10),
        "OVR": 60 + r.randint(-5, 10),
        "potential": 65 + r.randint(0, 25),
        "weapon": {"name": "Sword"},
        "team_id": team_tid,
    }

def _pretty(text: Any) -> str:
    return str(text).replace("_", " ").title()

class TeamSelectState:
    """
    3 columns: Countries | League (Top/Bottom) + Teams | Roster (top) + Player (bottom)
    Regenerate button (top-right) rerolls players for every team in all countries/leagues.
    """
    def __init__(self, app):
        self.app = app
        self.font  = pygame.font.SysFont(None, 22)
        self.h1    = pygame.font.SysFont(None, 34)
        self.h2    = pygame.font.SysFont(None, 20)
        self.small = self.font

        self.rect_countries: Optional[pygame.Rect] = None
        self.rect_league: Optional[pygame.Rect] = None
        self.rect_detail: Optional[pygame.Rect] = None
        self.rect_roster: Optional[pygame.Rect] = None
        self.rect_stats: Optional[pygame.Rect] = None

        self.seed = getattr(self.app, "world_seed", 7777)
        self.world = self._build_world(self.seed)

        self.country_idx = getattr(self.app, "last_country_idx", 0)
        self.league_level = getattr(self.app, "last_league_level", 1)  # 1 or 2
        self.team_idx: Optional[int] = 0
        self.player_idx: Optional[int] = 0

        self.scroll_teams   = 0
        self.scroll_players = 0
        self.scroll_stats   = 0
        self.stats_content_h = 0

        # Buttons
        self.btns: List[Button] = []
        self.toggle_top: Optional[Button] = None
        self.toggle_bottom: Optional[Button] = None
        self.btn_start: Optional[Button] = None
        self.btn_regen: Optional[Button] = None

    # ---- world build ----
    def _build_world(self, seed: int) -> Dict[str, Any]:
        rng = random.Random(seed)
        world = {"countries": []}
        for cname in _COUNTRIES:
            leagues = [self._make_league(cname, 1, rng), self._make_league(cname, 2, rng)]
            world["countries"].append({"name": cname, "leagues": leagues})
        return world

    def _make_league(self, country: str, level: int, rng: random.Random, team_size: int = 12) -> Dict[str, Any]:
        name = f"{country} {'Premier' if level == 1 else 'Division'}"
        teams = []
        for i in range(20):
            tname = f"{country} {_rand_name(rng)}"
            color = _rand_color(rng)
            fighters = [self._mk_fighter(i, j, country, rng) for j in range(team_size)]
            teams.append({"tid": i, "name": tname, "color": color, "fighters": fighters})
        return {"name": name, "teams": teams}

    def _mk_fighter(self, team_tid: int, idx: int, country: str, rng: random.Random) -> Dict[str, Any]:
        # Try generator (old signature)
        if generate_fighter is not None:
            try:
                f = generate_fighter(level=1, rng=rng, town=country, neg_trait_prob=0.15)  # old API
                f["team_id"] = team_tid; f["pid"] = idx
                f["max_hp"] = f.get("max_hp", f.get("hp", 10)); f["alive"] = True
                f.setdefault("origin", country)
                f.pop("num", None)  # drop jersey number if provided
                if "age" not in f:
                    f["age"] = rng.randint(18, 38)
                # ensure class exists
                f.setdefault("class", _pick_class_from_abilities(
                    {k: f.get(k, f.get(k.lower(), 10)) for k in _ABILITY_KEYS}, rng))
                return f
            except TypeError:
                # Try newer API
                try:
                    f = generate_fighter(team={"tid": team_tid}, seed=rng.randint(0, 10_000_000))  # new API
                    f["team_id"] = team_tid; f["pid"] = idx
                    f["max_hp"] = f.get("max_hp", f.get("hp", 10)); f["alive"] = True
                    f.setdefault("origin", country)
                    f.pop("num", None)
                    if "age" not in f:
                        f["age"] = rng.randint(18, 38)
                    f.setdefault("class", _pick_class_from_abilities(
                        {k: f.get(k, f.get(k.lower(), 10)) for k in _ABILITY_KEYS}, rng))
                    return f
                except Exception:
                    traceback.print_exc()
            except Exception:
                traceback.print_exc()
        # Fallback
        return _fallback_fighter(team_tid, idx, country, rng)

    # ---- life-cycle ----
    def enter(self):
        w, h = self.app.screen.get_size()
        pad = 16
        left_w = max(220, int(w * 0.22))
        mid_w  = max(380, int(w * 0.34))
        right_w = w - (left_w + mid_w + pad*4)

        self.rect_countries = pygame.Rect(pad, 70, left_w, h - 70 - pad)
        self.rect_league    = pygame.Rect(self.rect_countries.right + pad, 70, mid_w, h - 70 - pad)
        self.rect_detail    = pygame.Rect(self.rect_league.right + pad, 70, right_w, h - 70 - pad)

        # right column split
        self.rect_roster = pygame.Rect(self.rect_detail.x, self.rect_detail.y, self.rect_detail.w, int(self.rect_detail.h * 0.55))
        self.rect_stats  = pygame.Rect(self.rect_detail.x, self.rect_roster.bottom + pad, self.rect_detail.w, self.rect_detail.bottom - (self.rect_roster.bottom + pad))

        # toggles top/bottom
        tb_w, tb_h = 120, 32
        self.toggle_top    = Button(pygame.Rect(self.rect_league.x, self.rect_league.y - tb_h - 6, tb_w, tb_h), "Top League", self._set_level_top)
        self.toggle_bottom = Button(pygame.Rect(self.rect_league.x + tb_w + 8, self.rect_league.y - tb_h - 6, tb_w, tb_h), "Bottom League", self._set_level_bottom)

        # top-right buttons: Start (far right) and Regenerate (left of it)
        btn_w, btn_h, gap = 140, 40, 10
        start_x = w - btn_w - 16
        regen_x = start_x - btn_w - gap
        self.btn_start = Button(pygame.Rect(start_x, 16, btn_w, btn_h), "Start", self._start)
        self.btn_regen = Button(pygame.Rect(regen_x, 16, btn_w, btn_h), "Regenerate", self._regen_all_fighters)

        self.btns = [self.toggle_top, self.toggle_bottom, self.btn_regen, self.btn_start]

    def _set_level_top(self): self.league_level = 1; self.scroll_teams = self.scroll_players = self.scroll_stats = 0
    def _set_level_bottom(self): self.league_level = 2; self.scroll_teams = self.scroll_players = self.scroll_stats = 0

    # ---- helpers ----
    def _countries(self) -> List[Dict[str, Any]]: return self.world["countries"]
    def _country(self) -> Dict[str, Any]: return self._countries()[self.country_idx or 0]
    def _league(self) -> Dict[str, Any]: return self._country()["leagues"][0 if self.league_level==1 else 1]
    def _teams(self) -> List[Dict[str, Any]]: return self._league()["teams"]

    def _team_row_h(self) -> int:
        """Height of a team tile in the mid column (two text lines)."""
        return 48

    def _team_avgs(self, t: Dict[str, Any]) -> Tuple[int, int]:
        """Average OVR and POT for a team; robust to key variants."""
        fighters = t.get("fighters", []) or []
        if not fighters: return (0, 0)
        s_ovr, s_pot, n = 0, 0, 0
        for p in fighters:
            try:
                o = p.get("OVR", p.get("ovr", p.get("OVR_RATING", 0)))
                po = p.get("potential", p.get("pot", 0))
                o = int(float(o)) if o is not None else 0
                po = int(float(po)) if po is not None else 0
            except Exception:
                o, po = 0, 0
            s_ovr += o; s_pot += po; n += 1
        if n == 0: return (0, 0)
        return (round(s_ovr / n), round(s_pot / n))

    def _selected_team(self) -> Optional[Dict[str, Any]]:
        idx = self.team_idx if self.team_idx is not None else 0
        ts = self._teams()
        if not ts: return None
        if idx < 0 or idx >= len(ts): idx = 0
        return ts[idx]

    def _selected_player(self) -> Optional[Dict[str, Any]]:
        t = self._selected_team()
        if not t: return None
        plist = t.get("fighters", [])
        if not plist: return None
        i = max(0, min(self.player_idx or 0, len(plist)-1))
        return plist[i]

    # --- display helpers ---
    def _display_name(self, p: dict) -> str:
        n = p.get("name") or p.get("Name") or p.get("full_name") or p.get("fullName")
        if n: return str(n)
        first = p.get("first_name") or p.get("firstName") or p.get("first")
        last  = p.get("last_name")  or p.get("lastName")  or p.get("last")
        combo = f"{first or ''} {last or ''}".strip()
        return combo or "Player"

    def _pretty_race(self, r) -> str:
        if not r: return "-"
        return str(r).replace("_", " ").title()

    # ---- events ----
    def handle(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self._back(); return
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._start(); return

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            step = 24
            if self.rect_league and self.rect_league.collidepoint(mx, my):
                inner = self.rect_league.inflate(-16, -74); inner.y = self.rect_league.y + 60
                row_h = self._team_row_h()
                self.scroll_teams = self._clamp_scroll(self.scroll_teams, event.y*step, len(self._teams()), row_h, inner)
            elif self.rect_roster and self.rect_roster.collidepoint(mx, my):
                list_area = self.rect_roster.inflate(-16, -54); list_area.y = self.rect_roster.y + 36
                team = self._selected_team()
                n = len(team.get("fighters", [])) if team else 0
                self.scroll_players = self._clamp_scroll(self.scroll_players, event.y*step, n, 28, list_area)
            elif self.rect_stats and self.rect_stats.collidepoint(mx, my):
                content_h = max(self.stats_content_h, self.rect_stats.h)
                self.scroll_stats = self._clamp_scroll_px(self.scroll_stats, event.y*step, content_h, self.rect_stats)

        for b in self.btns:
            b.handle(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # country selection
            if self.rect_countries and self.rect_countries.collidepoint(mx, my):
                inner = self.rect_countries.inflate(-16, -58); inner.y = self.rect_countries.y + 48
                row_h = 36
                idx = (my - inner.y) // row_h
                if 0 <= idx < len(self._countries()):
                    self._select_country(int(idx))
            # team selection
            if self.rect_league and self.rect_league.collidepoint(mx, my):
                inner = self.rect_league.inflate(-16, -74); inner.y = self.rect_league.y + 60
                row_h = self._team_row_h()
                idx = (my - inner.y - self.scroll_teams) // row_h
                if 0 <= idx < len(self._teams()):
                    self._select_team(int(idx))
            # player selection
            if self.rect_roster and self.rect_roster.collidepoint(mx, my):
                list_area = self.rect_roster.inflate(-16, -54); list_area.y = self.rect_roster.y + 36
                row_h = 28
                idx = (my - list_area.y - self.scroll_players) // row_h
                team = self._selected_team()
                plist = team.get("fighters", []) if team else []
                if 0 <= idx < len(plist):
                    self._select_player(int(idx))

    def update(self, dt: float):
        pass

    # ---- draw ----
    def draw(self, screen: pygame.Surface):
        w, h = screen.get_size()
        screen.fill((16,16,20))
        title = self.h1.render("Choose Your Team", True, (235,235,240))
        screen.blit(title, (16, 20))

        self._draw_panel(screen, self.rect_countries, "Countries"); self._draw_countries(screen)
        self._draw_panel(screen, self.rect_league, f"{self._country().get('name','')} • {'Top' if self.league_level==1 else 'Division'}"); self._draw_league_toggle(screen); self._draw_team_list(screen)
        self._draw_panel(screen, self.rect_detail, ""); self._draw_roster(screen)

        if self.rect_roster:
            pygame.draw.line(screen, (28,28,32), (self.rect_roster.x, self.rect_roster.bottom), (self.rect_roster.right-8, self.rect_roster.bottom), 2)

        self._draw_player_stats(screen)

        # buttons (update Start enabled state)
        if self.btn_start:
            self.btn_start.disabled = (self.team_idx is None)
        for b in self.btns:
            if b not in (self.toggle_top, self.toggle_bottom):
                b.draw(screen, self.font)
        if self.toggle_top: self.toggle_top.draw(screen, self.font, selected=(self.league_level==1))
        if self.toggle_bottom: self.toggle_bottom.draw(screen, self.font, selected=(self.league_level==2))

    # ---- draw helpers ----
    def _draw_panel(self, screen: pygame.Surface, rect: Optional[pygame.Rect], title: str):
        if not rect: return
        pygame.draw.rect(screen, (42,44,52), rect, border_radius=12)
        pygame.draw.rect(screen, (24,24,28), rect, 2, border_radius=12)
        if title:
            t = self.h2.render(title, True, (215,215,220)); screen.blit(t, (rect.x+12, rect.y+10))

    def _draw_scrollbar(self, screen: pygame.Surface, area: pygame.Rect, content_h: int, scroll_px: int):
        if content_h <= area.h: return
        track = pygame.Rect(area.right - 6, area.y, 4, area.h)
        pygame.draw.rect(screen, (30,30,35), track, border_radius=2)
        denom = max(1, content_h - area.h)
        ratio = min(1.0, max(0.0, -scroll_px / denom))
        thumb_h = max(18, int(area.h * area.h / content_h))
        thumb_y = area.y + int((area.h - thumb_h) * ratio)
        thumb = pygame.Rect(track.x, thumb_y, track.w, thumb_h)
        pygame.draw.rect(screen, (120,120,130), thumb, border_radius=2)

    def _draw_countries(self, screen: pygame.Surface):
        rect = self.rect_countries
        if not rect: return
        inner = rect.inflate(-16, -58); inner.y = rect.y + 48
        row_h = 36
        for i, c in enumerate(self._countries()):
            r = pygame.Rect(inner.x, inner.y + i*row_h, inner.w, row_h-6)
            Button(r, c["name"], lambda: None).draw(screen, self.font, selected=(i == self.country_idx))

    def _draw_league_toggle(self, screen: pygame.Surface):
        if self.toggle_top:    self.toggle_top.draw(screen, self.font, selected=(self.league_level==1))
        if self.toggle_bottom: self.toggle_bottom.draw(screen, self.font, selected=(self.league_level==2))

    def _draw_team_list(self, screen: pygame.Surface):
        rect = self.rect_league
        if not rect: return
        inner = rect.inflate(-16, -74); inner.y = rect.y + 60
        row_h = self._team_row_h()
        prev = screen.get_clip(); screen.set_clip(inner)

        for i, t in enumerate(self._teams()):
            y = inner.y + i*row_h + self.scroll_teams
            r = pygame.Rect(inner.x, y, inner.w, row_h-6)
            sel = (i == (self.team_idx or 0))
            bg = (58, 60, 70) if not sel else (88, 92, 110)
            pygame.draw.rect(screen, bg, r, border_radius=8)
            pygame.draw.rect(screen, (24, 24, 28), r, 2, border_radius=8)

            # First line: team name
            nm = t.get("name", f"Team {i}")
            name_surf = self.font.render(nm, True, (230,230,235))
            screen.blit(name_surf, (r.x + 10, r.y + 6))

            # Second line: averages
            avg_ovr, avg_pot = self._team_avgs(t)
            sub_txt = f"AVG OVR: {avg_ovr}   •   AVG POT: {avg_pot}"
            sub_surf = self.h2.render(sub_txt, True, (205,205,210))
            screen.blit(sub_surf, (r.x + 10, r.y + 6 + name_surf.get_height() + 2))

        screen.set_clip(prev)
        content_h = len(self._teams()) * row_h
        self._draw_scrollbar(screen, inner, content_h, self.scroll_teams)

    def _draw_roster(self, screen: pygame.Surface):
        rect = self.rect_roster
        if not rect: return
        list_area = rect.inflate(-16, -54); list_area.y = rect.y + 36
        row_h = 28
        team = self._selected_team(); fighters = team.get("fighters", []) if team else []

        prev = screen.get_clip(); screen.set_clip(list_area)
        y0 = list_area.y + self.scroll_players
        for i, p in enumerate(fighters):
            r = pygame.Rect(list_area.x, y0 + i*row_h, list_area.w, row_h-4)
            nm = self._display_name(p)
            ovr = _ovr(p)
            age = int(p.get('age', 18))
            label = f"{nm}   AGE {age}   OVR {ovr}"
            Button(r, label, lambda: None).draw(screen, self.font, selected=(self.player_idx==i))
        screen.set_clip(prev)
        content_h = len(fighters) * row_h
        self._draw_scrollbar(screen, list_area, content_h, self.scroll_players)

    def _draw_player_stats(self, screen: pygame.Surface):
        rect = self.rect_stats
        if not rect: return

        p = self._selected_player()
        if not p:
            self.stats_content_h = 0
            return

        def G(key, default=None): return p.get(key, p.get(key.upper(), default))

        ovr = int(G("ovr", G("OVR", 60)))
        lvl_src = G("level", G("lvl", None))
        level = int(lvl_src) if lvl_src is not None else max(1, ovr // 10)

        name = self._display_name(p)
        race = self._pretty_race(G("race","-"))
        origin = G("origin", self._country().get("name","-"))
        pot = int(G("potential",70))
        cls_raw = G("class","Fighter")
        cls_disp = _pretty(cls_raw)
        hp = int(G("hp",10)); max_hp = int(G("max_hp", hp)); ac = int(G("ac",12))
        STR = int(G("str",G("STR",10))); DEX = int(G("dex",G("DEX",10))); CON = int(G("con",G("CON",10)))
        INT = int(G("int",G("INT",10))); WIS = int(G("wis",G("WIS",10))); CHA = int(G("cha",G("CHA",10)))
        age = int(G("age", 18))

        wpn = G("weapon",{})
        weapon_name = (wpn.get("name") if isinstance(wpn,dict) else (wpn if isinstance(wpn,str) else "-"))
        armor_val = G("armor_name", None) or G("equipped_armor", None) or (G("armor",{}).get("name") if isinstance(G("armor",None),dict) else "-")

        clip = rect.inflate(-12, -16)
        prev = screen.get_clip(); screen.set_clip(clip)

        x0 = rect.x + 12
        y = rect.y + 12 + self.scroll_stats
        line_h = self.font.get_height() + 6

        def line(text: str):
            nonlocal y
            surf = self.font.render(text, True, (220,220,225))
            screen.blit(surf, (x0, y)); y += line_h

        # Compact top lines (AGE replaces jersey number)
        line(f"{name}    AGE: {age}    LVL: {level}")
        line(f"{race}    {origin}    OVR: {ovr}    POT: {pot}")
        line(f"{cls_disp}    HP: {hp}/{max_hp}    AC: {ac}")

        # Attributes grid
        y += 4
        labels = ("STR","DEX","CON","INT","WIS","CHA"); vals = (STR,DEX,CON,INT,WIS,CHA)
        col_w = (rect.w - 24) // 6; top_y = y
        for i, lab in enumerate(labels):
            lx = x0 + i*col_w + col_w//2
            surf = self.font.render(lab, True, (210,210,215))
            screen.blit(surf, (lx - surf.get_width()//2, top_y))
        y = top_y + self.font.get_height() + 4
        for i, v in enumerate(vals):
            lx = x0 + i*col_w + col_w//2
            surf = self.font.render(str(v), True, (235,235,240))
            screen.blit(surf, (lx - surf.get_width()//2, y))
        y += self.font.get_height() + 10

        line(f"Armor: {armor_val}    Weapon: {weapon_name}")

        self.stats_content_h = max(0, (y - (rect.y + 12)))
        screen.set_clip(prev)

    # ---- selection helpers ----
    def _select_country(self, idx: int):
        self.country_idx = idx
        self.team_idx = 0; self.player_idx = 0
        self.scroll_teams = self.scroll_players = self.scroll_stats = 0

    def _select_team(self, idx: int):
        self.team_idx = idx
        self.player_idx = 0; self.scroll_players = self.scroll_stats = 0

    def _select_player(self, idx: int):
        self.player_idx = idx

    # ---- scroll helpers ----
    def _clamp_scroll(self, current: int, delta: int, n_items: int, row_h: int, view_rect: Optional[pygame.Rect]) -> int:
        if not view_rect: return 0
        content_h = n_items*row_h
        max_neg = min(0, view_rect.h - content_h)
        new_val = current + delta
        if new_val > 0: new_val = 0
        if new_val < max_neg: new_val = max_neg
        return new_val

    def _clamp_scroll_px(self, current: int, delta: int, content_h: int, view_rect: Optional[pygame.Rect]) -> int:
        if not view_rect: return 0
        if content_h <= 0: return 0
        max_neg = min(0, view_rect.h - content_h)
        new_val = current + delta
        if new_val > 0: new_val = 0
        if new_val < max_neg: new_val = max_neg
        return new_val

    # ---- actions ----
    def _back(self):
        self.app.pop_state()

    def _start(self):
        SeasonHubState = _import_opt("ui.state_season_hub.SeasonHubState")
        if SeasonHubState is None: return

        league = self._league()
        remapped = []
        for i, t in enumerate(league["teams"]):
            fighters = []
            for p in t.get("fighters", []):
                cp = dict(p); cp["team_id"] = i; fighters.append(cp)
            remapped.append({"tid": i, "name": t["name"], "color": t.get("color",(120,120,120)), "fighters": fighters})

        user_tid = int(self.team_idx if self.team_idx is not None else 0)

        if Career is not None:
            # Call Career.new without unsupported kwargs (e.g., 'names')
            try:
                car = Career.new(seed=self.seed,
                                 n_teams=len(remapped),
                                 team_size=(len(remapped[0]["fighters"]) if remapped else 12),
                                 fighters=remapped,
                                 user_tid=user_tid)
            except TypeError:
                # Fallback: try positional common order
                try:
                    car = Career.new(self.seed, len(remapped),
                                     len(remapped[0]["fighters"]) if remapped else 12,
                                     remapped, user_tid)
                except Exception:
                    traceback.print_exc()
                    return
        else:
            car = type("MiniCareer", (), {})()
            car.teams = remapped; car.week = 1; car.user_tid = user_tid; car.seed = self.seed
            def _tn(tid):
                for t in remapped:
                    if int(t.get("tid",-1)) == int(tid): return t.get("name", f"Team {tid}")
                return f"Team {tid}"
            car.team_name = _tn

        self.app.push_state(SeasonHubState(self.app, car))

    def _regen_all_fighters(self):
        r = random.Random()
        for c in self.world.get("countries", []):
            country = c.get("name", "Unknown")
            for league in c.get("leagues", []):
                for t in league.get("teams", []):
                    tid = int(t.get("tid", 0))
                    size = len(t.get("fighters", [])) or 12
                    new_list = []
                    for j in range(size):
                        try:
                            p = self._mk_fighter(tid, j, country, r)
                        except Exception:
                            traceback.print_exc()
                            p = _fallback_fighter(tid, j, country, r)
                        new_list.append(p)
                    t["fighters"] = new_list
        self.player_idx = 0; self.scroll_players = self.scroll_stats = 0

def _import_opt(fullname: str):
    try:
        module_name, class_name = fullname.rsplit(".", 1)
        mod = __import__(module_name, fromlist=[class_name])
        return getattr(mod, class_name)
    except Exception:
        return None

# Back-compat exports
TeamSelect = TeamSelectState
__all__ = ["TeamSelectState", "TeamSelect"]
