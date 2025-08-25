# core/sim.py
from __future__ import annotations

from typing import List, Optional, Tuple

from engine import TBCombat, Team as BattleTeam, fighter_from_dict, layout_teams_tiles
from .types import Career, Fixture, TableRow
from . import config
from .rng import mix


# ----------------------------- table + roster helpers -----------------------------

def _ensure_table_rows(career: Career) -> None:
    """Create empty table rows once per team."""
    if career.table:
        return
    for tid, name in enumerate(career.team_names):
        career.table[tid] = TableRow(team_id=tid, name=name)


def _top_k_by_ovr(roster: List[dict], k: int) -> List[dict]:
    """Pick top-K fighters by 'ovr' (descending)."""
    return sorted(roster, key=lambda f: f.get("ovr", 50), reverse=True)[:k]


def _apply_table_result(tbl: TableRow, gf: int, ga: int, result: str) -> None:
    """Update a single team's table row with a W/D/L result and GF/GA."""
    tbl.played += 1
    tbl.goals_for += gf
    tbl.goals_against += ga
    if result == "W":
        tbl.wins += 1
        tbl.points += config.POINTS_WIN
    elif result == "D":
        tbl.draws += 1
        tbl.points += config.POINTS_DRAW
    else:
        tbl.losses += 1
        tbl.points += config.POINTS_LOSS


# ----------------------------- deterministic seeding -----------------------------

def _fixture_seed(career: Career, fx: Fixture, idx_in_week: int) -> int:
    """
    Stable, cross-process child seed derived from career.seed and fixture identity.
    Using core.rng.mix keeps results identical across platforms and runs.
    """
    return mix(career.seed, "fixture", fx.week, fx.home_id, fx.away_id, idx_in_week)


# ----------------------------- single-fixture runner -----------------------------

def _play_fixture_full(career: Career, fx: Fixture, seed: int) -> Tuple[int, int]:
    """
    Hydrate and run a full TBCombat for a fixture.
    Returns (home_goals, away_goals) using 'downs as goals' proxy.
    """
    H_id, A_id = fx.home_id, fx.away_id
    H_name, A_name = career.team_names[H_id], career.team_names[A_id]
    H_color, A_color = tuple(career.team_colors[H_id]), tuple(career.team_colors[A_id])

    teamH = BattleTeam(0, H_name, H_color)
    teamA = BattleTeam(1, A_name, A_color)

    topH = _top_k_by_ovr(career.rosters[H_id], config.TEAM_SIZE)
    topA = _top_k_by_ovr(career.rosters[A_id], config.TEAM_SIZE)

    fighters = (
        [fighter_from_dict({**fd, "team_id": 0}) for fd in topH]
        + [fighter_from_dict({**fd, "team_id": 1}) for fd in topA]
    )

    layout_teams_tiles(fighters, config.GRID_W, config.GRID_H)
    tb = TBCombat(teamH, teamA, fighters, config.GRID_W, config.GRID_H, seed=seed)

    for _ in range(config.TURN_LIMIT):
        if tb.winner is not None:
            break
        tb.take_turn()

    # Score proxy: goals = number of enemy fighters downed (TEAM_SIZE - alive)
    home_alive = sum(1 for f in tb.fighters if f.team_id == 0 and f.alive)
    away_alive = sum(1 for f in tb.fighters if f.team_id == 1 and f.alive)
    home_goals = config.TEAM_SIZE - away_alive
    away_goals = config.TEAM_SIZE - home_alive
    return int(home_goals), int(away_goals)


# ----------------------------- unified week runner -----------------------------

def _simulate_week(career: Career, *, skip_index: Optional[int] = None) -> list[Fixture]:
    """
    Internal single implementation that all public week-sim functions delegate to.
    - Simulates unplayed fixtures in the current week (optionally skipping one index)
    - Uses deterministic per-fixture seeds
    - Centralizes table math
    - Advances week if all fixtures in the week are now played
    Returns the list of fixtures that were simulated in this call.
    """
    _ensure_table_rows(career)
    week = career.week
    week_fx: List[Fixture] = [f for f in career.fixtures if f.week == week]

    simulated: List[Fixture] = []
    for i, fx in enumerate(week_fx):
        if fx.played:
            continue
        if skip_index is not None and i == skip_index:
            continue

        seed = _fixture_seed(career, fx, i)
        hg, ag = _play_fixture_full(career, fx, seed)

        fx.home_goals = hg
        fx.away_goals = ag
        fx.played = True
        simulated.append(fx)

        H = career.table[fx.home_id]
        A = career.table[fx.away_id]
        if hg > ag:
            _apply_table_result(H, hg, ag, "W")
            _apply_table_result(A, ag, hg, "L")
        elif ag > hg:
            _apply_table_result(H, hg, ag, "L")
            _apply_table_result(A, ag, hg, "W")
        else:
            _apply_table_result(H, hg, ag, "D")
            _apply_table_result(A, ag, hg, "D")

    # Advance if the current week is fully played
    if week_fx and all(f.played for f in week_fx):
        career.week += 1

    return simulated


# ----------------------------- public API (thin wrappers) -----------------------------

def simulate_week_ai(career: Career) -> None:
    """
    Simulate all unplayed fixtures in the current week using the full engine
    (deterministic results derived from career.seed).
    """
    _simulate_week(career, skip_index=None)


def simulate_week_full(career: Career, seed_base: int = 1000) -> None:
    """
    Alias retained for API compatibility; delegates to the unified runner.
    """
    _simulate_week(career, skip_index=None)


def simulate_week_full_except(career: Career, skip_index: int, seed_base: int = 2000) -> None:
    """
    Simulate all unplayed fixtures in the current week EXCEPT the fixture at index `skip_index`
    (0-based among that week’s fixtures), using the full engine and deterministic seeds.
    """
    _simulate_week(career, skip_index=skip_index)
