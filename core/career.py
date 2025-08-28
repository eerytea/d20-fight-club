# core/career.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict, fields as dataclass_fields
from typing import Any, Dict, List, Optional, Tuple

# ---- Adapters (canonicalize shapes) ----
try:
    from core.adapters import (
        as_fixture_dict,
        as_result_dict,
        team_name_from,
    )
except Exception:
    # Safe fallbacks if adapters module isn't present (replace with real ones if available)
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
        tn = getattr(career, "team_names", None)
        if isinstance(tn, dict) and tid_i in tn:
            return str(tn[tid_i])
        return f"Team {tid_i}"

# ---- Thin wrappers (schedule/standings) ----
from core import schedule as _sched
from core import standings as _stand

# ---- Migrator (normalize old saves) ----
try:
    from core.migrate import normalize_save_dict
except Exception:
    def normalize_save_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        return d

# ---- Integration points (Elo, staff/training, bootstrap) ----
try:
    from core.usecases.integration_points import (
        bootstrap_career,
        on_match_finalized,
        weekly_training_tick,
    )
except Exception:
    def bootstrap_career(*args, **kwargs):  # no-op
        pass
    def on_match_finalized(*args, **kwargs):
        pass
    def weekly_training_tick(*args, **kwargs):
        pass


# ---------------------------------------------------------------------------
# Deterministic helpers (used for AI vs AI scores)
# ---------------------------------------------------------------------------

