# core/standings.py
from __future__ import annotations
from typing import Dict, List, Tuple, Iterable
from collections import defaultdict
from .config import POINTS_WIN, POINTS_DRAW, POINTS_LOSS

TableRow = Dict[str, int]
Table = Dict[int, TableRow]
H2HMap = Dict[Tuple[int, int], Dict[str, int]]

def new_table(team_ids: Iterable[int]):
    table: Table = {tid: {"P":0,"W":0,"D":0,"L":0,"K":0,"KA":0,"PTS":0} for tid in team_ids}
    h2h: H2HMap = defaultdict(lambda: {"a_pts":0,"b_pts":0,"a_k":0,"b_k":0})
    return table, h2h

def _ordered_pair(a: int, b: int) -> Tuple[int, int, bool]:
    if a < b: return a, b, True
    if a > b: return b, a, False
    return a, b, True

def apply_result(table: Table, h2h: H2HMap, home: int, away: int, k_home: int, k_away: int) -> None:
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
    by_pts: Dict[int, List[int]] = defaultdict(list)
    for tid, row in table.items():
        by_pts[row["PTS"]].append(tid)
    out: List[Tuple[int, TableRow]] = []
    for pts in sorted(by_pts.keys(), reverse=True):
        cluster = by_pts[pts]
        if len(cluster) == 1:
            tid = cluster[0]; out.append((tid, table[tid])); continue
        cluster.sort(key=lambda t: kill_diff(table[t]), reverse=True)
        i = 0
        while i < len(cluster):
            j = i + 1
            kd_i = kill_diff(table[cluster[i]])
            while j < len(cluster) and kill_diff(table[cluster[j]]) == kd_i:
                j += 1
            sub = cluster[i:j]
            if len(sub) == 1:
                t = sub[0]; out.append((t, table[t]))
            else:
                def h2h_points(tid: int) -> int:
                    pts_sum = 0
                    for other in sub:
                        if other == tid: continue
                        a, b, ab = _ordered_pair(tid, other)
                        rec = h2h[(a, b)]
                        pts_sum += rec["a_pts"] if ab else rec["b_pts"]
                    return pts_sum
                sub.sort(key=lambda t: (h2h_points(t), table[t]["K"]), reverse=True)
                for t in sub:
                    out.append((t, table[t]))
            i = j
    return out

def table_rows_sorted(table: Table, h2h: H2HMap) -> List[Dict]:
    """UI helper: returns a list of dicts with GD included and rank order applied."""
    rows: List[Dict] = []
    for rank, (tid, row) in enumerate(sort_table(table, h2h), start=1):
        rows.append({
            "rank": rank, "tid": tid, "P": row["P"], "W": row["W"], "D": row["D"], "L": row["L"],
            "K": row["K"], "KA": row["KA"], "GD": row["K"] - row["KA"], "PTS": row["PTS"],
        })
    return rows
