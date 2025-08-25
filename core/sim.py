# core/sim.py
from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple, Callable
import random
import hashlib

from .config import TURN_LIMIT
from .career import Career, Fixture


# --- Deterministic fixture seeding --------------------------------------------

def _hash_to_int(s: str) -> int:
    return int(hashlib.sha1(s.encode("utf-8")).hexdigest()[:12], 16)

def _fixture_seed(career_seed: int, fixture: Fixture) -> int:
    """
    Mix career.seed with a stable fixture identity to produce a reproducible child seed.
    """
    return (career_seed * 1_000_003) ^ _hash_to_int(f"{fixture.id}:{fixture.week}:{fixture.home_id}:{fixture.away_id}")


# --- Engine adapter (typed events + string log expected) ----------------------

def _engine_adapter() -> Callable[[Dict[str, Any], Dict[str, Any], int, int], Dict[str, Any]]:
    """
    Returns a callable: (home_team_dict, away_team_dict, seed, turn_limit) -> summary dict
    Summary dict should include:
        kills_home: int
        kills_away: int
        winner: 'home' | 'away' | None
        events_typed: List[Any]   (optional)
        events: List[str]         (optional)
    We try to call your engine/tbcombat; if not available, use a quick OVR-based sim.
    """
    try:
        # Your engine module; customize the known entrypoints here if needed.
        from engine import tbcombat as tb  # type: ignore
        # Preferred function signatures (we'll try in this order)
        if hasattr(tb, "simulate_match"):
            def _call(home_team: Dict[str, Any], away_team: Dict[str, Any], seed: int, turn_limit: int) -> Dict[str, Any]:
                return tb.simulate_match(home_team, away_team, seed=seed, turn_limit=turn_limit)
            return _call
        if hasattr(tb, "run_match"):
            def _call(home_team: Dict[str, Any], away_team: Dict[str, Any], seed: int, turn_limit: int) -> Dict[str, Any]:
                return tb.run_match(home_team, away_team, seed=seed, turn_limit=turn_limit)
            return _call
        if hasattr(tb, "TBCombat"):
            def _call(home_team: Dict[str, Any], away_team: Dict[str, Any], seed: int, turn_limit: int) -> Dict[str, Any]:
                # Generic TBCombat wrapper; adapt if your class has different API.
                combat = tb.TBCombat(home_team, away_team, seed=seed, turn_limit=turn_limit)
                result = combat.run(auto=True)
                return result  # expect the same keys as documented above
            return _call
    except Exception:
        pass

    # Fallback quick-sim: deterministic, OVR-weighted, no event logs.
    def _quick_sim(home_team: Dict[str, Any], away_team: Dict[str, Any], seed: int, turn_limit: int) -> Dict[str, Any]:
        rng = random.Random(seed)
        avg_home = sum(p.get("ovr", 40) for p in home_team.get("roster", [])) / max(1, len(home_team.get("roster", [])))
        avg_away = sum(p.get("ovr", 40) for p in away_team.get("roster", [])) / max(1, len(away_team.get("roster", [])))
        # Convert to win probability (simple logistic)
        diff = avg_home - avg_away
        p_home = 1.0 / (1.0 + pow(10.0, -diff / 20.0))
        # Decide winner
        r = rng.random()
        if abs(avg_home - avg_away) < 2.0 and r < 0.15:
            winner = None  # draw chance if very close
        else:
            winner = "home" if r < p_home else "away"
        # Kills roughly equal to team size with some noise
        ts = max(len(home_team.get("roster", [])), len(away_team.get("roster", [])))
        base = max(3, ts)
        kh = max(0, int(rng.gauss(base, 1.2)))
        ka = max(0, int(rng.gauss(base, 1.2)))
        # Nudge winner to have more kills
        if winner == "home":
            kh, ka = max(kh, ka + rng.randint(0, 2)), min(ka, kh - rng.randint(0, 1))
        elif winner == "away":
            ka, kh = max(ka, kh + rng.randint(0, 2)), min(kh, ka - rng.randint(0, 1))
        # Clamp and avoid negative
        kh = max(0, kh); ka = max(0, ka)
        return {
            "kills_home": kh,
            "kills_away": ka,
            "winner": winner,
            "events_typed": [],
            "events": [],
        }

    return _quick_sim

_ENGINE_SIM = _engine_adapter()


# --- Public API: unified week runner ------------------------------------------

def simulate_week_ai(career: Career) -> None:
    """Sim every unplayed fixture in this week (including user's) headlessly."""
    _simulate_week(career, mode="ai_all")

def simulate_week_full(career: Career) -> None:
    """Sim every unplayed fixture in this week with full combat (headless)."""
    _simulate_week(career, mode="full_all")

def simulate_week_full_except(career: Career, except_fixture_id: Optional[str]) -> None:
    """
    Sim every unplayed fixture in this week *except* the provided fixture id
    (used when the user will play/watch their own match).
    """
    _simulate_week(career, mode="full_except", except_fixture_id=except_fixture_id)


# --- Core runner ---------------------------------------------------------------

def _simulate_week(
    career: Career,
    mode: str,
    except_fixture_id: Optional[str] = None,
) -> None:
    """
    Single internal path used by all public week runners.
    Modes:
      - "ai_all": simulate all fixtures headlessly
      - "full_all": simulate all fixtures with engine (headless)
      - "full_except": simulate all fixtures with engine except except_fixture_id
    """
    # Today, "ai_all" and "full_all" both go through the engine adapter; if you later
    # want a separate lightweight sim, you can split behaviors here.
    fixtures = career.remaining_unplayed_in_week()

    for fx in fixtures:
        if mode == "full_except" and except_fixture_id and fx.id == except_fixture_id:
            continue

        # Build inputs for engine
        home = career.team_by_id(fx.home_id)
        away = career.team_by_id(fx.away_id)

        # Deterministic seed per fixture
        seed = _fixture_seed(career.seed, fx)

        # Run combat (typed events + legacy strings are supported by adapter)
        summary = _ENGINE_SIM(home, away, seed, TURN_LIMIT)

        # Winner mapping
        winner_tid: Optional[int]
        if summary.get("winner") == "home":
            winner_tid = fx.home_id
        elif summary.get("winner") == "away":
            winner_tid = fx.away_id
        else:
            winner_tid = None

        kills_home = int(summary.get("kills_home", 0))
        kills_away = int(summary.get("kills_away", 0))

        # Record + update standings
        career.record_result(fx.id, kills_home, kills_away)

    # If everything in the week is played, advance week
    career.advance_week_if_done()
