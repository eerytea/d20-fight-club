# core/sim.py
from __future__ import annotations

from typing import Dict, Optional, Any, Callable
import random

from .config import TURN_LIMIT
from .career import Career, Fixture
from .rng import mix

# --- Deterministic per-fixture seed ------------------------------------------

def _fixture_seed(career_seed: int, fixture: Fixture) -> int:
    return mix(career_seed, f"fx:{fixture.id}", f"w:{fixture.week}", f"h:{fixture.home_id}", f"a:{fixture.away_id}")

# --- Engine adapter -----------------------------------------------------------

def _engine_adapter() -> Callable[[Dict[str, Any], Dict[str, Any], int, int], Dict[str, Any]]:
    """
    (home_team, away_team, seed, turn_limit) -> summary dict
    Keys expected: kills_home, kills_away, winner ('home'|'away'|None), events_typed?, events?
    """
    try:
        from engine import tbcombat as tb  # type: ignore
        if hasattr(tb, "simulate_match"):
            return lambda H, A, S, T: tb.simulate_match(H, A, seed=S, turn_limit=T)
        if hasattr(tb, "run_match"):
            return lambda H, A, S, T: tb.run_match(H, A, seed=S, turn_limit=T)
        if hasattr(tb, "TBCombat"):
            def _call(H, A, S, T):
                combat = tb.TBCombat(H, A, seed=S, turn_limit=T)
                return combat.run(auto=True)
            return _call
    except Exception:
        pass

    # Deterministic, OVR-weighted fallback
    def _quick(H, A, S, T):
        rng = random.Random(S)
        rh = H.get("roster") or H.get("fighters") or []
        ra = A.get("roster") or A.get("fighters") or []
        ah = sum(p.get("ovr", 40) for p in rh) / max(1, len(rh))
        aa = sum(p.get("ovr", 40) for p in ra) / max(1, len(ra))
        diff = ah - aa
        p_home = 1 / (1 + 10 ** (-diff / 20))
        r = rng.random()
        if abs(diff) < 2 and r < 0.20:
            winner = None
        else:
            winner = "home" if r < p_home else "away"
        ts = max(len(rh), len(ra), 3)
        base = ts
        kh = max(0, int(rng.gauss(base, 1.1)))
        ka = max(0, int(rng.gauss(base, 1.1)))
        if winner == "home":
            kh = max(kh, ka + rng.randint(1, 2))
        elif winner == "away":
            ka = max(ka, kh + rng.randint(1, 2))
        return {"kills_home": kh, "kills_away": ka, "winner": winner, "events_typed": [], "events": []}
    return _quick

_ENGINE_SIM = _engine_adapter()

# --- Public API ---------------------------------------------------------------

def simulate_week_ai(career: Career) -> None:
    _simulate_week(career, except_fixture_id=None)

def simulate_week_full(career: Career) -> None:
    _simulate_week(career, except_fixture_id=None)

def simulate_week_full_except(career: Career, except_fixture_id: Optional[str]) -> None:
    _simulate_week(career, except_fixture_id=except_fixture_id)

# --- Core runner --------------------------------------------------------------

def _simulate_week(career: Career, except_fixture_id: Optional[str]) -> None:
    fixtures = career.remaining_unplayed_in_week()
    for fx in fixtures:
        if except_fixture_id and fx.id == except_fixture_id:
            continue
        home, away = career.team_by_id(fx.home_id), career.team_by_id(fx.away_id)
        seed = _fixture_seed(career.seed, fx)
        summary = _ENGINE_SIM(home, away, seed, TURN_LIMIT)

        kills_home = int(summary.get("kills_home", 0))
        kills_away = int(summary.get("kills_away", 0))
        career.record_result(fx.id, kills_home, kills_away)

    career.advance_week_if_done()
