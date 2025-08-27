# core/career.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

# Adapters: one place to normalize shapes
from core.adapters import (
    as_fixture_dict,
    as_result_dict,
    team_name_from,
    roster_for_team,
)

# Optional hooks (safe no-ops if not present)
try:
    from core.usecases.integration_points import on_match_finalized, weekly_training_tick
except Exception:  # keep the game running even if glue isn't wired yet
    def on_match_finalized(*args, **kwargs):
        pass
    def weekly_training_tick(*args, **kwargs):
        pass


# --------------------------
# Small helpers (deterministic)
# --------------------------

def _mix_seed(seed: int, text: str) -> int:
    """Stable 64-bit hash mix used for deterministic sim scores."""
    x = (seed ^ 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    for ch in text.encode("utf-8"):
        x ^= (ch + 0x9E3779B97F4A7C15 + ((x << 6) & 0xFFFFFFFFFFFFFFFF) + (x >> 2))
        x &= 0xFFFFFFFFFFFFFFFF
    return x

def _deterministic_kills(seed: int, week: int, home_id: int, away_id: int) -> Tuple[int, int]:
    """Returns (k_home, k_away) in a small range, but stable for the same inputs."""
    r = _mix_seed(seed, f"W{week}:{home_id}-{away_id}")
    k_home = (r >> 5) % 5 + ((r >> 17) & 1)   # 0..5
    k_away = (r >> 9) % 5 + ((r >> 19) & 1)   # 0..5
    return int(k_home), int(k_away)

def _build_double_round_robin(n_teams: int) -> List[List[Tuple[int, int]]]:
    """
    Returns a list of weeks. Each week is a list of pairs (home_id, away_id).
    It uses the "circle method" and then mirrors for the second leg.
    """
    ids = list(range(n_teams))
    if n_teams % 2 == 1:
        ids.append(-1)  # bye marker
    n = len(ids)
    half = n // 2
    arr = ids[:]

    first_leg: List[List[Tuple[int, int]]] = []
    for _ in range(n - 1):
        week_pairs: List[Tuple[int, int]] = []
        for i in range(half):
            a, b = arr[i], arr[n - 1 - i]
            if a != -1 and b != -1:
                week_pairs.append((a, b))  # a is home, b is away
        first_leg.append(week_pairs)
        # rotate (keep first in place)
        arr = [arr[0]] + [arr[-1]] + arr[1:-1]

    # second leg: swap home/away for each pair, same order of weeks
    second_leg = [[(b, a) for (a, b) in week] for week in first_leg]
    return first_leg + second_leg


# --------------------------
# Data model
# --------------------------

@dataclass
class Career:
    """
    Plain-English version:
      - Holds teams, fixtures, current week, and the standings table.
      - Gives helper functions the UI needs (team name, table rows).
      - Can simulate a week for AI teams (your team is left for you to play).
    """
    seed: int = 12345
    week: int = 1                         # 1-based week
    user_tid: Optional[int] = 0

    # Teams are dicts like: {"tid": int, "name": str, "fighters": [FighterDict, ...]}
    teams: List[Dict[str, Any]] = field(default_factory=list)

    # Fixtures are stored both per-week and flat. Keys are normalized everywhere.
    fixtures_by_week: List[List[Dict[str, Any]]] = field(default_factory=list)
    fixtures: List[Dict[str, Any]] = field(default_factory=list)

    # Standings map by tid -> row
    # row keys: tid, name, P, W, D, L, K, KD, PTS
    standings: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    # -------------- Construction --------------

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
        Create a new career with:
          - n_teams teams with simple default fighters,
          - a double round-robin schedule,
          - week = 1, standings initialized to zeros.
        """
        if not team_names:
            team_names = [f"Team {i}" for i in range(n_teams)]

        # Build minimal teams (fighters are simple; you can swap in your generator later)
        teams: List[Dict[str, Any]] = []
        for tid in range(n_teams):
            fighters = []
            for pid in range(team_size):
                fighters.append({
                    "pid": pid,
                    "name": f"P{pid}",
                    "team_id": 0,       # the engine will set 0 for home / 1 for away at runtime
                    "hp": 10,
                    "max_hp": 10,
                    "ac": 10,
                    "alive": True,
                    "STR": 10, "DEX": 10, "CON": 10, "INT": 8, "WIS": 8, "CHA": 8,
                })
            teams.append({"tid": tid, "name": team_names[tid], "fighters": fighters})

        # Fixtures: double round robin, normalized shape
        weeks = _build_double_round_robin(n_teams)
        fixtures_by_week: List[List[Dict[str, Any]]] = []
        for w, pairs in enumerate(weeks, start=1):
            wk: List[Dict[str, Any]] = []
            for (home, away) in pairs:
                fx = {
                    "week": w, "home_id": int(home), "away_id": int(away),
                    "played": False, "k_home": 0, "k_away": 0,
                    "winner": None, "comp_kind": "league",
                }
                # add common aliases some UIs read
                fx["home_tid"] = fx["home_id"]
                fx["away_tid"] = fx["away_id"]
                fx["A"] = fx["home_id"]
                fx["B"] = fx["away_id"]
                wk.append(fx)
            fixtures_by_week.append(wk)

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
        return car

    # -------------- Basic helpers for UI --------------

    @property
    def week_index(self) -> int:
        """0-based index (useful for arrays). Week 1 -> index 0."""
        return max(0, int(self.week) - 1)

    def team_name(self, tid: Any) -> str:
        """Safe team name lookup used everywhere."""
        return team_name_from(self, tid)

    def fixtures_for_week(self, w: int) -> List[Dict[str, Any]]:
        """Return fixtures list (normalized) for 1-based week w."""
        if 1 <= w <= len(self.fixtures_by_week):
            return [as_fixture_dict(fx) for fx in self.fixtures_by_week[w - 1]]
        return []

    # -------------- Save/load (optional) --------------

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Career":
        # forgiving load: if keys differ, Python will raise, but we try to pass most through
        return cls(**d)

    # -------------- Standings --------------

    def table_rows(self) -> List[Dict[str, Any]]:
        """Unsorted rows (handy for debugging)."""
        return [dict(v) for _, v in sorted(self.standings.items(), key=lambda kv: int(kv[0]))]

    def table_rows_sorted(self) -> List[Dict[str, Any]]:
        """
        Sort by PTS desc, then KD desc, then Head-to-Head points inside a tie group.
        If still tied, use total K desc as a last simple tie-breaker.
        """
        rows = list(self.standings.values())
        # primary sort
        rows.sort(key=lambda r: (r["PTS"], r["KD"], r["K"]), reverse=True)

        # h2h adjust within tie groups on (PTS, KD)
        # For each group, compute mini-table using only games among the tied teams.
        i = 0
        out = []
        while i < len(rows):
            j = i + 1
            while j < len(rows) and rows[j]["PTS"] == rows[i]["PTS"] and rows[j]["KD"] == rows[i]["KD"]:
                j += 1
            group = rows[i:j]
            if len(group) > 1:
                h2h_pts = self._head_to_head_points([g["tid"] for g in group])
                group.sort(key=lambda r: (h2h_pts.get(r["tid"], 0), r["K"]), reverse=True)
            out.extend(group)
            i = j
        return out

    def _head_to_head_points(self, tids: List[int]) -> Dict[int, int]:
        """
        Points from matches played only between the teams in 'tids'.
        3 for win, 1 for draw, 0 for loss.
        """
        s = {tid: 0 for tid in tids}
        for fx in self.fixtures:
            if not fx.get("played"):
                continue
            h = int(fx["home_id"]); a = int(fx["away_id"])
            if h in s and a in s:
                w = fx.get("winner", None)  # 0/1/None
                if w == 0:
                    s[h] += 3
                elif w == 1:
                    s[a] += 3
                else:
                    s[h] += 1; s[a] += 1
        return s

    def _recompute_standings(self) -> None:
        """Rebuild the standings table from all played fixtures."""
        table: Dict[int, Dict[str, Any]] = {
            int(t["tid"]): {
                "tid": int(t["tid"]),
                "name": self.team_name(t["tid"]),
                "P": 0, "W": 0, "D": 0, "L": 0,
                "K": 0, "KD": 0, "PTS": 0,
            }
            for t in self.teams
        }

        for fx in self.fixtures:
            if not fx.get("played"):
                continue
            h = int(fx["home_id"]); a = int(fx["away_id"])
            kh = int(fx.get("k_home", 0)); ka = int(fx.get("k_away", 0))
            w = fx.get("winner", None)  # 0/1/None

            th = table[h]; ta = table[a]
            th["P"] += 1; ta["P"] += 1
            th["K"] += kh; ta["K"] += ka
            th["KD"] += (kh - ka); ta["KD"] += (ka - kh)

            if w == 0:
                th["W"] += 1; th["PTS"] += 3
                ta["L"] += 1
            elif w == 1:
                ta["W"] += 1; ta["PTS"] += 3
                th["L"] += 1
            else:
                th["D"] += 1; ta["D"] += 1
                th["PTS"] += 1; ta["PTS"] += 1

        self.standings = table

    # -------------- Record results --------------

    def record_result(self, result: Dict[str, Any]) -> None:
        """
        Save a finished match into fixtures and update the standings.
        Expected keys (normalized for you): home_id, away_id, k_home, k_away, winner.
        """
        r = as_result_dict(result)
        h = int(r["home_id"]); a = int(r["away_id"])
        kh = int(r["k_home"]);  ka = int(r["k_away"])
        w  = r.get("winner", None)

        # Find the first matching, unplayed fixture (current week first, then all)
        fx = self._find_unplayed_fixture(h, a)
        if fx is None:
            # If not found, create one in the current week (failsafe)
            fx = {
                "week": self.week, "home_id": h, "away_id": a,
                "played": False, "k_home": 0, "k_away": 0, "winner": None, "comp_kind": "league"
            }
            fx["home_tid"] = h; fx["away_tid"] = a; fx["A"] = h; fx["B"] = a
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

    # alias names that other modules might call
    def save_match_result(self, result: Dict[str, Any]) -> None:
        self.record_result(result)
    def apply_result(self, result: Dict[str, Any]) -> None:
        self.record_result(result)

    def _find_unplayed_fixture(self, home_id: int, away_id: int) -> Optional[Dict[str, Any]]:
        # Look in current week first
        if 1 <= self.week <= len(self.fixtures_by_week):
            for fx in self.fixtures_by_week[self.week - 1]:
                if (int(fx["home_id"]) == home_id and int(fx["away_id"]) == away_id and not fx.get("played")):
                    return fx
        # Then search all
        for fx in self.fixtures:
            if int(fx["home_id"]) == home_id and int(fx["away_id"]) == away_id and not fx.get("played"):
                return fx
        return None

    # -------------- Sim week (AI vs AI) --------------

    def simulate_week_ai(self) -> None:
        """
        Simulate only AI vs AI fixtures in the current week.
        Your team's fixture is left unplayed so you can play it.
        After sim, a small training tick runs for each club (if the hook exists).
        """
        if not (1 <= self.week <= len(self.fixtures_by_week)):
            return

        week_fixtures = self.fixtures_by_week[self.week - 1]
        for fx in week_fixtures:
            if fx.get("played"):
                continue
            h = int(fx["home_id"]); a = int(fx["away_id"])

            # Skip user's game
            if self.user_tid is not None and (str(h) == str(self.user_tid) or str(a) == str(self.user_tid)):
                continue

            kh, ka = _deterministic_kills(self.seed, int(self.week), h, a)
            w = 0 if kh > ka else (1 if ka > kh else None)
            self.record_result({"home_id": h, "away_id": a, "k_home": kh, "k_away": ka, "winner": w})

        # Training tick (coaches influence) — safe to ignore if not wired
        try:
            # Build per-club lists and default focus
            players_by_club: Dict[str, List[Dict[str, Any]]] = {}
            for t in self.teams:
                tid = str(t.get("tid"))
                roster = t.get("fighters") or t.get("players") or []
                players_by_club[tid] = roster
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

        # If everything this week is played, advance the week
        if all(fx.get("played") for fx in week_fixtures) and week_fixtures:
            self.advance_week()

    # -------------- Week advance --------------

    def advance_week(self) -> None:
        self.week = int(self.week) + 1

    # Some UIs call this name
    def next_week(self) -> None:
        self.advance_week()
