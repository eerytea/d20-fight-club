# ui/state_team_select.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from typing import Callable, List, Optional, Dict, Any, Tuple
import random

# Prefer your real generator. If it fails, we will use a solid internal fallback.
try:
    from core.creator import generate_fighter as _real_generate_fighter
except Exception:
    _real_generate_fighter = None  # type: ignore

try:
    from core.ratings import compute_ovr as _compute_ovr  # optional (for fallback only)
except Exception:
    _compute_ovr = None  # type: ignore

def _import_opt(fullname: str):
    try:
        module_name, class_name = fullname.rsplit(".", 1)
        mod = __import__(module_name, fromlist=[class_name])
        return getattr(mod, class_name)
    except Exception:
        return None

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

# ---- internal fallback generator (only used if the real one fails) ----
_STD_ARRAY = [15,14,13,12,10,8]
_RACE_FALLBACK = [
    "Human","Dwarf","Elf","Orc","Halfling","Gnome","Tiefling","Half-Elf"
]
_FIRST = ["Kael","Ryn","Mira","Thorn","Lysa","Doran","Nyra","Kellan","Sera","Jorin",
          "Talia","Bren","Arin","Sel","Vara","Garrin","Orin","Kira","Fen","Zara"]
_LAST  = ["Stone","Vale","Rook","Ash","Hollow","Black","Bright","Gale","Wolfe","Mire",
          "Thorne","Ridge","Hawk","Frost","Dusk","Iron","Raven","Drake","Storm","Oath"]

def _fallback_generate_fighter(team_tid: int, jersey: int, country: str, rng: random.Random) -> Dict[str, Any]:
    # Standard array → random assignment
    vals = _STD_ARRAY[:]; rng.shuffle(vals)
    keys = ["STR","DEX","CON","INT","WIS","CHA"]; rng.shuffle(keys)
    base = {k: v for k, v in zip(keys, vals)}

    race = rng.choice(_RACE_FALLBACK)
    name = f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"

    # Simple vitals
    dex_mod = (base.get("DEX",10)-10)//2
    con_mod = (base.get("CON",10)-10)//2
    hp = 10 + con_mod
    ac = 10 + dex_mod  # armor_bonus=0 for now

    # Build lowercase mirrors for OVR calc if available
    lower = {k.lower(): v for k,v in base.items()}
    f = {
        "pid": jersey-1,
        "num": jersey,
        "team_id": team_tid,
        "origin": country,
        "name": name,
        "race": race,
        "class": "Fighter",
        "level": 1,
        "hp": hp, "max_hp": hp, "ac": ac,
        **base,
        **lower,
        "alive": True,
        "weapon": {"name": "Longsword", "damage": "1d8"},
        "armor_bonus": 0,
    }
    # Try to compute a decent OVR; otherwise a stable heuristic
    if _compute_ovr:
        try:
            f["OVR"] = int(_compute_ovr(f))
        except Exception:
            f["OVR"] = 60 + (base["STR"]+base["DEX"]+base["CON"]-30)//2
    else:
        f["OVR"] = 60 + (base["STR"]+base["DEX"]+base["CON"]-30)//2
    f.setdefault("potential", int(f["OVR"] + rng.randint(5, 20)))
    return f

