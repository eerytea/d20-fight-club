# core/career.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from datetime import date

# --- Local lightweight types -------------------------------------------------

@dataclass
class Fixture:
    week: int                 # 1-based
    home_id: int
    away_id: int
    played: bool = False
    k_home: int = 0
    k_away: int = 0
    winner: Optional[int] = None  # 0=home, 1=away, None=draw
    comp_kind: str = "league"     # "league"|"cup"|...

    # UI/test-friendly aliases (read-only properties)
    @property
    def home_tid(self) -> int: return self.home_id
    @property
    def away_tid(self) -> int: return self.away_id
    @property
    def A(self) -> int: return self.home_id
    @property
    def B(self) -> int: return self.away_id

# --- Utility: deterministic small-score generator ---------------------------

def _mix_seed(seed: int, a: str) -> int:
    # Very simple 64-bit mix; stable across runs
    x = (seed ^ 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    for ch in a.encode("utf-8"):
        x ^= ch + 0x9E3779B97F4A7C15 + ((x << 6) & 0xFFFFFFFFFFFFFFFF) + (x >> 2)
        x &= 0xFFFFFFFFFFFFFFFF
    return x

def _deterministic_kills(seed: int, week: int, home_id: int, away_id: int) -> Tuple[int, int]:
    ident = f"W{week}:{home_id}-{away_id}"
    r = _mix_seed(seed, ident)
    k_home = (r >> 5) % 5 + ((r >> 17) & 1)   # 0..5
    k_away = (r >> 9) % 5 + ((r >> 19) & 1)   # 0..5
    return int(k_home), int(k_away)

# --- Career data model -------------------------------------------------------

@dataclass
class Career:
    seed: int = 12345
    week: int = 1                                   # 1-based
    user_tid: Optional[int] = 0
    teams: List[Dict[str, Any]] = field(default_factory=list)
    fixtures_by_week: List[List[Dict[str, Any]]] = field(default_factory=list)
    fixtures: List[Dict[str, Any]] = field(default_factory=list)
    # standings keyed by tid
    standings: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    # ---------- construction ----------
    @classmethod
    def new(cls,
            seed: int = 12345,
            n_teams: int = 20,
            team_size: int = 5,
            user_team_id: Optional[int] = 0,
            team_names: Optional[List[str]] = None) -> "Career":
        # Team names fallback
        if not team_names:
            team_names = [f"Team {i}" for i in range(n_teams)]
        teams: List[Dict[str, Any]] = []
        for tid in range(n_teams):
            fighters = []
            for pid in range(team_size):
                fighters.append({
                    "pid": pid,
                    "name": f"P{pid}",
                    "team_id": 0,  # set dynamically in match builder
                    "hp": 10,
                    "max_hp": 10,
                    "ac": 10,
                    "alive": True,
                    "STR": 10, "DEX": 10, "CON": 10, "INT": 8, "WIS": 8, "CHA": 8,
                })
            teams.append({"tid": tid, "name": team_names[tid], "fighters": fighters})

        # Build double round-robin fixtures
        # circle method
        ids = list(range(n_teams))
        if n_teams % 2 == 1:
            ids.append(-1)
        n = len(ids)
        half = n // 2
        arr = ids[:]
        weeks_pairs: List[List[Tuple[int,int]]] = []
        for _ in range(n-1):
            week_pairs: List[Tuple[int,int]] = []
            for i in range(half):
                t1, t2 = arr[i], arr[n-1-i]
                if t1 != -1 and t2 != -1:
                    week_pairs.append((t1, t2))
            weeks_pairs.append(week_pairs)
            arr = [arr[0]] + [arr[-1]] + arr[1:-1]
        # double round robin: add reversed fixtures after first leg
        all_weeks: List[List[Tuple[int,int]]] = []
        all_weeks.extend(weeks_pairs)
        all_weeks.extend([(b,a) for (a,b) in wp] for wp in weeks_pairs)

        fixtures_by_week: List[List[Dict[str, Any]]] = []
        for w, wp in enumerate(all_weeks, start=1):
            week_list: List[Dict[str, Any]] = []
            for (a,b) in wp:
                week_list.append({"week": w, "home_id": a, "away_id": b, "played": False, "comp_kind": "league"})
            fixtures_by_week.append(week_list)
        fixtures_flat = [fx for week in fixtures_by_week for fx in week]

        car = cls(seed=seed, week=1, user_tid=user_team_id, teams=teams,
                  fixtures_by_week=fixtures_by_week, fixtures=fixtures_flat)
        car._recompute_standings()
        return car

    # ---------- helpers for UI ----------
    def team_name(self, tid: Any) -> str:
        try_tid = str(tid)
        for t in self.teams:
            if str(t.get("tid", t.get("id"))) == try_tid:
                return t.get("name", f"Team {tid}")
        # fallback mapping
        mapping = getattr(self, "team_names", None)
        if isinstance(mapping, dict) and try_tid in mapping:
            return str(mapping[try_tid])
        if isinstance(mapping, list):
            try:
                i = int(try_tid)
                return mapping[i]
            except Exception:
                pass
        return f"Team {tid}"

    # ---------- persistence-ish ----------
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Career":
        # lenient load
        return cls(**d)

    # ---------- standings view ----------
    def table_rows(self) -> List[Dict[str, Any]]:
        return [dict(v) for _, v in sorted(self.standings.items(), key=lambda kv: int(kv[0]))]

    def table_rows_sorted(self) -> List[Dict[str, Any]]:
        rows = list(self.standings.values())
        rows.sort(key=lambda r: (r["PTS"], r["KD"], r["K"]), reverse=True)
        return [dict(r) for r in rows]

    # ---------- results & standings ----------
    def record_result(self, result: Dict[str, Any]) -> None:
        """Persist a finished match and update standings.
        Expected result keys: home_tid, away_tid, K_home, K_away, winner
        """
        h = int(result.get("home_tid") or result.get("home_id"))
        a = int(result.get("away_tid") or result.get("away_id"))
        kh = int(result.get("K_home", result.get("k_home", 0)))
        ka = int(result.get("K_away", result.get("k_away", 0)))
        w = result.get("winner", None)
        # Mark fixture
        fx = self._find_fixture(h, a)
        if fx is None:
            # create ad-hoc fixture in current week (failsafe)
            fx = {"week": self.week, "home_id": h, "away_id": a, "played": False, "comp_kind": "league"}
            self.fixtures.append(fx)
            while len(self.fixtures_by_week) < self.week:
                self.fixtures_by_week.append([])
            self.fixtures_by_week[self.week-1].append(fx)
        fx["played"] = True
        fx["k_home"] = kh
        fx["k_away"] = ka
        fx["winner"] = w
        self._recompute_standings()

    # alias names some code might call
    def save_match_result(self, result: Dict[str, Any]) -> None:
        self.record_result(result)
    def apply_result(self, result: Dict[str, Any]) -> None:
        self.record_result(result)

    def _find_fixture(self, home_id: int, away_id: int) -> Optional[Dict[str, Any]]:
        # search current week first
        for fx in self.fixtures_by_week[self.week-1] if 0 <= self.week-1 < len(self.fixtures_by_week) else []:
            if int(fx.get("home_id")) == home_id and int(fx.get("away_id")) == away_id:
                return fx
        # search all
        for fx in self.fixtures:
            if int(fx.get("home_id")) == home_id and int(fx.get("away_id")) == away_id:
                return fx
        return None

    def _recompute_standings(self) -> None:
        # initialize
        table: Dict[int, Dict[str, Any]] = {int(t["tid"]): {"tid": int(t["tid"]), "name": self.team_name(t["tid"]),
                                                            "P": 0, "W": 0, "D": 0, "L": 0,
                                                            "K": 0, "KD": 0, "PTS": 0}
                                            for t in self.teams}
        # accumulate from played fixtures
        for fx in self.fixtures:
            if not fx.get("played"):
                continue
            h, a = int(fx["home_id"]), int(fx["away_id"])
            kh, ka = int(fx.get("k_home", 0)), int(fx.get("k_away", 0))
            w = fx.get("winner")
            th = table[h]; ta = table[a]
            th["P"] += 1; ta["P"] += 1
            th["K"] += kh; ta["K"] += ka
            th["KD"] += (kh - ka); ta["KD"] += (ka - kh)
            if w == 0: th["W"] += 1; ta["L"] += 1; th["PTS"] += 3
            elif w == 1: ta["W"] += 1; th["L"] += 1; ta["PTS"] += 3
            else: th["D"] += 1; ta["D"] += 1; th["PTS"] += 1; ta["PTS"] += 1
        self.standings = table

    # ---------- sim week ----------
    def simulate_week_ai(self) -> None:
        """Sim AI-vs-AI fixtures for the current week; leave the user's match unplayed."""
        this_week = [fx for fx in self.fixtures_by_week[self.week-1]] if 0 <= self.week-1 < len(self.fixtures_by_week) else []
        for fx in this_week:
            if fx.get("played"):
                continue
            # Skip user team's fixture so they can play it
            if self.user_tid is not None and (str(fx["home_id"]) == str(self.user_tid) or str(fx["away_id"]) == str(self.user_tid)):
                continue
            kh, ka = _deterministic_kills(self.seed, int(fx["week"]), int(fx["home_id"]), int(fx["away_id"]))
            w = 0 if kh > ka else (1 if ka > kh else None)
            self.record_result({"home_tid": fx["home_id"], "away_tid": fx["away_id"], "K_home": kh, "K_away": ka, "winner": w})
        # If all fixtures of this week are played, advance
        if all(fx.get("played") for fx in this_week) and this_week:
            self.advance_week()

    # ---------- week advance ----------
    def advance_week(self) -> None:
        self.week = int(self.week) + 1

    # Optional back-compat names some UIs call
    def next_week(self) -> None:
        self.advance_week()
