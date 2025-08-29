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

try:
    from core.creator import generate_fighter
except Exception:
    generate_fighter = None  # type: ignore

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

class TeamSelectState:
    """
    3 columns: Countries | League (Top/Bottom) + Teams | Roster (top) + Player (bottom)
    Regenerate button (top-right) rerolls players for every team in all countries/leagues.
    """
    def __init__(self, app):
        self.app = app
        # slightly smaller fonts for tighter layout
        self.font  = pygame.font.SysFont(None, 22)
        self.h1    = pygame.font.SysFont(None, 34)
        self.h2    = pygame.font.SysFont(None, 20)
        self.small = pygame.font.SysFont(None, 18)

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
                    fighters = [self._new_fighter(tid, (j % 99)+1, cname, rng) for j in range(12)]
                    teams.append({"tid": tid, "name": name, "color": color, "fighters": fighters})
                leagues.append({"name": lname if li==0 else 'Division', "teams": teams})
            world["countries"].append({"name": cname, "leagues": leagues})
        return world

    def _new_fighter(self, tid: int, num: int, country: str, rng: random.Random) -> Dict[str, Any]:
        if generate_fighter:
            p = generate_fighter(seed=rng.randint(0, 10_000_000))
            p["num"] = p.get("num", num)
            p["team_id"] = tid
            p["origin"] = p.get("origin", country)
            p["OVR"] = p.get("OVR", p.get("ovr", 60))
            return p
        # fallback simple generator
        name = f"F{tid}-{num:02d}"
        STR = 10 + rng.randint(-1, 3)
        DEX = 10 + rng.randint(-1, 3)
        CON = 10 + rng.randint(-1, 3)
        INT = 8 + rng.randint(0, 2)
        WIS = 8 + rng.randint(0, 2)
        CHA = 8 + rng.randint(0, 2)
        ovr = int(0.6*STR + 0.7*DEX + 0.6*CON + 0.3*CHA + 4)
        return {
            "pid": int(f"{tid}{num:02d}"),
            "name": name,
            "num": num,
            "race": "Human",
            "origin": country,
            "class": "Fighter",
            "hp": 10, "max_hp": 10, "ac": 12,
            "STR": STR, "DEX": DEX, "CON": CON, "INT": INT, "WIS": WIS, "CHA": CHA,
            "OVR": ovr, "potential": ovr + rng.randint(3, 15),
            "weapon": {"name": "Sword"},
            "equipped_armor": "Leather",
            "team_id": tid,
        }

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
                self.scroll_players = self._clamp_scroll(self.scroll_players, event.y*step, len(self._selected_team().get("fighters", [])), 28, list_area)
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

    def _draw_roster(self, screen: pygame.Surface):
        rect = self.rect_roster
        if not rect: return
        # removed header: Players
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
            nm = f"{p.get('name','?')}   #{int(p.get('num',0)):02d}   OVR {int(p.get('OVR',p.get('ovr',60)))}"
            txt = self.font.render(nm, True, (230,230,235))
            screen.blit(txt, (rr.x + 10, rr.y + (rr.h - txt.get_height()) // 2))
        screen.set_clip(prev)

    def _draw_player_stats(self, screen: pygame.Surface):
        rect = self.rect_stats
        if not rect: return

        p = self._selected_player()
        if not p:
            self.stats_content_h = 0
            return

        def G(key, default=None): return p.get(key, p.get(key.upper(), default))

        name = G("name","Unknown"); num = int(G("num",0))
        race = G("race","-"); origin = G("origin", self._country().get("name","-"))
        ovr = int(G("ovr", G("OVR", 60))); pot = int(G("potential",70))
        cls = G("class","Fighter"); hp = int(G("hp",10)); max_hp = int(G("max_hp", hp)); ac = int(G("ac",12))
        STR = int(G("str",G("STR",10))); DEX = int(G("dex",G("DEX",10))); CON = int(G("con",G("CON",10)))
        INT = int(G("int",G("INT",10))); WIS = int(G("wis",G("WIS",10))); CHA = int(G("cha",G("CHA",10)))

        wpn = G("weapon",{})
        weapon_name = (wpn.get("name") if isinstance(wpn,dict) else (wpn if isinstance(wpn,str) else "-"))
        equipped_armor = (
            G("equipped_armor", None)
            or (G("armor",{}).get("name") if isinstance(G("armor",None),dict) else (G("armor") if isinstance(G("armor",None),str) else None))
            or G("armor_name", None) or "-"
        )

        clip = rect.inflate(-12, -16)
        prev = screen.get_clip(); screen.set_clip(clip)

        x0 = rect.x + 12
        y = rect.y + 12 + self.scroll_stats   # moved up (was +36)
        line_h = self.font.get_height() + 6

        def line(text: str):
            nonlocal y
            surf = self.font.render(text, True, (220,220,225))
            screen.blit(surf, (x0, y)); y += line_h

        # Removed "Player" header and labels for name/race/origin
        line(f"{name}    #{num:02d}")
        line(f"{race}    {origin}    OVR: {ovr}    Potential: {pot}")
        line(f"Class: {cls}    HP: {hp}/{max_hp}    AC: {ac}")

        y += 4
        labels = ("STR","DEX","CON","INT","WIS","CHA"); vals = (STR,DEX,CON,INT,WIS,CHA)
        col_w = (rect.w - 24) // 6; top_y = y
        for i, lab in enumerate(labels):
            lx = x0 + i*col_w + col_w//2
            surf = self.small.render(lab, True, (210,210,215))
            screen.blit(surf, (lx - surf.get_width()//2, top_y))
        y = top_y + self.small.get_height() + 4
        for i, v in enumerate(vals):
            lx = x0 + i*col_w + col_w//2
            surf = self.h2.render(str(v), True, (235,235,240))
            screen.blit(surf, (lx - surf.get_width()//2, y))
        y += self.h2.get_height() + 10

        line(f"Equipped Armor: {equipped_armor}    Weapon: {weapon_name}")

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

    def _tn(self, tid):
        t = self._selected_team()
        return t.get("name", f"Team {tid}") if t else f"Team {tid}"

    def _regen_all_fighters(self):
        r = random.Random()
        for c in self.world.get("countries", []):
            country = c.get("name", "Unknown")
            for league in c.get("leagues", []):
                for t in league.get("teams", []):
                    tid = int(t.get("tid", 0))
                    size = len(t.get("fighters", [])) or 8
                    t["fighters"] = [self._new_fighter(tid, (j%99)+1, country, r) for j in range(size)]
        self.player_idx = 0; self.scroll_players = self.scroll_stats = 0

__all__ = ['TeamSelectState']
TeamSelect = TeamSelectState
