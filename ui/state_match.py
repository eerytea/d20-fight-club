# ui/state_match.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import math
import random
import traceback

# ==========================
# Grid / Board constants
# ==========================
GRID_COLS = 9
GRID_ROWS = 5
TILE      = 64

BOARD_BG  = (34, 36, 44)
GRID_LINE = (26, 28, 34)

# ==========================
# Small UI Button
# ==========================
@dataclass
class Button:
    rect: pygame.Rect
    text: str
    action: callable
    hover: bool = False
    disabled: bool = False

    def draw(self, surf: pygame.Surface, font: pygame.font.Font):
        bg = (58,60,70) if not self.hover else (76,78,90)
        if self.disabled: bg = (48,48,54)
        pygame.draw.rect(surf, bg, self.rect, border_radius=10)
        pygame.draw.rect(surf, (24,24,28), self.rect, 2, border_radius=10)
        color = (235,235,240) if not self.disabled else (160,160,165)
        txt = font.render(self.text, True, color)
        surf.blit(txt, (self.rect.x + 14, self.rect.y + (self.rect.h - txt.get_height()) // 2))

    def handle(self, ev: pygame.event.Event):
        if self.disabled: return
        if ev.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                self.action()

# ==========================
# Utility
# ==========================
def _team_name(career, tid: int) -> str:
    try:
        if hasattr(career, "team_name") and callable(career.team_name):
            return career.team_name(int(tid))
        for t in getattr(career, "teams", []):
            if int(t.get("tid", -1)) == int(tid):
                return t.get("name", f"Team {tid}")
    except Exception:
        pass
    return f"Team {tid}"

def _avg_ovr(team: Dict[str,Any]) -> float:
    fs = team.get("fighters", []) or []
    if not fs: return 60.0
    s = 0.0; n = 0
    for p in fs:
        try: s += float(p.get("OVR", p.get("ovr", p.get("OVR_RATING", 60)))); n += 1
        except Exception: pass
    return s / max(1, n)

def _fixtures_for_week(car, week_idx: int) -> List[Any]:
    weeks = getattr(car, "fixtures_by_week", None)
    if weeks and 0 <= week_idx-1 < len(weeks):
        return weeks[week_idx-1]
    fixtures = getattr(car, "fixtures", [])
    out: List[Any] = []
    for f in fixtures:
        w = f.get("week") if isinstance(f, dict) else None
        if w == week_idx:
            out.append(f)
    return out

def _set_fixture_result(raw: Any, sh: int, sa: int):
    try:
        if isinstance(raw, dict):
            raw["score_home"] = sh
            raw["score_away"] = sa
            raw["played"] = True
            raw["is_played"] = True
        elif isinstance(raw, list):
            while len(raw) < 4: raw.append(None)
            raw[2] = sh; raw[3] = sa
    except Exception:
        pass

def _recompute_standings(car):
    for hook in ("_recompute_standings", "recompute_standings", "recalc_standings", "_recalc_tables"):
        fn = getattr(car, hook, None)
        if callable(fn):
            try:
                fn(); return
            except Exception:
                pass
    try:
        if not hasattr(car, "standings"): car.standings = {}
        for t in car.teams:
            tid = int(t["tid"])
            car.standings.setdefault(tid, {"tid": tid, "pts":0, "w":0, "d":0, "l":0, "gf":0, "ga":0, "gd":0, "name":t["name"]})
            s = car.standings[tid]
            s.update({"pts":0, "w":0, "d":0, "l":0, "gf":0, "ga":0, "gd":0, "name":t["name"]})
        # Walk through all played weeks
        wmax = getattr(car, "week", 1)
        weeks = getattr(car, "fixtures_by_week", [])
        total_weeks = len(weeks) if weeks else wmax
        for w in range(1, min(wmax, total_weeks)+1):
            fxs = _fixtures_for_week(car, w)
            for f in fxs:
                if not isinstance(f, dict): continue
                played = f.get("played", f.get("is_played", False))
                sh = f.get("score_home"); sa = f.get("score_away")
                if not played or sh is None or sa is None: continue
                h = int(f.get("home_id", f.get("home_tid", f.get("A", 0))))
                a = int(f.get("away_id", f.get("away_tid", f.get("B", 0))))
                shs = car.standings[h]; sas = car.standings[a]
                shs["gf"] += int(sh); shs["ga"] += int(sa)
                sas["gf"] += int(sa); sas["ga"] += int(sh)
                if sh > sa:
                    shs["w"] += 1; sas["l"] += 1; shs["pts"] += 3
                elif sh < sa:
                    sas["w"] += 1; shs["l"] += 1; sas["pts"] += 3
                else:
                    shs["d"] += 1; sas["d"] += 1; shs["pts"] += 1; sas["pts"] += 1
        table = []
        for tid, s in car.standings.items():
            s["gd"] = s["gf"] - s["ga"]
            table.append(s)
        table.sort(key=lambda r: (r["pts"], r["gd"], r["gf"]), reverse=True)
        car.table_sorted = table
    except Exception:
        pass

# ==========================
# Units
# ==========================
@dataclass
class Unit:
    pid: int
    team: str         # "home" or "away"
    name: str
    ovr: int
    hp: int
    max_hp: int
    ac: int
    atk_mod: int
    dmg_mod: int
    cx: int
    cy: int
    alive: bool = True

# ==========================
# Match State
# ==========================
class MatchState:
    """
    Watchable grid match:
      - 5 vs 5 units.
      - Move toward nearest enemy and melee when adjacent.
      - Score = KOs (written back to fixtures).
    Supports preset lineup via fixture["preset_lineup"] from the tactics screen.
    Constructor shapes supported:
      (app, career, fixture)
      (app, fixture, career)
      (app, fixture)
      (app, home_tid, away_tid, career) [fallback: builds fixture]
      (app, home_tid, away_tid)
    """
    def __init__(self, *args, **kwargs):
        # Parse constructor permutations
        self.app = None
        self.career = None
        self.fixture: Dict[str,Any] = {}

        if len(args) >= 3 and hasattr(args[0], "screen"):
            # (app, career, fixture) OR (app, fixture, career)
            self.app = args[0]
            if isinstance(args[1], dict) and not isinstance(args[2], dict):
                self.fixture = dict(args[1]); self.career = args[2]
            elif not isinstance(args[1], dict) and isinstance(args[2], dict):
                self.career = args[1]; self.fixture = dict(args[2])
            else:
                # (app, fixture) only
                self.fixture = dict(args[1])
        elif len(args) >= 4 and hasattr(args[0], "screen"):
            # (app, home_tid, away_tid, career)
            self.app = args[0]; home = int(args[1]); away = int(args[2]); self.career = args[3]
            self.fixture = {"home_id": home, "away_id": away, "home_tid": home, "away_tid": away, "A": home, "B": away,
                            "week": getattr(self.career, "week", 1), "played": False, "score_home": None, "score_away": None}
        elif len(args) >= 3 and hasattr(args[0], "screen"):
            # (app, home_tid, away_tid)
            self.app = args[0]; home = int(args[1]); away = int(args[2])
            self.fixture = {"home_id": home, "away_id": away, "home_tid": home, "away_tid": away, "A": home, "B": away,
                            "week": 1, "played": False, "score_home": None, "score_away": None}
        else:
            raise TypeError("Unsupported MatchState constructor signature")

        # Defaults if career missing
        if self.career is None:
            self.career = type("MiniCar", (), {})()
            self.career.teams = []
            self.career.week  = self.fixture.get("week", 1)

        # Parse home/away ids
        self.home_tid = int(self.fixture.get("home_id", self.fixture.get("home_tid", self.fixture.get("A", 0))))
        self.away_tid = int(self.fixture.get("away_id", self.fixture.get("away_tid", self.fixture.get("B", 0))))
        self.week     = int(self.fixture.get("week", getattr(self.career, "week", 1)))

        # Fonts
        self.font  = pygame.font.SysFont(None, 22)
        self.h1    = pygame.font.SysFont(None, 34)
        self.h2    = pygame.font.SysFont(None, 20)

        # Layout rects
        self.rect_header: Optional[pygame.Rect] = None
        self.rect_board:  Optional[pygame.Rect] = None
        self.rect_side:   Optional[pygame.Rect] = None

        # Buttons
        self.btns: List[Button] = []
        self.running = False
        self.fast = False
        self.finished = False

        # Board & units
        self.grid_cols = GRID_COLS
        self.grid_rows = GRID_ROWS
        self.tile = TILE

        self.units: List[Unit] = []
        self.home_kos = 0
        self.away_kos = 0

        # Initiative pacing
        self._accum = 0.0
        self._step_interval = 0.4  # seconds per unit action (slower); faster when fast=True

        # Prepare rosters and placement in enter()
        # but we also need preset hook available here for external calls
        self._preset_from_fixture: Optional[Dict[str,Any]] = self.fixture.get("preset_lineup") if isinstance(self.fixture, dict) else None

    # ------------- lifecycle -------------
    def enter(self):
        w, h = self.app.screen.get_size()
        pad = 16

        self.rect_header = pygame.Rect(pad, pad, w - pad*2, 48)
        # Board on left, side controls on right
        board_w = self.grid_cols * self.tile
        board_h = self.grid_rows * self.tile
        bx = pad + 4
        by = self.rect_header.bottom + pad
        self.rect_board = pygame.Rect(bx, by, board_w, board_h)
        self.rect_side  = pygame.Rect(self.rect_board.right + pad, by, max(360, w - (self.rect_board.right + pad*2)), board_h)

        # Buttons in side panel
        sx, sy = self.rect_side.x + 12, self.rect_side.y + 12
        bw, bh, gap = self.rect_side.w - 24, 44, 10
        def add(label, cb):
            nonlocal sy
            b = Button(pygame.Rect(sx, sy, bw, bh), label, cb)
            self.btns.append(b); sy += (bh + gap)
        add("Start / Pause", self._toggle_start_pause)
        add("Fast (toggle)", self._toggle_fast)
        add("Skip (Instant)", self._skip_to_end)

        # Team names
        self.home_name = _team_name(self.career, self.home_tid)
        self.away_name = _team_name(self.career, self.away_tid)

        # Build units (5 per side)
        home_list = self._team_fighters(self.home_tid)
        away_list = self._team_fighters(self.away_tid)

        # Choose five (by OVR top 5 if available)
        def top5(lst):
            try:
                return sorted(lst, key=lambda p: int(p.get("OVR", p.get("ovr", 60))), reverse=True)[:5]
            except Exception:
                return lst[:5]
        sel_home = top5(home_list)
        sel_away = top5(away_list)

        # Convert to Units
        self.units = []
        # default placement grids (home left, away right)
        home_cols = [1,1,1,0,0] if self.grid_cols >= 2 else [0]*5
        home_rows = self._spread_rows(len(sel_home))
        away_cols = [self.grid_cols-2, self.grid_cols-2, self.grid_cols-2, self.grid_cols-1, self.grid_cols-1] if self.grid_cols >= 2 else [self.grid_cols-1]*5
        away_rows = self._spread_rows(len(sel_away))

        # Build units with stats
        for i, p in enumerate(sel_home):
            u = self._make_unit(p, team="home",
                                cx=home_cols[i % len(home_cols)],
                                cy=home_rows[i % len(home_rows)])
            self.units.append(u)
        for i, p in enumerate(sel_away):
            u = self._make_unit(p, team="away",
                                cx=away_cols[i % len(away_cols)],
                                cy=away_rows[i % len(away_rows)])
            self.units.append(u)

        # Apply preset lineup from tactics if present (overrides positions for the user's side)
        if self._preset_from_fixture:
            try:
                self._apply_preset_lineup(self._preset_from_fixture.get("side","home"),
                                          self._preset_from_fixture.get("slots", []))
            except Exception:
                traceback.print_exc()

    def handle(self, ev: pygame.event.Event):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                if self.finished:
                    self._back_to_hub()
                else:
                    # confirm? for now just go back
                    self._back_to_hub()
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._toggle_start_pause()
            elif ev.key == pygame.K_f:
                self._toggle_fast()
            elif ev.key == pygame.K_s:
                self._skip_to_end()

        for b in self.btns:
            # After finish, morph buttons into a single Back button
            b.handle(ev)

    def update(self, dt: float):
        if self.finished or not self.running:
            return
        speed = 3.0 if self.fast else 1.0
        self._accum += dt * speed
        while self._accum >= self._step_interval:
            self._accum -= self._step_interval
            self._step_once()
            if self._check_finish():
                self._finalize_result()
                break

    def draw(self, screen: pygame.Surface):
        screen.fill((16,16,20))

        # header
        pygame.draw.rect(screen, (42,44,52), self.rect_header, border_radius=12)
        pygame.draw.rect(screen, (24,24,28), self.rect_header, 2, border_radius=12)
        t1 = self.h1.render(f"{self.home_name} vs {self.away_name}", True, (235,235,240))
        t2 = self.h1.render(f"Week {self.week}", True, (220,220,225))
        screen.blit(t1, (self.rect_header.x + 12, self.rect_header.y + (self.rect_header.h - t1.get_height())//2))
        screen.blit(t2, (self.rect_header.right - t2.get_width() - 12, self.rect_header.y + (self.rect_header.h - t2.get_height())//2))

        # board
        pygame.draw.rect(screen, (42,44,52), self.rect_board, border_radius=10)
        pygame.draw.rect(screen, (24,24,28), self.rect_board, 2, border_radius=10)
        for c in range(self.grid_cols):
            for r in range(self.grid_rows):
                rect = self._cell_rect(c,r)
                pygame.draw.rect(screen, BOARD_BG, rect)
                pygame.draw.rect(screen, GRID_LINE, rect, 1)

        # units
        for u in self.units:
            if not u.alive: continue
            rect = self._cell_rect(u.cx, u.cy)
            self._draw_unit(screen, rect, u)

        # side panel
        pygame.draw.rect(screen, (42,44,52), self.rect_side, border_radius=10)
        pygame.draw.rect(screen, (24,24,28), self.rect_side, 2, border_radius=10)
        x = self.rect_side.x + 12
        y = self.rect_side.y + 12 + (44+10)*3 + 8  # below buttons
        lh = self.font.get_height() + 8

        score_text = self.h2.render("Score (KOs)", True, (215,215,220))
        screen.blit(score_text, (x, y)); y += lh
        s_line = self.font.render(f"{self.home_name}: {self.home_kos}     {self.away_name}: {self.away_kos}", True, (230,230,235))
        screen.blit(s_line, (x, y)); y += lh

        # status / controls
        y += 8
        st = "FINISHED" if self.finished else ("RUNNING" if self.running else "PAUSED")
        st_s = self.font.render(f"Status: {st}   Speed: {'FAST' if self.fast else 'NORMAL'}", True, (230,230,235))
        screen.blit(st_s, (x, y)); y += lh

        if self.finished:
            y += 10
            done = self.h2.render("Match complete. Press Backspace/Esc to return.", True, (210,210,215))
            screen.blit(done, (x, y))

        # draw buttons last
        for b in self.btns:
            b.draw(screen, self.font)
        if self.finished:
            # Overlay a big "Back to Hub" button on top of Skip
            back_rect = pygame.Rect(self.btns[-1].rect.x, self.btns[-1].rect.y, self.btns[-1].rect.w, self.btns[-1].rect.h)
            pygame.draw.rect(screen, (88,92,110), back_rect, border_radius=10)
            pygame.draw.rect(screen, (24,24,28), back_rect, 2, border_radius=10)
            txt = self.font.render("Back to Hub", True, (235,235,240))
            screen.blit(txt, (back_rect.x + 14, back_rect.y + (back_rect.h - txt.get_height()) // 2))

    # ------------- controls -------------
    def _toggle_start_pause(self):
        if self.finished: return
        self.running = not self.running

    def _toggle_fast(self):
        if self.finished: return
        self.fast = not self.fast

    def _skip_to_end(self):
        if self.finished: 
            self._back_to_hub(); 
            return
        # Simulate instantly
        guard = 0
        while not self.finished and guard < 2000:
            self._step_once()
            if self._check_finish():
                self._finalize_result()
                break
            guard += 1

    def _back_to_hub(self):
        self.app.pop_state()

    # ------------- unit helpers -------------
    def _team_fighters(self, tid: int) -> List[Dict[str,Any]]:
        for t in getattr(self.career, "teams", []):
            if int(t.get("tid", -1)) == int(tid):
                return t.get("fighters", [])
        return []

    def _make_unit(self, p: Dict[str,Any], team: str, cx: int, cy: int) -> Unit:
        def G(k,d=None): return p.get(k, p.get(k.upper(), d))
        name = (G("name") or (f"{G('first','') } {G('last','')}".strip())) or "Fighter"
        hp   = int(G("hp", G("max_hp", 10)))
        max_hp = int(G("max_hp", hp))
        ac   = int(G("ac", 12))
        STR  = int(G("str", G("STR", 10)))
        DEX  = int(G("dex", G("DEX", 10)))
        ovr  = int(G("ovr", G("OVR", 60)))
        # Basic melee attack mod: better of STR/DEX mod (+ ovr influence small)
        atk_mod = max((STR-10)//2, (DEX-10)//2) + (ovr-60)//20
        dmg_mod = max((STR-10)//2, 0)
        return Unit(pid=int(G("pid", -1)), team=team, name=name, ovr=ovr,
                    hp=hp, max_hp=max_hp, ac=ac, atk_mod=atk_mod, dmg_mod=dmg_mod,
                    cx=int(cx), cy=int(cy), alive=True)

    def _cell_rect(self, cx: int, cy: int) -> pygame.Rect:
        return pygame.Rect(self.rect_board.x + cx*self.tile,
                           self.rect_board.y + cy*self.tile, self.tile, self.tile)

    def _spread_rows(self, n: int) -> List[int]:
        rows = list(range(self.grid_rows))
        # center-first ordering
        center = self.grid_rows // 2
        order = [center]
        for i in range(1, self.grid_rows):
            if center - i >= 0: order.append(center - i)
            if center + i < self.grid_rows: order.append(center + i)
        return order[:max(1,n)]

    def clear_side_units(self, side: str):
        for u in self.units:
            if u.team == side:
                u.alive = False

    def spawn_unit(self, side: str, fighter: Dict[str,Any], cx: int, cy: int):
        # Remove any existing on that exact cell (prevent overlap)
        for u in self.units:
            if u.alive and u.cx == cx and u.cy == cy:
                u.alive = False
        self.units.append(self._make_unit(fighter, side, cx, cy))

    def _apply_preset_lineup(self, side: str, slots: List[Dict[str,Any]]):
        """Called from enter(); places given pids for side at cx,cy and removes defaults for that side."""
        team_tid = self.home_tid if side == "home" else self.away_tid
        roster = self._team_fighters(team_tid)
        pid_to_fighter = { int(p.get("pid",-1)): p for p in roster }
        # clear current
        self.clear_side_units(side)
        # place new
        for slot in slots:
            pid = int(slot.get("pid", -1))
            cx  = int(slot.get("cx", 0))
            cy  = int(slot.get("cy", 0))
            f = pid_to_fighter.get(pid)
            if f is None: 
                continue
            self.spawn_unit(side, f, cx, cy)

    # ------------- sim -------------
    def _units_alive(self, side: Optional[str]=None) -> List[Unit]:
        return [u for u in self.units if u.alive and (side is None or u.team == side)]

    def _nearest_enemy(self, u: Unit) -> Optional[Unit]:
        enemies = self._units_alive("away" if u.team == "home" else "home")
        if not enemies: return None
        best = None; best_d = 1e9
        for e in enemies:
            d = abs(e.cx - u.cx) + abs(e.cy - u.cy)
            if d < best_d:
                best = e; best_d = d
        return best

    def _step_once(self):
        # simple initiative: home units first, then away
        order = self._units_alive("home") + self._units_alive("away")
        rnd = random.Random(12345)  # deterministic local jitter for tie-breaks
        for u in order:
            if not u.alive: continue
            tgt = self._nearest_enemy(u)
            if tgt is None:
                continue
            # if adjacent, attack
            if abs(tgt.cx - u.cx) + abs(tgt.cy - u.cy) <= 1:
                self._attack(u, tgt, rnd)
            else:
                # move one step toward target (greedy; prefer horizontal advance)
                dx = 1 if tgt.cx > u.cx else -1 if tgt.cx < u.cx else 0
                dy = 1 if tgt.cy > u.cy else -1 if tgt.cy < u.cy else 0
                step = (u.cx + (dx if dx != 0 else 0), u.cy + (dy if dx == 0 else 0))
                # If step occupied or off board, try vertical/horizontal swap
                if not self._can_move_to(*step):
                    alt = (u.cx, u.cy + (dy if dy != 0 else 0))
                    if self._can_move_to(*alt):
                        step = alt
                    else:
                        alt2 = (u.cx + (dx if dx != 0 else 0), u.cy)
                        if self._can_move_to(*alt2):
                            step = alt2
                        else:
                            step = (u.cx, u.cy)
                u.cx, u.cy = step

    def _can_move_to(self, cx: int, cy: int) -> bool:
        if cx < 0 or cy < 0 or cx >= self.grid_cols or cy >= self.grid_rows:
            return False
        for x in self.units:
            if x.alive and x.cx == cx and x.cy == cy:
                return False
        return True

    def _attack(self, a: Unit, d: Unit, rnd: random.Random):
        # D20 to hit
        roll = rnd.randint(1, 20)
        hit = (roll + a.atk_mod) >= d.ac
        if hit:
            dmg = max(1, rnd.randint(1, 8) + a.dmg_mod)
            d.hp -= dmg
            if d.hp <= 0:
                d.alive = False
                if d.team == "home": self.away_kos += 1
                else: self.home_kos += 1

    def _check_finish(self) -> bool:
        if not self._units_alive("home") or not self._units_alive("away"):
            return True
        return False

    def _finalize_result(self):
        self.finished = True
        self.running = False
        sh, sa = self.home_kos, self.away_kos

        # Write back to fixture store
        try:
            # Find raw fixture object for this week & teams
            weeks = getattr(self.career, "fixtures_by_week", None)
            raw = None
            if weeks and 0 <= self.week-1 < len(weeks):
                for f in weeks[self.week-1]:
                    if isinstance(f, dict):
                        h = int(f.get("home_id", f.get("home_tid", f.get("A", -1))))
                        a = int(f.get("away_id", f.get("away_tid", f.get("B", -1))))
                        if h == self.home_tid and a == self.away_tid:
                            raw = f; break
                    elif isinstance(f, (list, tuple)):
                        h = int(f[0]) if len(f)>=1 else -1
                        a = int(f[1]) if len(f)>=2 else -1
                        if h == self.home_tid and a == self.away_tid:
                            raw = f; break
            if raw is None:
                # fallback search in flat fixtures
                for f in getattr(self.career, "fixtures", []):
                    if not isinstance(f, dict): continue
                    if int(f.get("week", -1)) != self.week: continue
                    h = int(f.get("home_id", f.get("home_tid", f.get("A", -1))))
                    a = int(f.get("away_id", f.get("away_tid", f.get("B", -1))))
                    if h == self.home_tid and a == self.away_tid:
                        raw = f; break
            _set_fixture_result(raw, sh, sa)
        except Exception:
            traceback.print_exc()

        _recompute_standings(self.career)

    # ------------- drawing helpers -------------
    def _draw_unit(self, surf: pygame.Surface, rect: pygame.Rect, u: Unit):
        # color by team
        bg = (80, 128, 100) if u.team == "home" else (120, 92, 120)
        pygame.draw.rect(surf, bg, rect, border_radius=6)
        pygame.draw.rect(surf, (22,24,28), rect, 2, border_radius=6)

        # name / ovr
        nm = self._short(_safe(u.name), 12)
        l1 = self.font.render(nm, True, (240,240,245))
        l2 = self.font.render(f"{u.ovr}", True, (230,230,235))
        surf.blit(l1, (rect.x + 6, rect.y + 4))
        surf.blit(l2, (rect.right - l2.get_width() - 6, rect.y + 4))

        # HP bar
        bar_w = rect.w - 12
        hp_ratio = max(0.0, min(1.0, u.hp / max(1, u.max_hp)))
        bar_bg = pygame.Rect(rect.x + 6, rect.bottom - 12, bar_w, 6)
        bar_fg = pygame.Rect(rect.x + 6, rect.bottom - 12, int(bar_w * hp_ratio), 6)
        pygame.draw.rect(surf, (40,40,46), bar_bg, border_radius=3)
        pygame.draw.rect(surf, (70,200,90) if u.team=="home" else (200,90,200), bar_fg, border_radius=3)

    def _short(self, s: str, n: int) -> str:
        return s if len(s) <= n else s[:n-1] + "…"

def _safe(x: Any) -> str:
    try: return str(x)
    except Exception: return "?"
