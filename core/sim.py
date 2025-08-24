from __future__ import annotations

import random
def set_seed(seed: int | None):
    if seed is not None:
        random.seed(seed)

from __future__ import annotations
from typing import List
import random

from engine import TBCombat, Team as BattleTeam, fighter_from_dict, layout_teams_tiles
from .types import Career, Fixture, TableRow

GRID_W, GRID_H = 10, 8  # small grid for speed

def _ensure_table_rows(career: Career) -> None:
    if career.table:
        return
    for tid, name in enumerate(career.team_names):
        career.table[tid] = TableRow(team_id=tid, name=name)

def _pick_top4(roster: list[dict]) -> list[dict]:
    # choose top 4 by OVR (field name 'ovr' exists in creator output)
    return sorted(roster, key=lambda f: f.get("ovr", 50), reverse=True)[:4]

def _play_fixture(career: Career, fx: Fixture, seed: int) -> None:
    # hydrate fighters for both sides, pick top 4 each
    rng = random.Random(seed)

    H_id, A_id = fx.home_id, fx.away_id
    H_name = career.team_names[H_id]
    A_name = career.team_names[A_id]
    H_color = tuple(career.team_colors[H_id])
    A_color = tuple(career.team_colors[A_id])

    H_team = BattleTeam(H_id, H_name, H_color)
    A_team = BattleTeam(A_id, A_name, A_color)

    H_f = [_ for _ in _pick_top4(career.rosters[H_id])]
    A_f = [_ for _ in _pick_top4(career.rosters[A_id])]
    fighters = [fighter_from_dict({**fd, "team_id": H_id}) for fd in H_f] + \
               [fighter_from_dict({**fd, "team_id": A_id}) for fd in A_f]

    layout_teams_tiles(fighters, GRID_W, GRID_H)
    combat = TBCombat(H_team, A_team, fighters, GRID_W, GRID_H, seed=seed)

    # run capped turns
    for _ in range(1000):
        if combat.winner is not None:
            break
        combat.take_turn()

    # score proxy: #downed enemies (you can replace with engine metric)
    # Here we count alive remaining as inverse, or rely on engine if it exposes a stat.
    home_alive = sum(1 for f in fighters if f.team_id == H_id and f.alive)
    away_alive = sum(1 for f in fighters if f.team_id == A_id and f.alive)
    # convert to “goals” style
    H_goals = 4 - away_alive
    A_goals = 4 - home_alive

    fx.home_goals = int(H_goals)
    fx.away_goals = int(A_goals)
    fx.played = True

def _apply_table_result(tbl: TableRow, gf: int, ga: int, res: str) -> None:
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

def simulate_week_ai(career: Career) -> None:
    _ensure_table_rows(career)
    # play all fixtures for current week which are not played
    week = career.week
    fixtures = [f for f in career.fixtures if f.week == week and not f.played]
    if not fixtures:
        return
    for fx in fixtures:
        # deterministic but varied
        seed = (career.seed * 10_007) ^ (fx.week*997) ^ (fx.home_id*31 + fx.away_id*17)
        _play_fixture(career, fx, seed)

        # update table
        H, A = career.table[fx.home_id], career.table[fx.away_id]
        hg, ag = fx.home_goals or 0, fx.away_goals or 0
        if hg > ag:
            _apply_table_result(H, hg, ag, "W")
            _apply_table_result(A, ag, hg, "L")
        elif hg < ag:
            _apply_table_result(H, hg, ag, "L")
            _apply_table_result(A, ag, hg, "W")
        else:
            _apply_table_result(H, hg, ag, "D")
            _apply_table_result(A, ag, hg, "D")

    # advance week
    career.week += 1

# core/sim.py  (additions)
from __future__ import annotations
from typing import Optional, Tuple
from .types import Career, Fixture
from engine import Team, fighter_from_dict, layout_teams_tiles, TBCombat

# Reuse your grid dims
GRID_W, GRID_H = 10, 8