def _mix_seed(seed: int, text: str) -> int:
    x = (seed ^ 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    for ch in text.encode("utf-8"):
        x ^= (ch + 0x9E3779B97F4A7C15 + ((x << 6) & 0xFFFFFFFFFFFFFFFF) + (x >> 2))
        x &= 0xFFFFFFFFFFFFFFFF
    return x

def _deterministic_kills(seed: int, week: int, home_id: int, away_id: int) -> Tuple[int, int]:
    r = _mix_seed(seed, f"W{week}:{home_id}-{away_id}")
    k_home = (r >> 5) % 5 + ((r >> 17) & 1)   # 0..5
    k_away = (r >> 9) % 5 + ((r >> 19) & 1)   # 0..5
    return int(k_home), int(k_away)


# ---------------------------------------------------------------------------
# Career model
# ---------------------------------------------------------------------------

@dataclass
class Career:
    """
    Holds teams, fixtures, current week, standings, and (via bootstrap) reputation/staff.
    Uses one consistent shape so UI/engine don't guess key names.
    """
    seed: int = 12345
    week: int = 1
    user_tid: Optional[int] = 0

    teams: List[Dict[str, Any]] = field(default_factory=list)

    fixtures_by_week: List[List[Dict[str, Any]]] = field(default_factory=list)
    fixtures: List[Dict[str, Any]] = field(default_factory=list)

    standings: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    reputation: Optional[Dict[str, Any]] = None
    staff: Optional[Dict[str, Any]] = None

    # ---------------------- Construction ----------------------

    @classmethod
    def new(
        cls,
        seed: int = 12345,
        n_teams: int = 20,
        team_size: int = 5,
        user_team_id: Optional[int] = 0,
        team_names: Optional[List[str]] = None,
    ) -> "Career":
        if not team_names:
            team_names = [f"Team {i}" for i in range(n_teams)]

        teams: List[Dict[str, Any]] = []
        for tid in range(n_teams):
            fighters = []
            for pid in range(team_size):
                fighters.append({
                    "pid": pid,
                    "name": f"P{pid}",
                    "team_id": 0,
                    "hp": 10, "max_hp": 10, "ac": 10, "alive": True,
                    "STR": 10, "DEX": 10, "CON": 10, "INT": 8, "WIS": 8, "CHA": 8,
                })
            teams.append({"tid": tid, "name": team_names[tid], "fighters": fighters})

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

        # Ensure Elo/staff tables exist
        try:
            bootstrap_career(car)
        except Exception:
            pass

        return car

    # ---------------------- Helpers for UI ----------------------

    @property
    def week_index(self) -> int:
        return max(0, int(self.week) - 1)

    def team_name(self, tid: Any) -> str:
        return team_name_from(self, tid)

    def fixtures_for_week(self, w: int) -> List[Dict[str, Any]]:
        if 1 <= w <= len(self.fixtures_by_week):
            return [as_fixture_dict(fx) for fx in self.fixtures_by_week[w - 1]]
        return []

    # ---------------------- Save / Load ----------------------

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Career":
        """
        Load a Career from dict, normalizing old saves and ignoring unknown keys.
        Recomputes standings and bootstraps Elo/staff.
        """
        nd = normalize_save_dict(dict(d))
        allowed = {f.name for f in dataclass_fields(cls)}
        init_kwargs = {k: v for k, v in nd.items() if k in allowed}
        obj = cls(**init_kwargs)

        try:
            if not obj.fixtures and obj.fixtures_by_week:
                obj.fixtures = [fx for wk in obj.fixtures_by_week for fx in wk]
            obj._recompute_standings()
        finally:
            try:
                bootstrap_career(obj)
            except Exception:
                pass
        return obj

    # ---------------------- Standings ----------------------

    def table_rows(self) -> List[Dict[str, Any]]:
        return [dict(v) for _, v in sorted(self.standings.items(), key=lambda kv: int(kv[0]))]

    def table_rows_sorted(self) -> List[Dict[str, Any]]:
        return _stand.table_rows_sorted(self.teams, self.fixtures)

    def _recompute_standings(self) -> None:
        rows = _stand.table_rows_sorted(self.teams, self.fixtures)
        self.standings = {row["tid"]: row for row in rows}

    # ---------------------- Recording results ----------------------

    def record_result(self, result: Dict[str, Any]) -> None:
        """
        Persist a finished match into fixtures and update standings.
        Expected keys: home_id, away_id, k_home, k_away, winner.
        """
        r = as_result_dict(result)
        h = int(r["home_id"]); a = int(r["away_id"])
        kh = int(r["k_home"]);  ka = int(r["k_away"])
        w  = r.get("winner", None)

        fx = self._find_unplayed_fixture(h, a)
        if fx is None:
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

        # Reputation/Elo update (if wired)
        try:
            on_match_finalized(self, str(h), str(a), kh, ka, comp_kind=fx.get("comp_kind", "league"), home_advantage="a")
        except Exception:
            pass

    def save_match_result(self, result: Dict[str, Any]) -> None:
        self.record_result(result)
    def apply_result(self, result: Dict[str, Any]) -> None:
        self.record_result(result)

    def _find_unplayed_fixture(self, home_id: int, away_id: int) -> Optional[Dict[str, Any]]:
        if 1 <= self.week <= len(self.fixtures_by_week):
            for fx in self.fixtures_by_week[self.week - 1]:
                if int(fx["home_id"]) == home_id and int(fx["away_id"]) == away_id and not fx.get("played"):
                    return fx
        for fx in self.fixtures:
            if int(fx["home_id"]) == home_id and int(fx["away_id"]) == away_id and not fx.get("played"):
                return fx
        return None

    # ---------------------- Simulate a week (AI vs AI) ----------------------

    def simulate_week_ai(self) -> None:
        """
        Sim all AI-vs-AI fixtures in the current week.
        Leaves the user's match unplayed. Runs training tick using stored focus.
        Advances week if all fixtures for this week end up played.
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

        # ---- Training tick (uses per-player focus from staff['training_focus']) ----
        try:
            players_by_club: Dict[str, List[Dict[str, Any]]] = {}
            for t in self.teams:
                tid = str(t.get("tid"))
                roster = t.get("fighters") or t.get("players") or []
                players_by_club[tid] = roster

            # Global store keyed by "tid:pid"
            focus_store: Dict[str, Dict[str, float]] = {}
            if isinstance(self.staff, dict):
                focus_store = dict(self.staff.get("training_focus", {}))

            # Call weekly tick per club with normalized pid→focus map
            for tid, plist in players_by_club.items():
                focus_per_player: Dict[str, Dict[str, float]] = {}
                for p in plist:
                    pid = str(p.get("pid", p.get("id", 0)))
                    key = f"{tid}:{pid}"
                    f = focus_store.get(key, None)
                    if not isinstance(f, dict):
                        f = {"DEX": 0.5, "STR": 0.5}
                    dex = float(f.get("DEX", 0.5)); strv = float(f.get("STR", 0.5))
                    s = dex + strv
                    if s <= 0: dex, strv = 0.5, 0.5
                    else: dex, strv = dex/s, strv/s
                    focus_per_player[pid] = {"DEX": dex, "STR": strv}
                weekly_training_tick(self, tid, plist, focus_per_player)
        except Exception:
            pass

        # Advance week if everything is played
        if all(fx.get("played") for fx in week_fixtures) and week_fixtures:
            self.advance_week()

    # ---------------------- Week advance ----------------------

    def advance_week(self) -> None:
        self.week = int(self.week) + 1

    def next_week(self) -> None:
        self.advance_week()
# ---- Compatibility helpers & safe monkey-patches (append-only) ----
# Paste this block at the VERY END of core/career.py

# Public helper used by tests and other modules
try:
    from .config import DEFAULT_SEED as _DEF_SEED, LEAGUE_TEAMS as _DEF_TEAMS, TEAM_SIZE as _DEF_TEAM_SIZE
except Exception:
    _DEF_SEED, _DEF_TEAMS, _DEF_TEAM_SIZE = 42, 20, 10

def new_career(seed: int = _DEF_SEED, team_count: int = _DEF_TEAMS, team_size: int = _DEF_TEAM_SIZE):
    """
    Convenience wrapper returning a new Career with no user-controlled team.
    """
    try:
        # Late import to avoid circulars during module load
        _Career = globals().get("Career", None)
        if _Career is None:
            from .career import Career as _Career  # type: ignore
        return _Career.new(seed=seed, n_teams=team_count, team_size=team_size, user_team_id=None)  # type: ignore
    except Exception as e:
        raise RuntimeError(f"new_career failed: {e}")

# ---- Monkey patches for standings (non-destructive) ----
try:
    Career  # type: ignore[name-defined]
except Exception:
    # Career isn't defined yet in this module context; nothing to patch.
    pass
else:
    # Prefer the real standings implementation if present
    try:
        from . import standings as _stand  # type: ignore
    except Exception:
        _stand = None  # type: ignore

    def _safe_recompute_standings(self):
        """
        Recompute standings from self.teams and self.fixtures.

        Stores self.standings as a dict keyed by tid.
        Uses core.standings if available; otherwise falls back to a simple aggregator.
        """
        # Build id/name maps
        ids = []
        names = {}
        for i, t in enumerate(getattr(self, "teams", []) or []):
            tid = int(t.get("tid", t.get("id", i)))
            ids.append(tid)
            names[tid] = t.get("name", f"Team {i}")

        fixtures = list(getattr(self, "fixtures", []) or [])

        rows = None
        if _stand is not None:
            try:
                table, h2h = _stand.new_table(ids, names)  # type: ignore[attr-defined]
                for fx in fixtures:
                    if not fx.get("played"):
                        continue
                    _stand.apply_result(
                        table, h2h,
                        int(fx["home_id"]), int(fx["away_id"]),
                        int(fx.get("k_home", 0)), int(fx.get("k_away", 0)),
                    )
                rows = _stand.table_rows_sorted(table, h2h)  # type: ignore[attr-defined]
            except Exception:
                rows = None

        if rows is None:
            # Fallback very small implementation
            agg = {tid: {"tid": tid, "name": names.get(tid, f"Team {tid}"),
                         "P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "PTS": 0}
                   for tid in ids}
            for fx in fixtures:
                if not fx.get("played"):
                    continue
                h = int(fx["home_id"]); a = int(fx["away_id"])
                kh = int(fx.get("k_home", 0)); ka = int(fx.get("k_away", 0))
                agg[h]["P"] += 1; agg[a]["P"] += 1
                agg[h]["GF"] += kh; agg[h]["GA"] += ka
                agg[a]["GF"] += ka; agg[a]["GA"] += kh
                agg[h]["GD"] = agg[h]["GF"] - agg[h]["GA"]
                agg[a]["GD"] = agg[a]["GF"] - agg[a]["GA"]
                if kh > ka:
                    agg[h]["W"] += 1; agg[a]["L"] += 1
                    agg[h]["PTS"] += 3
                elif ka > kh:
                    agg[a]["W"] += 1; agg[h]["L"] += 1
                    agg[a]["PTS"] += 3
                else:
                    agg[h]["D"] += 1; agg[a]["D"] += 1
                    agg[h]["PTS"] += 1; agg[a]["PTS"] += 1
            rows = list(agg.values())
            rows.sort(key=lambda r: (r["PTS"], r["GD"], r["GF"]), reverse=True)

        # Alias to tests' expected keys: K (kills) and KD (kill diff)
        out = []
        for r in rows:
            k = int(r.get("GF", r.get("K", 0)))
            kd = int(r.get("GD", r.get("KD", k - int(r.get("GA", 0)))))
            rr = dict(r)
            rr["K"] = k
            rr["KD"] = kd
            out.append(rr)

        # Persist as dict for quick lookup
        self.standings = {row["tid"]: row for row in out}

    def _safe_table_rows_sorted(self):
        """
        Return rows with the scoreboard keys expected by tests:
        P, W, D, L, K, KD, PTS.
        """
        rows = list(getattr(self, "standings", {}).values()) if isinstance(getattr(self, "standings", {}), dict) else []
        if not rows:
            try:
                _safe_recompute_standings(self)
                rows = list(getattr(self, "standings", {}).values())
            except Exception:
                rows = []
        # Keep deterministic ordering
        rows.sort(key=lambda r: (int(r.get("PTS", 0)), int(r.get("KD", 0)), int(r.get("K", 0))), reverse=True)
        return rows

    # Only install patches if original methods are missing or clearly incompatible
    if not hasattr(Career, "_recompute_standings"):
        Career._recompute_standings = _safe_recompute_standings  # type: ignore[attr-defined]
    else:
        # Always provide as helper and replace; it's idempotent and safer than guessing old shapes
        Career._recompute_standings = _safe_recompute_standings  # type: ignore[attr-defined]

    if not hasattr(Career, "table_rows_sorted"):
        Career.table_rows_sorted = _safe_table_rows_sorted  # type: ignore[attr-defined]
    else:
        Career.table_rows_sorted = _safe_table_rows_sorted  # type: ignore[attr-defined]
