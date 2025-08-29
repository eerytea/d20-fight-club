# ui/state_season_hub.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import random
import traceback

# ---------- small shared Button ----------
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
        try: s += float(p.get("OVR", p.get("ovr", p.get("OVR_RATING", 60)))); n += 1
        except Exception: pass
    return s / max(1, n)

def _norm_fixture(f: Any) -> Dict[str, Any]:
    if isinstance(f, dict):
        home = f.get("home_id", f.get("home_tid", f.get("A", f.get("home", 0))))
        away = f.get("away_id", f.get("away_tid", f.get("B", f.get("away", 0))))
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
    return {"home": 0, "away": 0, "played": False, "sh": None, "sa": None, "_raw": f}

def _fixtures_for_week(car, week_idx: int) -> List[Dict[str, Any]]:
    weeks = getattr(car, "fixtures_by_week", None)
    if weeks and 0 <= week_idx-1 < len(weeks):
        return [_norm_fixture(x) for x in weeks[week_idx-1]]
    fixtures = getattr(car, "fixtures", [])
    out: List[Dict[str, Any]] = []
    for f in fixtures:
        w = f.get("week") if isinstance(f, dict) else None
        if w == week_idx: out.append(_norm_fixture(f))
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
        wmax = getattr(car, "week", 1)
        weeks = getattr(car, "fixtures_by_week", [])
        total_weeks = len(weeks) if weeks else wmax
        for w in range(1, min(wmax, total_weeks)+1):
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
        table = []
        for tid, s in car.standings.items():
            s["gd"] = s["gf"] - s["ga"]
            table.append(s)
        table.sort(key=lambda r: (r["pts"], r["gd"], r["gf"]), reverse=True)
        car.table_sorted = table
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

    def enter(self):
        w, h = self.app.screen.get_size()
        pad = 16
        self.rect_header = pygame.Rect(pad, pad, w - pad*2, 48)
        self.rect_left   = pygame.Rect(pad, self.rect_header.bottom + pad, int(w * 0.62) - pad, h - (self.rect_header.bottom + pad*2))
        self.rect_right  = pygame.Rect(self.rect_left.right + pad, self.rect_left.y, w - (self.rect_left.right + pad*2), self.rect_left.h)

        # Buttons
        bx = self.rect_right.x + 12
        by = self.rect_right.y + 12
        bw, bh, gap = self.rect_right.w - 24, 48, 12

        def add(label, cb, disabled=False):
            nonlocal by
            b = Button(pygame.Rect(bx, by, bw, bh), label, cb, disabled=disabled)
            self.btns.append(b); by += (bh + gap)

        add("Play", self._play)
        add("Sim Week", self._sim_week)
        add("Schedule", self._go_schedule)
        add("Table", self._go_table)
        add("Roster", self._go_roster)
        add("Season Statistics", lambda: None)  # unwired for now
        add("Save", lambda: None)               # unwired for now
        add("Back", self._back)

    def handle(self, ev: pygame.event.Event):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE): self._back(); return
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):  self._play(); return
        for b in self.btns:
            b.handle(ev)

    def update(self, dt: float):
        self.week = int(getattr(self.career, "week", self.week) or self.week)

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

        # left: this week's games
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
            score = ""
            if fx["played"] and fx["sh"] is not None and fx["sa"] is not None:
                score = f"—  {fx['sh']} - {fx['sa']}"
            label = f"{hname}  vs  {aname}   {score}"
            surf = self.font.render(label, True, (230,230,235))
            screen.blit(surf, (lp.x + 12, y))
            y += line_h

        # right: buttons
        rp = self.rect_right
        pygame.draw.rect(screen, (42,44,52), rp, border_radius=12)
        pygame.draw.rect(screen, (24,24,28), rp, 2, border_radius=12)
        for b in self.btns:
            b.draw(screen, self.font)

    # ----- actions -----
    def _back(self): self.app.pop_state()

    def _play(self):
        """Open Tactics first; it will push MatchState afterward."""
        try:
            from ui.state_match_tactics import MatchTacticsState  # type: ignore
        except Exception:
            MatchTacticsState = None  # type: ignore

        # Find the user's current fixture this week
        user_tid = int(getattr(self.career, "user_tid", 0))
        week_fixtures = _fixtures_for_week(self.career, self.week)
        my = None
        for fx in week_fixtures:
            if int(fx["home"]) == user_tid or int(fx["away"]) == user_tid:
                my = fx; break
        if not my: return

        home, away = int(my["home"]), int(my["away"])
        fixture = {
            "home_id": home, "away_id": away,
            "home_tid": home, "away_tid": away,
            "A": home, "B": away,
            "week": self.week,
            "played": my["played"],
            "score_home": my["sh"], "score_away": my["sa"],
        }

        if MatchTacticsState is not None:
            try:
                self.app.push_state(MatchTacticsState(self.app, self.career, fixture))
                return
            except Exception:
                traceback.print_exc()

        # fallback straight to MatchState if tactics module missing
        try:
            from ui.state_match import MatchState  # type: ignore
            self.app.push_state(MatchState(self.app, self.career, fixture))
        except Exception:
            traceback.print_exc()

    def _sim_week(self):
        """Advance all fixtures for this week, then bump week and recompute standings."""
        used_native = False
        for name in ("sim_week", "simulate_week", "simulate_current_week", "sim_round"):
            fn = getattr(self.career, name, None)
            if callable(fn):
                try:
                    fn(); used_native = True
                except Exception:
                    traceback.print_exc()
                break

        if not used_native:
            try:
                rnd = random.Random(getattr(self.career, "seed", 1) + self.week * 777)
                week_fixtures = _fixtures_for_week(self.career, self.week)
                ovr_by_tid = {int(t["tid"]): _avg_ovr(t) for t in getattr(self.career, "teams", [])}
                for fx in week_fixtures:
                    if fx["played"]:  # already simmed
                        continue
                    h, a = int(fx["home"]), int(fx["away"])
                    hq = ovr_by_tid.get(h, 60.0)
                    aq = ovr_by_tid.get(a, 60.0)
                    hb = max(0.4, (hq - 40.0) / 25.0)
                    ab = max(0.4, (aq - 40.0) / 25.0)
                    sh = max(0, int(rnd.gauss(hb, 0.9)))
                    sa = max(0, int(rnd.gauss(ab, 0.9)))
                    if rnd.random() < 0.15: sh += 1  # home edge
                    _set_fixture_result(fx.get("_raw"), sh, sa)
                    fx["played"] = True; fx["sh"] = sh; fx["sa"] = sa
            except Exception:
                traceback.print_exc()

        # Advance week (don’t exceed available weeks)
        try:
            total_weeks = len(getattr(self.career, "fixtures_by_week", [])) or getattr(self.career, "total_weeks", 0)
            self.career.week = min(int(getattr(self.career, "week", 1)) + 1, total_weeks or 9999)
            self.week = int(self.career.week)
        except Exception:
            pass

        _recompute_standings(self.career)

    def _go_schedule(self):
        try:
            from ui.state_schedule import ScheduleState  # type: ignore
            self.app.push_state(ScheduleState(self.app, self.career))
        except Exception:
            traceback.print_exc()

    def _go_table(self):
        try:
            from ui.state_table import TableState  # type: ignore
            self.app.push_state(TableState(self.app, self.career))
        except Exception:
            traceback.print_exc()

    def _go_roster(self):
        try:
            from ui.state_roster_view import RosterViewState  # type: ignore
            self.app.push_state(RosterViewState(self.app, self.career))
        except Exception:
            traceback.print_exc()
