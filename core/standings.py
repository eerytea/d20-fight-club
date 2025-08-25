# core/standings.py
from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Tuple, List

# Reuse the lightweight dataclass used by tests
from .types import TableRow

# Type aliases for clarity
Table = Dict[int, TableRow]
H2HMap = Dict[Tuple[int, int], Dict[str, int]]  # (A,B) -> {a_gf, a_ga, a_pts, b_pts}


def new_table(team_ids: List[int], names: Dict[int, str] | None = None) -> tuple[Table, H2HMap]:
    """
    Create a standings table with TableRow entries and an empty H2H map.
    """
    table: Table = {}
    for tid in team_ids:
        table[tid] = TableRow(
            team_id=tid,
            name=(names.get(tid) if names else f"Team {tid}"),
            played=0,
            wins=0,
            goals_for=0,
            goals_against=0,
            points=0,
        )
    h2h: H2HMap = {}
    return table, h2h


def apply_result(table: Table, h2h: H2HMap, home_id: int, away_id: int, k_home: int, k_away: int) -> None:
    """
    Apply a single match result to the standings and H2H map.
    Points system: 3-1-0 (W-D-L). Goals are "kills".
    """
    th = table[home_id]
    ta = table[away_id]

    th.played += 1
    ta.played += 1

    th.goals_for += int(k_home)
    th.goals_against += int(k_away)
    ta.goals_for += int(k_away)
    ta.goals_against += int(k_home)

    if k_home > k_away:
        th.wins += 1
        th.points += 3
    elif k_home < k_away:
        ta.wins += 1
        ta.points += 3
    else:
        th.points += 1
        ta.points += 1

    key = (home_id, away_id)
    rec = h2h.setdefault(key, {"a_gf": 0, "a_ga": 0, "a_pts": 0, "b_pts": 0})
    rec["a_gf"] += int(k_home)
    rec["a_ga"] += int(k_away)
    if k_home > k_away:
        rec["a_pts"] += 3
    elif k_home == k_away:
        rec["a_pts"] += 1
        rec["b_pts"] += 1
    else:
        rec["b_pts"] += 3


def _goal_diff(r: TableRow) -> int:
    return int(r.goals_for) - int(r.goals_against)


def sort_table(table: Table, h2h: H2HMap) -> List[Tuple[int, Dict[str, int]]]:
    """
    Return a list of (team_id, row_as_dict) sorted by:
      points DESC, goal difference DESC, goals_for DESC, team_id ASC.
    (Head-to-head is tracked but omitted here to keep things simple and deterministic.)
    """
    rows = list(table.values())
    rows.sort(
        key=lambda r: (int(r.points), _goal_diff(r), int(r.goals_for), -int(r.team_id)),
        reverse=True,
    )
    # Convert TableRow -> dict for callers that expect dict-like stats
    out: List[Tuple[int, Dict[str, int]]] = []
    for r in rows:
        d = asdict(r)
        out.append((r.team_id, d))
    return out
