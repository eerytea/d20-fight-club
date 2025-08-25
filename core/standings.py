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


def _h2h_points_for(a: int, b: int, h2h: H2HMap) -> int:
    """Total points team a earned vs team b across all meetings (home/away)."""
    pts = 0
    rec_ab = h2h.get((a, b))
    if rec_ab:
        pts += int(rec_ab.get("a_pts", 0))
    rec_ba = h2h.get((b, a))
    if rec_ba:
        pts += int(rec_ba.get("b_pts", 0))  # when b was 'a' in that key, 'b_pts' are a's points
    return pts


def _group_h2h_rankings(tids: List[int], h2h: H2HMap) -> Dict[int, int]:
    """
    For a tied group, compute head-to-head points each team earned against
    other teams in the same group. Higher is better.
    """
    scores: Dict[int, int] = {tid: 0 for tid in tids}
    for i, a in enumerate(tids):
        for b in tids:
            if a == b:
                continue
            scores[a] += _h2h_points_for(a, b, h2h)
    return scores


def _sorted_with_tiebreakers(table: Table, h2h: H2HMap) -> List[int]:
    """
    Sort team IDs by:
      1) Points (desc)
      2) Goal difference (desc)
      3) Head-to-head points within tied cluster (desc)
      4) Goals for (desc)
      5) Team id (asc) — stable final breaker
    """
    # First pass: sort by coarse metrics (points, GD, GF)
    ids = list(table.keys())
    ids.sort(
        key=lambda tid: (int(table[tid].points), _goal_diff(table[tid]), int(table[tid].goals_for), -int(tid)),
        reverse=True,
    )

    # Second pass: resolve clusters tied on (points, GD) using head-to-head mini-table
    i = 0
    out: List[int] = []
    n = len(ids)
    while i < n:
        tid = ids[i]
        r = table[tid]
        cluster = [tid]
        j = i + 1
        while j < n:
            t2 = ids[j]
            r2 = table[t2]
            if (r.points == r2.points) and (_goal_diff(r) == _goal_diff(r2)):
                cluster.append(t2)
                j += 1
            else:
                break
        if len(cluster) > 1:
            h2h_scores = _group_h2h_rankings(cluster, h2h)
            cluster.sort(
                key=lambda t: (h2h_scores[t], int(table[t].goals_for), -int(t)),
                reverse=True,
            )
        out.extend(cluster)
        i = j
    return out


def sort_table(table: Table, h2h: H2HMap) -> List[tuple[int, Dict[str, int]]]:
    """
    Return a list of (team_id, row_as_dict) sorted with the tiebreakers above.
    """
    ordered_ids = _sorted_with_tiebreakers(table, h2h)
    return [(tid, asdict(table[tid])) for tid in ordered_ids]


# Back-compat name used by tests
def table_rows_sorted(table: Table, h2h: H2HMap) -> List[tuple[int, Dict[str, int]]]:
    """
    Alias expected by tests: identical to sort_table.
    """
    return sort_table(table, h2h)
