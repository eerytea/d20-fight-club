# core/career.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

# --- Shared adapters (normalize shapes) ---
try:
    from core.adapters import (
        as_fixture_dict,
        as_result_dict,
        team_name_from,
    )
except Exception:
    # Safe fallbacks if adapters module isn't present (should be replaced by real adapters)
    def as_fixture_dict(fx: Dict[str, Any]) -> Dict[str, Any]:
        d = dict(fx)
        d.setdefault("week", int(d.get("week", 1)))
        d.setdefault("home_id", int(d.get("home_id", d.get("home_tid", d.get("A", 0)))))
        d.setdefault("away_id", int(d.get("away_id", d.get("away_tid", d.get("B", 1)))))
        d.setdefault("played", bool(d.get("played", False)))
        d.setdefault("k_home", int(d.get("k_home", 0)))
        d.setdefault("k_away", int(d.get("k_away", 0)))
        d.setdefault("winner", d.get("winner", None))
        d.setdefault("comp_kind", d.get("comp_kind", "league"))
        d["home_tid"] = d["home_id"]; d["away_tid"] = d["away_id"]
        d["A"] = d["home_id"]; d["B"] = d["away_id"]
        return d

    def as_result_dict(r: Dict[str, Any]) -> Dict[str, Any]:
        d = dict(r)
        d["home_id"] = int(d.get("home_id", d.get("home_tid", d.get("A", 0))))
        d["away_id"] = int(d.get("away_id", d.get("away_tid", d.get("B", 1))))
        d["k_home"] = int(d.get("k_home", 0))
        d["k_away"] = int(d.get("k_away", 0))
        d["winner"] = d.get("winner", None)
        return d

    def team_name_from(career, tid: Any) -> str:
        tid_i = int(tid)
        for t in getattr(career, "teams", []):
            if int(t.get("tid", t.get("id", -999))) == tid_i:
                return t.get("name", f"Team {tid_i}")
        # map fallback
        tn = getattr(career, "team_names", None)
        if isinstance(tn, dict) and tid_i in tn:
            return str(tn[tid_i])
        return f"Team {tid_i}"

# --- Thin wrappers (single responsibility) ---
# schedule: fixtures_by_week in canonical fixture shape
# standings: sorted table rows in canonical standing shape
from core import schedule as _sched
from core import standings as _stand

# --- Integration points (Elo, staff/training, bootstrap) ---
try:
    from core.usecases.integration_points import (
        bootstrap_career,
        on_match_finalized,
        weekly_training_tick,
    )
except Exception:
    def bootstrap_career(*args, **kwargs):  # no-op if module not present
        pass
    def on_match_finalized(*args, **kwargs):
        pass
    def weekly_training_tick(*args, **kwargs):
        pass


# ---------------------------------------------------------------------------
# Small deterministic helpers (used for AI week sim scores)
# ---------------------------------------------------------------------------

