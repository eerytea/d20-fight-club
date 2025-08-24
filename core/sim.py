# core/sim.py
from __future__ import annotations

from typing import List, Tuple, Optional
import random

from .types import Career, Fixture, TableRow

# Keep these around in case other modules expect them
GRID_W, GRID_H = 10, 8


# ---------------------------
# Seeding / Determinism
# ---------------------------
def set_seed(seed: Optional[int]) -> None:
    """Optionally seed Python's global RNG for reproducible sims."""
    if seed is not None:
        random.seed(seed)


def _seed_for_fixture(career: Career, fx: Fixture) -> int:
    """Deterministic per-fixture seed derived from career + fixture fields."""
    # Mix in career.seed, week, and team ids with different primes.
    base = getattr(career, "seed", 0) or 0
    return (base * 10007) ^ (fx.week * 997) ^ (fx.home_id * 31 + fx.away_id * 17)


# ---------------------------
# Table helpers
# ---------------------------
def _ensure_table_rows(career: Career) -> None:
    """Ensure every team has a TableRow in the standings."""
    if career.table:
        # assume already built
        return
    for tid, name in enumerate(career.team_names):
        career.table[tid] = TableRow(team_id=tid, name=name)


def _apply_table_result(tbl: TableRow, gf: int, ga: int, res: str) -> None:
    """Apply a single match result to a table row (3/1/0)."""
    tbl.played += 1
    tbl.goals_for += gf
    tbl.goals_against += ga
    if res == "W":
        tbl.wins += 1
        tbl.points += 3
    elif res == "D":
        tbl.draws += 1
        tbl.points += 1
    else:
        tbl.losses += 1


# ---------------------------
# Team strength / scoring
# ---------------------------
def _top_n_roster(roster: List[dict], n: int = 4) -> List[dict]:
    """Pick the top-N fighters by 'ovr' from a roster dict list."""
    return sorted(roster, key=lambda f: f.get("ovr", 50), reverse=True)[:n]


def _team_strength(career: Career, team_id: int, n: int = 4) -> int:
    """Compute a simple team strength as the sum of top-N OVR."""
    rs = career.rosters[team_id]
    return sum(int(x.get("ovr", 50)) for x in _top_n_roster(rs, n=n))


def _quick_goals_for_pair(str_home: int, str_away: int, rng: random.Random) -> Tuple[int, int]:
    """
    Convert two strengths into plausible 'goals' (0–4 ish) with a bit of noise.
    This is a deliberately simple, deterministic, and test-stable proxy.
    """
    # Base chances from relative strength
    total = max(1, str_home + str_away)
    p_home = str_home / total
    p_away = str_away / total

    # Draw 4 Bernoulli-like chances per side (cap at 4)
    # You can tweak these multipliers for a different scoring profile.
    trials = 4
    h = sum(1 for _ in range(trials) if rng.random() < (0.35 + 0.4 * p_home))
    a = sum(1 for _ in range(trials) if rng.random() < (0.35 + 0.4 * p_away))

    # keep within a reasonable cap
    return min(h, 4), min(a, 4)


def _play_fixture_quick(career: Career, fx: Fixture, seed: int) -> None:
    """
    Quick, RNG-based simulation for a single fixture.
    Updates fx.home_goals, fx.away_goals, fx.played.
    """
    rng = random.Random(seed)

    str_home = _team_strength(career, fx.home_id)
    str_away = _team_strength(career, fx.away_id)
    hg, ag = _quick_goals_for_pair(str_home, str_away, rng)

    fx.home_goals = int(hg)
    fx.away_goals = int(ag)
    fx.played = True


# ---------------------------
# Public APIs
# ---------------------------
def simulate_week_ai(career: Career) -> None:
    """
    Simulate all unplayed fixtures in the current week using a quick, deterministic model.
    Updates the table and advances the week if all fixtures are played.
    """
    _ensure_table_rows(career)
    wk = career.week

    # Gather unplayed fixtures for this week
    week_fixtures = [f for f in career.fixtures if f.week == wk and not f.played]
    if not week_fixtures:
        return

    for fx in week_fixtures:
        seed = _seed_for_fixture(career, fx)
        _play_fixture_quick(career, fx, seed)

        # Update table
        H = career.table[fx.home_id]
        A = career.table[fx.away_id]
        hg = fx.home_goals or 0
        ag = fx.away_goals or 0

        if hg > ag:
            _apply_table_result(H, hg, ag, "W")
            _apply_table_result(A, ag, hg, "L")
        elif hg < ag:
            _apply_table_result(H, hg, ag, "L")
            _apply_table_result(A, ag, hg, "W")
        else:
            _apply_table_result(H, hg, ag, "D")
            _apply_table_result(A, ag, hg, "D")

    # Advance to next week if everything for this week is now played
    if all(f.played for f in career.fixtures if f.week == wk):
        career.week += 1


def simulate_week_full(career: Career, seed_base: int = 1000) -> None:
    """
    Placeholder for 'full combat' simulation.
    Currently delegates to the same quick-sim logic for stability and tests.
    Swap _play_fixture_quick with a real engine-driven run when combat AI is ready.
    """
    _ensure_table_rows(career)
    wk = career.week
    week_fixtures = [f for f in career.fixtures if f.week == wk and not f.played]
    if not week_fixtures:
        return

    for i, fx in enumerate(week_fixtures):
        # Merge base with deterministic per-fixture seed
        seed = seed_base ^ _seed_for_fixture(career, fx) ^ i
        _play_fixture_quick(career, fx, seed)

        H = career.table[fx.home_id]
        A = career.table[fx.away_id]
        hg = fx.home_goals or 0
        ag = fx.away_goals or 0
        if hg > ag:
            _apply_table_result(H, hg, ag, "W")
            _apply_table_result(A, ag, hg, "L")
        elif hg < ag:
            _apply_table_result(H, hg, ag, "L")
            _apply_table_result(A, ag, hg, "W")
        else:
            _apply_table_result(H, hg, ag, "D")
            _apply_table_result(A, ag, hg, "D")

    if all(f.played for f in career.fixtures if f.week == wk):
        career.week += 1


def simulate_week_full_except(career: Career, skip_index: int, seed_base: int = 2000) -> None:
    """
    Simulate the current week's fixtures with quick-sim, skipping the fixture at the
    given 0-based index **within this week's fixtures order**.
    """
    _ensure_table_rows(career)
    wk = career.week
    week_fx = [f for f in career.fixtures if f.week == wk]

    for i, fx in enumerate(week_fx):
        if i == skip_index or fx.played:
            continue
        seed = seed_base ^ _seed_for_fixture(career, fx) ^ i
        _play_fixture_quick(career, fx, seed)

        H = career.table[fx.home_id]
        A = career.table[fx.away_id]
        hg = fx.home_goals or 0
        ag = fx.away_goals or 0
        if hg > ag:
            _apply_table_result(H, hg, ag, "W")
            _apply_table_result(A, ag, hg, "L")
        elif hg < ag:
            _apply_table_result(H, hg, ag, "L")
            _apply_table_result(A, ag, hg, "W")
        else:
            _apply_table_result(H, hg, ag, "D")
            _apply_table_result(A, ag, hg, "D")

    if all(f.played for f in career.fixtures if f.week == wk):
        career.week += 1
