# core/sim.py
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