def _build_top4_teams_for_fixture(career: Career, fx: Fixture) -> Tuple[Team, Team, list]:
    """Build engine teams + top4 fighters per side for a fixture."""
    H_id, A_id = fx.home_id, fx.away_id
    teamH = Team(0, career.team_names[H_id], tuple(career.team_colors[H_id]))
    teamA = Team(1, career.team_names[A_id], tuple(career.team_colors[A_id]))

    def top4(tid):
        roster = career.rosters[tid]
        return sorted(roster, key=lambda f: f.get("ovr", 50), reverse=True)[:4]

    fighters = [fighter_from_dict({**fd, "team_id": 0}) for fd in top4(H_id)] + \
               [fighter_from_dict({**fd, "team_id": 1}) for fd in top4(A_id)]
    layout_teams_tiles(fighters, GRID_W, GRID_H)
    return teamH, teamA, fighters

def simulate_fixture_full(career: Career, fx: Fixture, seed: Optional[int] = None) -> Tuple[int,int,int]:
    """
    Run a full engine combat for the fixture.
    Returns (home_goals, away_goals, winner_tid_rel) where winner_tid_rel in {0,1,-1},
    relative to (home=0, away=1).
    """
    teamH, teamA, fighters = _build_top4_teams_for_fixture(career, fx)
    tb = TBCombat(teamH, teamA, fighters, GRID_W, GRID_H, seed=seed)
    # Run with a hard cap to avoid infinite loops
    for _ in range(3000):
        if tb.winner is not None:
            break
        tb.take_turn()

    # Derive a "score" from downs inflicted (simple, deterministic)
    # Count how many enemy fighters are down at end. More downs = more "goals".
    downs_by_home = sum(1 for f in tb.fighters if f.team_id == 1 and not f.alive)
    downs_by_away = sum(1 for f in tb.fighters if f.team_id == 0 and not f.alive)

    winner_rel = tb.winner if tb.winner is not None else -1
    # Fall back: if tb.winner is -1 (both wiped), keep a draw; otherwise set goals equal if winner only decided by wipe.
    home_goals = downs_by_home
    away_goals = downs_by_away
    return home_goals, away_goals, winner_rel

def _apply_result(career: Career, fx: Fixture, home_goals: int, away_goals: int):
    fx.home_goals = home_goals
    fx.away_goals = away_goals
    fx.played = True
    # table update: 3/1/0
    tH = career.table[fx.home_id]
    tA = career.table[fx.away_id]
    tH.played += 1; tA.played += 1
    tH.goals_for += home_goals; tH.goals_against += away_goals
    tA.goals_for += away_goals; tA.goals_against += home_goals
    if home_goals > away_goals:
        tH.wins += 1; tA.losses += 1; tH.points += 3
    elif away_goals > home_goals:
        tA.wins += 1; tH.losses += 1; tA.points += 3
    else:
        tH.draws += 1; tA.draws += 1; tH.points += 1; tA.points += 1

def simulate_week_full(career: Career, seed_base: int = 1000) -> None:
    """Full-combat sim every unplayed fixture in the current week, then advance the week."""
    wk = career.week
    for i, fx in enumerate([f for f in career.fixtures if f.week == wk and not f.played]):
        hg, ag, _ = simulate_fixture_full(career, fx, seed=seed_base + i)
        _apply_result(career, fx, hg, ag)
    # advance to next week if all now played
    if all(f.played for f in career.fixtures if f.week == wk):
        career.week += 1

def simulate_week_full_except(career: Career, skip_index: int, seed_base: int = 2000) -> None:
    """
    Full-combat sim every unplayed fixture in the current week EXCEPT the one at index skip_index
    within that week's list (0-based among that week's fixtures).
    """
    wk = career.week
    week_fx = [f for f in career.fixtures if f.week == wk]
    for i, fx in enumerate(week_fx):
        if i == skip_index: 
            continue
        if fx.played:
            continue
        hg, ag, _ = simulate_fixture_full(career, fx, seed=seed_base + i)
        _apply_result(career, fx, hg, ag)
    if all(f.played for f in career.fixtures if f.week == wk):
        career.week += 1