def _mix_seed(seed: int, text: str) -> int:
    """Stable 64-bit mix so AI sims are reproducible."""
    x = (seed ^ 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    for ch in text.encode("utf-8"):
        x ^= (ch + 0x9E3779B97F4A7C15 + ((x << 6) & 0xFFFFFFFFFFFFFFFF) + (x >> 2))
        x &= 0xFFFFFFFFFFFFFFFF
    return x

def _deterministic_kills(seed: int, week: int, home_id: int, away_id: int) -> Tuple[int, int]:
    """Returns (k_home, k_away) in a small, stable range for the same inputs."""
    r = _mix_seed(seed, f"W{week}:{home_id}-{away_id}")
    k_home = (r >> 5) % 5 + ((r >> 17) & 1)   # 0..5
    k_away = (r >> 9) % 5 + ((r >> 19) & 1)   # 0..5
    return int(k_home), int(k_away)


# ---------------------------------------------------------------------------
# Career data model
# ---------------------------------------------------------------------------

@dataclass
class Career:
    """
    Holds teams, fixtures (by week + flat), current week, and standings.
    Uses one consistent shape everywhere so the UI/engine don’t guess key names.
    Can simulate AI vs AI weeks (your team’s match is left for you to play).
    """
    seed: int = 12345
    week: int = 1                      # Week is 1-based (Week 1, 2, 3, ...)
    user_tid: Optional[int] = 0

    # Teams: list of dicts like {"tid": int, "name": str, "fighters": [ {fighter fields...}, ... ]}
    teams: List[Dict[str, Any]] = field(default_factory=list)

    # Fixtures: canonical shape.
    fixtures_by_week: List[List[Dict[str, Any]]] = field(default_factory=list)
    fixtures: List[Dict[str, Any]] = field(default_factory=list)  # flattened

    # Standings: map tid -> row with keys {"tid","name","P","W","D","L","K","KD","PTS"}
    standings: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    # Optional: reputation/staff buckets added by bootstrap
    reputation: Optional[Dict[str, Any]] = None
    staff: Optional[Dict[str, Any]] = None

    # -----------------------------------------------------------------------
    # Construction
    # -----------------------------------------------------------------------

    @classmethod
    def new(
        cls,
        seed: int = 12345,
        n_teams: int = 20,
        team_size: int = 5,
        user_team_id: Optional[int] = 0,
        team_names: Optional[List[str]] = None,
    ) -> "Career":
        """
        Make a new career with:
          - n_teams simple teams with team_size fighters,
          - a double round-robin schedule (home/away twice),
          - standings initialized to zero,
          - bootstrap: reputation+staff seeded.
        """
        if not team_names:
            team_names = [f"Team {i}" for i in range(n_teams)]

        # Minimal teams (replace later with your generator)
        teams: List[Dict[str, Any]] = []
        for tid in range(n_teams):
            fighters = []
            for pid in range(team_size):
                fighters.append({
                    "pid": pid,
                    "name": f"P{pid}",
                    "team_id": 0,   # engine sets 0 for home / 1 for away at runtime
                    "hp": 10, "max_hp": 10, "ac": 10, "alive": True,
                    "STR": 10, "DEX": 10, "CON": 10, "INT": 8, "WIS": 8, "CHA": 8,
                })
            teams.append({"tid": tid, "name": team_names[tid], "fighters": fighters})

        # Fixtures in canonical shape via wrapper
        fixtures_by_week = _sched.fixtures_double_round_robin(n_teams, start_week=1, comp_kind="league")
        fixtures_flat = [fx for wk in fixtures_by_week for fx in wk]

        car = cls(
            seed=seed,
            week=1,
            user_tid=user_team_id,
            teams=teams,
            fixtures_by_week=fixtures_by_week,
            fixtures=fixtures_flat,
        )
        car._recompute_standings()

        # --- NEW: bootstrap Elo/staff so they're always present
        try:
            bootstrap_career(car)
        except Exception:
            pass

        return car

    # -----------------------------------------------------------------------
    # Basic helpers for UI
    # -----------------------------------------------------------------------

    @property
    def week_index(self) -> int:
        """0-based index for arrays. Week 1 -> 0."""
        return max(0, int(self.week) - 1)

    def team_name(self, tid: Any) -> str:
        """Safe name lookup (used by UI)."""
        return team_name_from(self, tid)

    def fixtures_for_week(self, w: int) -> List[Dict[str, Any]]:
        """Return canonical fixtures for 1-based week w."""
        if 1 <= w <= len(self.fixtures_by_week):
            return [as_fixture_dict(fx) for fx in self.fixtures_by_week[w - 1]]
        return []

    # -----------------------------------------------------------------------
    # Save / Load
    # -----------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Career":
        """
        Forgiving load: assumes dict matches fields; if structure drifted,
        external migrator should adapt. We also:
          - recompute standings (in case),
          - bootstrap reputation/staff to guarantee availability.
        """
        obj = cls(**d)
        try:
            # Normalize fixtures list if empty but we have per-week
            if not obj.fixtures and obj.fixtures_by_week:
                obj.fixtures = [fx for wk in obj.fixtures_by_week for fx in wk]
            obj._recompute_standings()
        finally:
            # Ensure Elo/staff tables exist on old saves
            try:
                bootstrap_career(obj)
            except Exception:
                pass
        return obj

    # -----------------------------------------------------------------------
    # Standings
    # -----------------------------------------------------------------------

    def table_rows(self) -> List[Dict[str, Any]]:
        """Unsorted copy (handy for debugging)."""
        return [dict(v) for _, v in sorted(self.standings.items(), key=lambda kv: int(kv[0]))]

    def table_rows_sorted(self) -> List[Dict[str, Any]]:
        """Sorted rows via the wrapper (PTS → KD → H2H → K)."""
        return _stand.table_rows_sorted(self.teams, self.fixtures)

    def _recompute_standings(self) -> None:
        """Rebuild standings from fixtures via the wrapper, store as a dict map by tid."""
        rows = _stand.table_rows_sorted(self.teams, self.fixtures)
        self.standings = {row["tid"]: row for row in rows}

    # -----------------------------------------------------------------------
    # Recording results
    # -----------------------------------------------------------------------

    def record_result(self, result: Dict[str, Any]) -> None:
        """
        Persist a finished match into fixtures and update standings.
        Expected keys (canonical): home_id, away_id, k_home, k_away, winner.
        """
        r = as_result_dict(result)
        h = int(r["home_id"]); a = int(r["away_id"])
        kh = int(r["k_home"]);  ka = int(r["k_away"])
        w  = r.get("winner", None)  # 0 / 1 / None

        # Find the first matching, unplayed fixture (prefer current week)
        fx = self._find_unplayed_fixture(h, a)
        if fx is None:
            # Failsafe: create one in the current week
            fx = {
                "week": self.week, "home_id": h, "away_id": a,
                "played": False, "k_home": 0, "k_away": 0, "winner": None, "comp_kind": "league",
                "home_tid": h, "away_tid": a, "A": h, "B": a,
            }
            self.fixtures.append(fx)
            while len(self.fixtures_by_week) < self.week:
                self.fixtures_by_week.append([])
            self.fixtures_by_week[self.week - 1].append(fx)

        fx["played"] = True
        fx["k_home"] = kh
        fx["k_away"] = ka
        fx["winner"] = w

        self._recompute_standings()

        # Optional: reputation update (club Elo)
        try:
            on_match_finalized(self, str(h), str(a), kh, ka, comp_kind=fx.get("comp_kind", "league"), home_advantage="a")
        except Exception:
            pass

    # Back-compat names some code may call
    def save_match_result(self, result: Dict[str, Any]) -> None:
        self.record_result(result)
    def apply_result(self, result: Dict[str, Any]) -> None:
        self.record_result(result)

    def _find_unplayed_fixture(self, home_id: int, away_id: int) -> Optional[Dict[str, Any]]:
        """Look for a matching, unplayed fixture (current week first, then anywhere)."""
        if 1 <= self.week <= len(self.fixtures_by_week):
            for fx in self.fixtures_by_week[self.week - 1]:
                if int(fx["home_id"]) == home_id and int(fx["away_id"]) == away_id and not fx.get("played"):
                    return fx
        for fx in self.fixtures:
            if int(fx["home_id"]) == home_id and int(fx["away_id"]) == away_id and not fx.get("played"):
                return fx
        return None

    # -----------------------------------------------------------------------
    # Simulate a week (AI vs AI only)
    # -----------------------------------------------------------------------

    def simulate_week_ai(self) -> None:
        """
        Sim all AI-vs-AI fixtures in the current week.
        Your team’s match is left unplayed so you can play it.
        After sim, a small training tick runs for each club (if wired).
        If all fixtures for this week are played, the week advances.
        """
        if not (1 <= self.week <= len(self.fixtures_by_week)):
            return

        week_fixtures = self.fixtures_by_week[self.week - 1]
        for fx in week_fixtures:
            if fx.get("played"):
                continue
            h = int(fx["home_id"]); a = int(fx["away_id"])
            # Skip user's fixture
            if self.user_tid is not None and (str(h) == str(self.user_tid) or str(a) == str(self.user_tid)):
                continue

            kh, ka = _deterministic_kills(self.seed, int(self.week), h, a)
            w = 0 if kh > ka else (1 if ka > kh else None)
            self.record_result({"home_id": h, "away_id": a, "k_home": kh, "k_away": ka, "winner": w})

        # Tiny training tick (coaches) — optional
        try:
            players_by_club: Dict[str, List[Dict[str, Any]]] = {}
            for t in self.teams:
                tid = str(t.get("tid"))
                roster = t.get("fighters") or t.get("players") or []
                players_by_club[tid] = roster
            # default focus if you don't have per-player focus yet
            focus_per_player: Dict[str, Dict[str, float]] = {}
            for tid, plist in players_by_club.items():
                for p in plist:
                    pid = str(p.get("pid", p.get("id", 0)))
                    if pid not in focus_per_player:
                        focus_per_player[pid] = {"DEX": 0.5, "STR": 0.5}
            for tid, plist in players_by_club.items():
                weekly_training_tick(self, tid, plist, focus_per_player)
        except Exception:
            pass

        # Advance week if everything is played
        if all(fx.get("played") for fx in week_fixtures) and week_fixtures:
            self.advance_week()

    # -----------------------------------------------------------------------
    # Week advance
    # -----------------------------------------------------------------------

    def advance_week(self) -> None:
        self.week = int(self.week) + 1

    # Alias some UIs call
    def next_week(self) -> None:
        self.advance_week()
