from core.standings import new_table, apply_result, table_rows_sorted

def test_points_kd_h2h_ordering():
    tids = [1,2,3]
    table, h2h = new_table(tids)
    # Results:
    # 1 beats 2 (2-0), 2 beats 3 (2-0), 3 beats 1 (2-0) -> all 3 pts, GD +2/-2, tied on PTS & GD
    apply_result(table, h2h, 1, 2, 2, 0)
    apply_result(table, h2h, 2, 3, 2, 0)
    apply_result(table, h2h, 3, 1, 2, 0)
    rows = table_rows_sorted(table, h2h)
    # H2H circular tie: fallback uses total K as final stabilizer; order should be stable and non-crashing
    assert [r["tid"] for r in rows] == [1,2,3] or [r["tid"] for r in rows] == [2,3,1] or [r["tid"] for r in rows] == [3,1,2]
    # Points sum check
    assert sum(r["PTS"] for r in rows) == 9