class TeamSelectState:
    """
    3 columns: Countries | League (Top/Bottom) + Teams | Roster (top) + Player (bottom)
    Regenerate rerolls players for every team in all countries/leagues.
    """
    def __init__(self, app):
        self.app = app
        # fonts (unify player-box to one size)
        self.font  = pygame.font.SysFont(None, 22)
        self.h1    = pygame.font.SysFont(None, 34)
        self.h2    = pygame.font.SysFont(None, 20)  # used for small panel titles only
        self.small = self.font                       # player stats use only self.font

        self.rect_countries: Optional[pygame.Rect] = None
        self.rect_league: Optional[pygame.Rect] = None
        self.rect_detail: Optional[pygame.Rect] = None
        self.rect_roster: Optional[pygame.Rect] = None
        self.rect_stats: Optional[pygame.Rect] = None

        self.level = 0  # 0=Top, 1=Bottom divisions
        self.country_idx: Optional[int] = 0
        self.team_idx: Optional[int] = 0
        self.player_idx: int = 0

        self.scroll_teams   = 0
        self.scroll_players = 0
        self.scroll_stats   = 0
        self.stats_content_h = 0  # calculated during draw

        self.btns: List[Button] = []
        self.toggle_top: Optional[Button] = None
        self.toggle_bottom: Optional[Button] = None

        # world
        self.seed = 1337
        self.world = self._build_world(self.seed)

    # ---- world build ----
    def _try_real_generator(self, rng: random.Random, country: str) -> Optional[Dict[str, Any]]:
        if _real_generate_fighter is None:
            return None
        try:
            # Signature that matches your repo creator.py
            return _real_generate_fighter(level=1, rng=rng, town=country, neg_trait_prob=0.15)
        except Exception as e:
            # If the signature changed, fall back safely.
            try:
                return _real_generate_fighter()
            except Exception:
                return None

    def _build_world(self, seed: int) -> Dict[str, Any]:
        rng = random.Random(seed)
        world = {"countries": []}
        for cname in _COUNTRIES:
            leagues = []
            for li, lname in enumerate(["Top Division", "Second Division"]):
                teams = []
                for i in range(20):
                    tid = i
                    color = _rand_color(rng)
                    name = _rand_name(rng)
                    team_stub: Dict[str, Any] = {"tid": tid, "name": name, "color": color}
                    fighters: List[Dict[str, Any]] = []
                    for j in range(12):
                        f = self._try_real_generator(rng, cname)
                        if isinstance(f, dict):
                            f["team_id"] = tid
                            f["pid"] = (j % 99)
                            f["num"] = (j % 99) + 1
                            f.setdefault("origin", cname)
                            f.setdefault("name", f"{cname[:1]}{tid}-{j:02d}")  # belt-and-suspenders
                        else:
                            f = _fallback_generate_fighter(tid, (j % 99) + 1, cname, rng)
                        fighters.append(f)
                    team_stub["fighters"] = fighters
                    teams.append(team_stub)
                leagues.append({"name": lname if li==0 else 'Division', "teams": teams})
            world["countries"].append({"name": cname, "leagues": leagues})
        return world

    # ---- life-cycle ----
    def enter(self):
        w, h = self.app.screen.get_size()
        pad = 12
        col_w = (w - 2*pad) // 3
        col_h = h - 2*pad - 76

        self.rect_countries = pygame.Rect(pad, 76 + pad, col_w - pad, col_h)
        self.rect_league    = pygame.Rect(pad + col_w, 76 + pad, col_w - pad, col_h)
        self.rect_detail    = pygame.Rect(pad + 2*col_w, 76 + pad, col_w - pad, col_h)

        # detail splits
        dpad = 10
        self.rect_roster    = pygame.Rect(self.rect_detail.x + dpad, self.rect_detail.y + dpad,
                                          self.rect_detail.w - 2*dpad, max(160, (self.rect_detail.h - 3*dpad)//2))
        self.rect_stats     = pygame.Rect(self.rect_detail.x + dpad, self.rect_roster.bottom + dpad,
                                          self.rect_detail.w - 2*dpad, self.rect_detail.bottom - dpad - (self.rect_roster.bottom + dpad))

        # toggles top/bottom
        tb_w, tb_h = 120, 32
        self.toggle_top    = Button(pygame.Rect(self.rect_league.x, self.rect_league.y - tb_h - 6, tb_w, tb_h), "Top League", self._set_level_top)
        self.toggle_bottom = Button(pygame.Rect(self.rect_league.x + tb_w + 8, self.rect_league.y - tb_h - 6, tb_w, tb_h), "Bottom League", self._set_level_bottom)
        self.btns = [self.toggle_top, self.toggle_bottom]

        # regenerate button
        self.btns.append(Button(pygame.Rect(w - 160 - 16, 16, 160, 40), "Regenerate", self._regen_all_fighters))

    def _set_level_top(self): self.level = 0; self.scroll_teams = self.scroll_players = self.scroll_stats = 0
    def _set_level_bottom(self): self.level = 1; self.scroll_teams = self.scroll_players = self.scroll_stats = 0

    # ---- helpers ----
    def _countries(self) -> List[Dict[str, Any]]: return self.world["countries"]
    def _country(self) -> Dict[str, Any]: return self._countries()[self.country_idx or 0]
    def _league(self) -> Dict[str, Any]: return self._country()["leagues"][self.level]
    def _teams(self) -> List[Dict[str, Any]]: return self._league()["teams"]
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
        i = max(0, min(self.player_idx, len(plist)-1))
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
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self._back(); return

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            step = 24
            if self.rect_league and self.rect_league.collidepoint(mx, my):
                area = self.rect_league.inflate(-16, -74); area.y = self.rect_league.y + 60
                self.scroll_teams = self._clamp_scroll(self.scroll_teams, event.y*step, len(self._teams()), 34, area)
            elif self.rect_roster and self.rect_roster.collidepoint(mx, my):
                list_area = self.rect_roster.inflate(-16, -54); list_area.y = self.rect_roster.y + 36
                team = self._selected_team()
                n = len(team.get("fighters", [])) if team else 0
                self.scroll_players = self._clamp_scroll(self.scroll_players, event.y*step, n, 28, list_area)
            elif self.rect_stats and self.rect_stats.collidepoint(mx, my):
                content_h = max(self.stats_content_h, self.rect_stats.h)  # avoid lock before first draw
                self.scroll_stats = self._clamp_scroll_px(self.scroll_stats, event.y*step, content_h, self.rect_stats)

        for b in self.btns:
            b.handle(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # choose country
            if self.rect_countries and self.rect_countries.collidepoint(mx, my):
                inner = self.rect_countries.inflate(-16, -58); inner.y = self.rect_countries.y + 48
                row_h = 36
                idx = (my - inner.y) // row_h
                if 0 <= idx < len(self._countries()):
                    self._select_country(int(idx))
            # choose team
            if self.rect_league and self.rect_league.collidepoint(mx, my):
                inner = self.rect_league.inflate(-16, -74); inner.y = self.rect_league.y + 60
                row_h = 34
                idx = (my - inner.y - self.scroll_teams) // row_h
                if 0 <= idx < len(self._teams()):
                    self._select_team(int(idx))
            # choose player
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
        self._draw_panel(screen, self.rect_league, f"{self._country().get('name','')} • {'Top' if self.level==0 else 'Division'}"); self._draw_league_toggle(screen); self._draw_team_list(screen)
        self._draw_panel(screen, self.rect_detail, ""); self._draw_roster(screen)  # no right-box title

        # divider between roster and stats
        if self.rect_roster:
            pygame.draw.line(screen, (28,28,32), (self.rect_roster.x, self.rect_roster.bottom), (self.rect_roster.right-8, self.rect_roster.bottom), 2)

        self._draw_player_stats(screen)

    # ---- draw helpers ----
    def _draw_panel(self, screen: pygame.Surface, rect: Optional[pygame.Rect], title: str):
        if not rect: return
        pygame.draw.rect(screen, (42,44,52), rect, border_radius=12)
        pygame.draw.rect(screen, (24,24,28), rect, 2, border_radius=12)
        if title:
            t = self.h2.render(title, True, (215,215,220)); screen.blit(t, (rect.x+12, rect.y+10))

    def _draw_scrollbar(self, screen: pygame.Surface, area: pygame.Rect, content_h: int, scroll_px: int):
        """Generic slim scrollbar on the right edge of area."""
        if content_h <= area.h: return
        track = pygame.Rect(area.right - 6, area.y, 4, area.h)
        pygame.draw.rect(screen, (30,30,35), track, border_radius=2)
        # scroll_px is <= 0. Convert to ratio 0..1
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
        if self.toggle_top:    self.toggle_top.draw(screen, self.font, selected=(self.level==0))
        if self.toggle_bottom: self.toggle_bottom.draw(screen, self.font, selected=(self.level==1))

    def _draw_team_list(self, screen: pygame.Surface):
        rect = self.rect_league
        if not rect: return
        inner = rect.inflate(-16, -74); inner.y = rect.y + 60
        row_h = 34
        prev = screen.get_clip(); screen.set_clip(inner)
        for i, t in enumerate(self._teams()):
            y = inner.y + i*row_h + self.scroll_teams
            r = pygame.Rect(inner.x, y, inner.w, row_h-6)
            sel = (i == (self.team_idx or 0))
            bg = (58, 60, 70) if not sel else (88, 92, 110)
            pygame.draw.rect(screen, bg, r, border_radius=8)
            pygame.draw.rect(screen, (24, 24, 28), r, 2, border_radius=8)
            nm = t.get("name", f"Team {i}")
            txt = self.font.render(nm, True, (230,230,235))
            screen.blit(txt, (r.x + 10, r.y + (r.h - txt.get_height()) // 2))
        screen.set_clip(prev)
        # scrollbar for team list
        content_h = len(self._teams()) * row_h
        self._draw_scrollbar(screen, inner, content_h, self.scroll_teams)

    def _draw_roster(self, screen: pygame.Surface):
        rect = self.rect_roster
        if not rect: return
        list_area = rect.inflate(-16, -54); list_area.y = rect.y + 36
        row_h = 28
        team = self._selected_team(); fighters = team.get("fighters", []) if team else []

        prev = screen.get_clip(); screen.set_clip(list_area)
        for i, p in enumerate(fighters):
            y = list_area.y + i*row_h + self.scroll_players
            rr = pygame.Rect(list_area.x, y, list_area.w, row_h-4)
            sel = (i == self.player_idx)
            bg = (58,60,70) if not sel else (88, 92, 110)
            pygame.draw.rect(screen, bg, rr, border_radius=8)
            pygame.draw.rect(screen, (24,24,28), rr, 2, border_radius=8)
            nm = f"{self._display_name(p)}   #{int(p.get('num',0)):02d}   OVR {int(p.get('OVR',p.get('ovr',60)))}"
            txt = self.font.render(nm, True, (230,230,235))
            screen.blit(txt, (rr.x + 10, rr.y + (rr.h - txt.get_height()) // 2))
        screen.set_clip(prev)
        # scrollbar for roster list
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

        name_raw = G("name", None) or G("Name", None)
        name = self._display_name(p) if not name_raw else str(name_raw)
        race = self._pretty_race(G("race","-"))
        origin = G("origin", self._country().get("name","-"))
        pot = int(G("potential",70))
        cls = G("class","Fighter")
        hp = int(G("hp",10)); max_hp = int(G("max_hp", hp)); ac = int(G("ac",12))
        STR = int(G("str",G("STR",10))); DEX = int(G("dex",G("DEX",10))); CON = int(G("con",G("CON",10)))
        INT = int(G("int",G("INT",10))); WIS = int(G("wis",G("WIS",10))); CHA = int(G("cha",G("CHA",10)))

        wpn = G("weapon",{})
        weapon_name = (wpn.get("name") if isinstance(wpn,dict) else (wpn if isinstance(wpn,str) else "-"))
        armor_val = (
            G("equipped_armor", None)
            or (G("armor",{}).get("name") if isinstance(G("armor",None),dict) else (G("armor") if isinstance(G("armor",None),str) else None))
            or G("armor_name", None) or "-"
        )

        clip = rect.inflate(-12, -16)
        prev = screen.get_clip(); screen.set_clip(clip)

        x0 = rect.x + 12
        y = rect.y + 12 + self.scroll_stats
        line_h = self.font.get_height() + 6

        def line(text: str):
            nonlocal y
            surf = self.font.render(text, True, (220,220,225))
            screen.blit(surf, (x0, y)); y += line_h

        # Minimal, label-free top: name + jersey + LVL and OVR/POT
        line(f"{name}    #{num_format(G('num',0))}    LVL: {level}")
        line(f"{race}    {origin}    OVR: {ovr}    POT: {pot}")
        line(f"{cls}    HP: {hp}/{max_hp}    AC: {ac}")

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

        user_tid = self.team_idx if self.team_idx is not None else 0
        Career = _import_opt("core.career.Career")
        if Career is not None:
            names = [t["name"] for t in remapped]
            car = Career.new(seed=self.seed, n_teams=len(remapped), team_size=len(remapped[0]["fighters"]) if remapped else 12,
                             names=names, fighters=remapped, user_tid=int(user_tid))
        else:
            car = type("MiniCareer", (), {})()
            car.teams = remapped; car.week = 1; car.user_tid = int(user_tid); car.seed = self.seed
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
                    size = len(t.get("fighters", [])) or 8
                    new_list = []
                    for j in range(size):
                        f = self._try_real_generator(r, country)
                        if isinstance(f, dict):
                            f["team_id"] = tid
                            f["pid"] = (j % 99)
                            f["num"] = (j % 99) + 1
                            f.setdefault("origin", country)
                            f.setdefault("name", f"{country[:1]}{tid}-{j:02d}")
                        else:
                            f = _fallback_generate_fighter(tid, (j % 99) + 1, country, r)
                        new_list.append(f)
                    t["fighters"] = new_list
        self.player_idx = 0; self.scroll_players = self.scroll_stats = 0

def num_format(n) -> str:
    try:
        return f"{int(n):02d}"
    except Exception:
        return "00"

# --- back-compat exports (make both names available) ---
TeamSelect = TeamSelectState
__all__ = ["TeamSelectState", "TeamSelect"]
