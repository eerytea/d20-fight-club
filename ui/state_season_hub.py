# ui/state_season_hub.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import random
import traceback

try:
    from core.career import Career  # type: ignore
except Exception:
    Career = None  # type: ignore

# ---------- small shared Button (same shape as menu/team_select) ----------
@dataclass
class Button:
    rect: pygame.Rect
    text: str
    action: callable
    hover: bool = False
    disabled: bool = False

    def draw(self, surf: pygame.Surface, font: pygame.font.Font, selected: bool=False):
        bg = (58, 60, 70) if not self.hover else (76, 78, 90)
        if selected: bg = (88, 92, 110)
        if self.disabled: bg = (48, 48, 54)
        pygame.draw.rect(surf, bg, self.rect, border_radius=10)
        pygame.draw.rect(surf, (24, 24, 28), self.rect, 2, border_radius=10)
        color = (235, 235, 240) if not self.disabled else (155, 155, 160)
        txt = font.render(self.text, True, color)
        surf.blit(txt, (self.rect.x + 14, self.rect.y + (self.rect.h - txt.get_height()) // 2))

    def handle(self, ev: pygame.event.Event):
        if self.disabled: return
        if ev.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                self.action()

# ---------- helpers ----------
def _import_opt(fullname: str):
    try:
        module_name, class_name = fullname.rsplit(".", 1)
        mod = __import__(module_name, fromlist=[class_name])
        return getattr(mod, class_name, None)
    except Exception:
        return None

def _team_name(car, tid: int) -> str:
    if hasattr(car, "team_name") and callable(getattr(car, "team_name")):
        try: return car.team_name(int(tid))  # type: ignore
        except Exception: pass
    # fallback: search list
    try:
        for t in getattr(car, "teams", []):
            if int(t.get("tid", -1)) == int(tid):
                return t.get("name", f"Team {tid}")
    except Exception:
        pass
    return f"Team {tid}"

def _avg_ovr(team: Dict[str, Any]) -> float:
    fs = team.get("fighters", []) or []
    if not fs: return 60.0
    s = 0.0; n = 0
    for p in fs:
        try:
            s += float(p.get("OVR", p.get("ovr", p.get("OVR_RATING", 60))))
            n += 1
        except Exception:
            pass
    return s / max(1, n)

def _norm_fixture(f: Any) -> Dict[str, Any]:
    """
    Normalize a fixture to dict:
      {home: int, away: int, played: bool, sh: Optional[int], sa: Optional[int]}
    Works with tuples/lists or dicts from various shapes.
    """
    if isinstance(f, dict):
        home = f.get("home_tid", f.get("home", f.get("h", f.get("home_id", 0))))
        away = f.get("away_tid", f.get("away", f.get("a", f.get("away_id", 0))))
        sh = f.get("score_home", f.get("sh", f.get("home_score")))
        sa = f.get("score_away", f.get("sa", f.get("away_score")))
        played = f.get("played", f.get("is_played", (sh is not None and sa is not None)))
        return {"home": int(home), "away": int(away), "played": bool(played), "sh": sh, "sa": sa, "_raw": f}
    if isinstance(f, (list, tuple)):
        home = int(f[0]) if len(f) >= 1 else 0
        away = int(f[1]) if len(f) >= 2 else 0
        sh = f[2] if len(f) >= 3 else None
        sa = f[3] if len(f) >= 4 else None
        played = (sh is not None and sa is not None)
        return {"home": home, "away": away, "played": bool(played), "sh": sh, "sa": sa, "_raw": f}
    # unknown
    return {"home": 0, "away": 0, "played": False, "sh": None, "sa": None, "_raw": f}

def _fixtures_for_week(car, week_idx: int) -> List[Dict[str, Any]]:
    weeks = getattr(car, "fixtures_by_week", None)
    if weeks and 0 <= week_idx-1 < len(weeks):
        return [_norm_fixture(x) for x in weeks[week_idx-1]]
    # fallback: single list with week field
    fixtures = getattr(car, "fixtures", [])
    out: List[Dict[str, Any]] = []
    for f in fixtures:
        w = f.get("week") if isinstance(f, dict) else None
        if w == week_idx:
            out.append(_norm_fixture(f))
    return out

def _set_fixture_result(raw: Any, sh: int, sa: int):
    """Write back scores & played flag onto various shapes."""
    try:
        if isinstance(raw, dict):
            for k, v in (("score_home", sh), ("score_away", sa), ("played", True), ("is_played", True)):
                if k in raw or True:
                    raw[k] = v
        elif isinstance(raw, list):
            while len(raw) < 4: raw.append(None)
            raw[2] = sh; raw[3] = sa
        elif isinstance(raw, tuple):
            # tuples are immutable — ignore; many schedulers use dict/list anyway
            pass
    except Exception:
        pass

def _recompute_standings(car):
    for hook in ("_recompute_standings", "recompute_standings", "recalc_standings", "_recalc_tables"):
        fn = getattr(car, hook, None)
        if callable(fn):
            try:
                fn()
                return
            except Exception:
                pass
    # light fallback: points table in car.standings as dict
    try:
        if not hasattr(car, "standings"): return
        # zero
        for t in car.teams:
            car.standings.setdefault(t["tid"], {"tid": t["tid"], "pts": 0, "w":0, "d":0, "l":0, "gf":0, "ga":0})
            s = car.standings[t["tid"]]
            s.update({"pts":0, "w":0, "d":0, "l":0, "gf":0, "ga":0})
        # sum from fixtures
        wmax = getattr(car, "week", 1)
        for w in range(1, wmax+1):
            for fx in _fixtures_for_week(car, w):
                if not fx["played"]: continue
                h, a, sh, sa = fx["home"], fx["away"], int(fx["sh"]), int(fx["sa"])
                shs = car.standings[h]; sas = car.standings[a]
                shs["gf"] += sh; shs["ga"] += sa
                sas["gf"] += sa; sas["ga"] += sh
                if sh > sa:
                    shs["w"] += 1; sas["l"] += 1; shs["pts"] += 3
                elif sh < sa:
                    sas["w"] += 1; shs["l"] += 1; sas["pts"] += 3
                else:
                    shs["d"] += 1; sas["d"] += 1; shs["pts"] += 1; sas["pts"] += 1
    except Exception:
        pass

# ---------- Season Hub ----------
class SeasonHubState:
    def __init__(self, app, career):
        self.app = app
        self.career = career

        self.font  = pygame.font.SysFont(None, 22)
        self.h1    = pygame.font.SysFont(None, 34)
        self.h2    = pygame.font.SysFont(None, 20)

        self.rect_header: Optional[pygame.Rect] = None
        self.rect_left:   Optional[pygame.Rect] = None
        self.rect_right:  Optional[pygame.Rect] = None

        self.btns: List[Button] = []
        self.week = int(getattr(self.career, "week", 1) or 1)

    # ----- lifecycle -----
    def enter(self):
        w, h = self.app.screen.get_size()
        pad = 16
        self.rect_header = pygame.Rect(pad, pad, w - pad*2, 48)
        self.rect_left   = pygame.Rect(pad, self.rect_header.bottom + pad, int(w * 0.62) - pad, h - (self.rect_header.bottom + pad*2))
        self.rect_right  = pygame.Rect(self.rect_left.right + pad, self.rect_left.y, w - (self.rect_left.right + pad*2), self.rect_left.h)

        # Buttons stack
        bx = self.rect_right.x + 12
        by = self.rect_right.y + 12
        bw, bh, gap = self.rect_right.w - 24, 48, 12

        def add(label, cb):
            nonlocal by
            b = Button(pygame.Rect(bx, by, bw, bh), label, cb)
            self.btns.append(b); by += (bh + gap)

        add("Play", self._play)
        add("Sim Week", self._sim_week)
        add("Schedule", self._go_schedule)
        add("Table", self._go_table)
        add("Roster", self._go_roster)
        add("Back", self._back)

    def handle(self, ev: pygame.event.Event):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self._back(); return
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._play(); return
        for b in self.btns:
            b.handle(ev)

    def update(self, dt: float):
        # keep week mirror fresh if career advances externally
        self.week = int(getattr(self.career, "week", self.week) or self.week)

    # ----- drawing -----
    def draw(self, screen: pygame.Surface):
        w, h = screen.get_size()
        screen.fill((16,16,20))

        # header
        hdr = self.rect_header
        pygame.draw.rect(screen, (42,44,52), hdr, border_radius=12)
        pygame.draw.rect(screen, (24,24,28), hdr, 2, border_radius=12)
        user_tid = int(getattr(self.career, "user_tid", 0))
        title = f"Your Team: {_team_name(self.career, user_tid)}"
        t1 = self.h1.render(title, True, (235,235,240))
        t2 = self.h1.render(f"Week {self.week}", True, (220,220,225))
        screen.blit(t1, (hdr.x + 12, hdr.y + (hdr.h - t1.get_height()) // 2))
        screen.blit(t2, (hdr.right - t2.get_width() - 12, hdr.y + (hdr.h - t2.get_height()) // 2))

        # left panel (matchups)
        lp = self.rect_left
        pygame.draw.rect(screen, (42,44,52), lp, border_radius=12)
        pygame.draw.rect(screen, (24,24,28), lp, 2, border_radius=12)
        sub = self.h2.render("This Week's Matchups", True, (215,215,220))
        screen.blit(sub, (lp.x + 12, lp.y + 10))

        week_fixtures = _fixtures_for_week(self.career, self.week)
        y = lp.y + 40
        line_h = self.font.get_height() + 10
        for fx in week_fixtures[:min(12, len(week_fixtures))]:
            hname = _team_name(self.career, fx["home"])
            aname = _team_name(self.career, fx["away"])
            sep = " — " if fx["played"] else "  —  "
            score = f"{fx['sh']} - {fx['sa']}" if fx["played"] and fx["sh"] is not None else ""
            label = f"{hname}  vs  {aname}  {sep}  {score}"
            surf = self.font.render(label, True, (230,230,235))
            screen.blit(surf, (lp.x + 12, y))
            y += line_h

        # right panel (buttons)
        rp = self.rect_right
        pygame.draw.rect(screen, (42,44,52), rp, border_radius=12)
        pygame.draw.rect(screen, (24,24,28), rp, 2, border_radius=12)
        for b in self.btns:
            b.draw(screen, self.font)

    # ----- actions -----
    def _back(self):
        self.app.pop_state()

    def _play(self):
        """Open the user's fixture for the current week."""
        user_tid = int(getattr(self.career, "user_tid", 0))
        week_fixtures = _fixtures_for_week(self.career, self.week)
        my = None
        for fx in week_fixtures:
            if int(fx["home"]) == user_tid or int(fx["away"]) == user_tid:
                my = fx; break
        if not my:
            return  # no match this week?

        home, away = int(my["home"]), int(my["away"])

        # Try several MatchState signatures
        MatchState = _import_opt("ui.state_match.MatchState")
        if MatchState is None:
            return
        # best bet: (app, home_tid, away_tid, career)
        for sig in (
            (self.app, home, away, self.career),
            (self.app, self.career, home, away),
            (self.app, home, away),
        ):
            try:
                st = MatchState(*sig)  # type: ignore
                self.app.push_state(st)
                return
            except TypeError:
                continue
            except Exception:
                traceback.print_exc()
                return
        # if all fail, give up silently

    def _sim_week(self):
        """Advance all AI fixtures (and yours) then move to next week."""
        # Prefer career's native sim
        for name in ("sim_week", "simulate_week", "simulate_current_week", "sim_round"):
            fn = getattr(self.career, name, None)
            if callable(fn):
                try:
                    fn()
                    # some impls also bump week; if not, do it below
                    break
                except Exception:
                    traceback.print_exc()
                    break
        else:
            # Lightweight local simulation
            try:
                rnd = random.Random(getattr(self.career, "seed", 1) + self.week * 777)
                week_fixtures = _fixtures_for_week(self.career, self.week)
                # quick average OVR lookup
                ovr_by_tid = {int(t["tid"]): _avg_ovr(t) for t in getattr(self.career, "teams", [])}
                for fx in week_fixtures:
                    if fx["played"]:  # already done
                        continue
                    h, a = int(fx["home"]), int(fx["away"])
                    hq = ovr_by_tid.get(h, 60.0)
                    aq = ovr_by_tid.get(a, 60.0)
                    # chance to score ~ Poisson-ish using quality
                    hb = max(0.6, (hq - 40.0) / 25.0)
                    ab = max(0.6, (aq - 40.0) / 25.0)
                    sh = max(0, int(rnd.gauss(hb, 0.9)))
                    sa = max(0, int(rnd.gauss(ab, 0.9)))
                    # tiny home edge
                    if rnd.random() < 0.15:
                        sh += 1
                    _set_fixture_result(fx.get("_raw"), sh, sa)
                    fx["played"] = True; fx["sh"] = sh; fx["sa"] = sa
                _recompute_standings(self.career)
            except Exception:
                traceback.print_exc()

        # Advance week if possible
        try:
            total_weeks = len(getattr(self.career, "fixtures_by_week", [])) or getattr(self.career, "total_weeks", 0)
            self.career.week = min(int(getattr(self.career, "week", 1)) + 1, total_weeks or 9999)
            self.week = int(self.career.week)
            _recompute_standings(self.career)
        except Exception:
            pass

    def _go_schedule(self):
        for fullname in ("ui.state_schedule.ScheduleState", "ui.state_schedule.Schedule"):
            Cls = _import_opt(fullname)
            if Cls is None: continue
            for args in ((self.app, self.career), (self.app,)):
                try:
                    self.app.push_state(Cls(*args))  # type: ignore
                    return
                except TypeError:
                    continue
                except Exception:
                    traceback.print_exc(); return

    def _go_table(self):
        for fullname in ("ui.state_table.TableState", "ui.state_table.Table"):
            Cls = _import_opt(fullname)
            if Cls is None: continue
            for args in ((self.app, self.career), (self.app,)):
                try:
                    self.app.push_state(Cls(*args))  # type: ignore
                    return
                except TypeError:
                    continue
                except Exception:
                    traceback.print_exc(); return

    def _go_roster(self):
        for fullname in ("ui.state_roster.RosterState", "ui.state_roster.Roster"):
            Cls = _import_opt(fullname)
            if Cls is None: continue
            for args in ((self.app, self.career), (self.app,)):
                try:
                    self.app.push_state(Cls(*args))  # type: ignore
                    return
                except TypeError:
                    continue
                except Exception:
                    traceback.print_exc(); return
