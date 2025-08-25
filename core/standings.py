# core/standings.py
from __future__ import annotations
from typing import Dict, List, Tuple, Iterable
from collections import defaultdict
from .config import POINTS_WIN, POINTS_DRAW, POINTS_LOSS

TableRow = Dict[str, int]
Table = Dict[int, TableRow]          # tid -> row
H2HMap = Dict[Tuple[int, int], Dict[str, int]]  # (a,b) ordered -> {"a_pts":..., "b_pts":..., "a_k":..., "b_k":...}

def new_table(team_ids: Iterable[int]) -> Tuple[Table, H2HMap]:
    table: Table = {}
    for tid in team_ids:
        table[tid] = {
            "P": 0,     # played
            "W": 0,
            "D": 0,
            "L": 0,
            "K": 0,     # kills for (PF)
            "KA": 0,    # kills against (PA)
            "PTS": 0,
        }
    return table, defaultdict(lambda: {"a_pts":0,"b_pts":0,"a_k":0,"b_k":0})

def _ordered_pair(a: int, b: int) -> Tuple[int, int, bool]:
    if a < b: return (a, b, True)
    if a > b: return (b, a, False)
    return (a, b, True)

def apply_result(table: Table, h2h: H2HMap, home: int, away: int, k_home: int, k_away: int) -> None:
    # update table
    th, ta = table[home], table[away]
    th["P"] += 1; ta["P"] += 1
    th["K"] += k_home; th["KA"] += k_away
    ta["K"] += k_away; ta["KA"] += k_home

    if k_home > k_away:
        th["W"] += 1; ta["L"] += 1
        th["PTS"] += POINTS_WIN; ta["PTS"] += POINTS_LOSS
        a_pts, b_pts = POINTS_WIN, POINTS_LOSS
    elif k_home < k_away:
        ta["W"] += 1; th["L"] += 1
        ta["PTS"] += POINTS_WIN; th["PTS"] += POINTS_LOSS
        a_pts, b_pts = POINTS_LOSS, POINTS_WIN
    else:
        th["D"] += 1; ta["D"] += 1
        th["PTS"] += POINTS_DRAW; ta["PTS"] += POINTS_DRAW
        a_pts = b_pts = POINTS_DRAW

    # update head-to-head mini-table
    a, b, ab = _ordered_pair(home, away)
    rec = h2h[(a, b)]
    if ab:
        rec["a_pts"] += a_pts; rec["b_pts"] += b_pts
        rec["a_k"] += k_home;  rec["b_k"] += k_away
    else:
        rec["a_pts"] += b_pts; rec["b_pts"] += a_pts
        rec["a_k"] += k_away;  rec["b_k"] += k_home

def kill_diff(row: TableRow) -> int:
    return row["K"] - row["KA"]

def sort_table(table: Table, h2h: H2HMap) -> List[Tuple[int, TableRow]]:
    """
    Sort by: Points, Kill Diff, Head-to-Head points (among tied cluster), then total K (for stability).
    Returns a list of (tid, row) sorted descending.
    """
    # group by points
    by_pts: Dict[int, List[int]] = defaultdict(list)
    for tid, row in table.items():
        by_pts[row["PTS"]].append(tid)

    sorted_pts = sorted(by_pts.keys(), reverse=True)
    out: List[Tuple[int, TableRow]] = []

    for pts in sorted_pts:
        cluster = by_pts[pts]
        if len(cluster) == 1:
            tid = cluster[0]
            out.append((tid, table[tid]))
            continue

        # tie-break among cluster by Kill Diff
        cluster.sort(key=lambda t: kill_diff(table[t]), reverse=True)

        # find sub-clusters that still tie on KD
        i = 0
        while i < len(cluster):
            j = i + 1
            kd_i = kill_diff(table[cluster[i]])
            while j < len(cluster) and kill_diff(table[cluster[j]]) == kd_i:
                j += 1
            sub = cluster[i:j]
            if len(sub) == 1:
                out.append((sub[0], table[sub[0]]))
            else:
                # Head-to-Head points across the tied subset
                def h2h_points(tid: int) -> int:
                    pts_sum = 0
                    for other in sub:
                        if other == tid: continue
                        a, b, ab = _ordered_pair(tid, other)
                        rec = h2h[(a, b)]
                        if ab:
                            pts_sum += rec["a_pts"]
                        else:
                            pts_sum += rec["b_pts"]
                    return pts_sum
                sub.sort(key=lambda t: (h2h_points(t), table[t]["K"]), reverse=True)
                for t in sub:
                    out.append((t, table[t]))
            i = j

    return out
