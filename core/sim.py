# core/sim.py
from __future__ import annotations

import random
from typing import List, Optional, Tuple

from engine import TBCombat, Team as BattleTeam, fighter_from_dict, layout_teams_tiles
from .types import Career, Fixture, TableRow
from . import config
from .rng import mix


def _ensure_table_rows(career: Career) -> None:
    if career.table:
        return
    for tid, name in enumerate(career.team_names):
        career.table[tid] = TableRow(team_id=tid, name=name)


def _top_k_by_ovr(roster: List[dict], k: int) -> List[dict]:
    return sorted(roster, key=lambda f: f.get("ovr", 50), reverse=True)[:k]


def _apply_table_result(tbl: TableRow, gf: int, ga: int, result: str) -> None:
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


def _fixture_seed(career: Career, fx: Fixture, idx_in_week: int) -> int:
    # Stable, cross-process child seed derived from career.seed and fixture identity
    return mix(career.seed, "fixture", fx.week, fx.home_id, fx.away_id, idx_in_week)


def _play_fixture_full(career: Career, fx: Fixture, seed: int) -> Tuple[int, int]:
    # Build teams and hydrate top TEAM_SIZE fighters each side
    H_id, A_id = fx.home_id, fx.away_id
    H_name, A_name = career.team_names[H_id], career.team_names[A_id]
    H_color, A_color = tuple(career.team_colors[H_id]), tuple(career.team_colors[A_id])
    teamH = BattleTeam(0, H_name, H_color)
    teamA = BattleTeam(1, A_name, A_color)

    topH = _top_k_by_ovr(career.rosters[H_id], config.TEAM_SIZE)
    topA = _top_k_by_ovr(career.rosters[A_id], config.TEAM_SIZE)
    fighters = [fighter_from_dict({**fd, "team_id": 0}) for fd in topH] + \
               [fighter_from_dict({**fd, "team_id": 1}) for fd in topA]

    layout_teams_tiles(fighters, config.GRID_W, config.GRID_H)
    tb = TBCombat(teamH, teamA, fighters, config.GRID_W, config.GRID_H, seed=seed)

    # Run to completion with global cap
    for _ in range(config.TURN_LIMIT):
        if tb.winner is not None:
            break
        tb.take_turn()

    # Score proxy: goals = number of enemies down (i.e., TEAM_SIZE - alive)
    home_alive = sum(1 for f in tb.fighters if f.team_id == 0 and f.alive)
    away_alive = sum(1 for f in tb.fighters if f.team_id == 1 and f.alive)
    H_goals = config.TEAM_SIZE - away_alive
    A_goals = config.TEAM_SIZE - home_alive
    return int(H_goals), int(A_goals)


def simulate_week_ai(career: Career) -> None:
    """
    Simulate all unplayed fixtures in the current week using the full engine with
    deterministic per-fixture seeds derived from career.seed.
    """
    _ensure_table_rows(career)
    week = career.week
    week_fixtures = [f for f in career.fixtures if f.week == week and not f.played]
    if not week_fixtures:
        return

    for i, fx in enumerate(week_fixtures):
        seed = _fixture_seed(career, fx, i)
        hg, ag = _play_fixture_full(career, fx, seed)
        fx.home_goals, fx.away_goals, fx.played = hg, ag, True

        H, A = career.table[fx.home_id], career.table[fx.away_id]
        if hg > ag:
            _apply_table_result(H, hg, ag, "W")
            _apply_table_result(A, ag, hg, "L")
        elif ag > hg:
            _apply_table_result(H, hg, ag, "L")
            _apply_table_result(A, ag, hg, "W")
        else:
            _apply_table_result(H, hg, ag, "D")
            _apply_table_result(A, ag, hg, "D")

    # Advance if week is complete
    if all(f.played for f in career.fixtures if f.week == week):
        career.week += 1


def simulate_week_full(career: Career, seed_base: int = 1000) -> None:
    """Alias retained for API compatibility; uses deterministic seeds internally."""
    simulate_week_ai(career)


def simulate_week_full_except(career: Career, skip_index: int, seed_base: int = 2000) -> None:
    """
    Simulate all unplayed fixtures in current week except the one at position 'skip_index'
    (0-based among this week's fixtures), using deterministic per-fixture seeds.
    """
    _ensure_table_rows(career)
    week = career.week
    week_fx = [f for f in career.fixtures if f.week == week]
    for i, fx in enumerate(week_fx):
        if i == skip_index or fx.played:
            continue
        seed = _fixture_seed(career, fx, i)
        hg, ag = _play_fixture_full(career, fx, seed)
        fx.home_goals, fx.away_goals, fx.played = hg, ag, True

        H, A = career.table[fx.home_id], career.table[fx.away_id]
        if hg > ag:
            _apply_table_result(H, hg, ag, "W"); _apply_table_result(A, ag, hg, "L")
        elif ag > hg:
            _apply_table_result(H, hg, ag, "L"); _apply_table_result(A, ag, hg, "W")
        else:
            _apply_table_result(H, hg, ag, "D"); _apply_table_result(A, ag, "D")
    if all(f.played for f in career.fixtures if f.week == week):
        career.week += 1
