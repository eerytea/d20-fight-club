# tests/test_schedule_round_robin.py
from __future__ import annotations
from collections import Counter
from core import schedule as _sched

def test_double_round_robin_counts_and_uniqueness():
    n = 6
    weeks = _sched.fixtures_double_round_robin(n_teams=n, start_week=1, comp_kind="league")
    all_fx = [fx for wk in weeks for fx in wk]
    # total matches in a double round-robin: n*(n-1)
    assert len(all_fx) == n * (n - 1)
    # each week has n/2 matches (since n is even here)
    for wk in weeks:
        assert len(wk) == n // 2
    # each ordered pair appears exactly once (home/away symmetry across two rounds)
    pairs = Counter((fx["home_id"], fx["away_id"]) for fx in all_fx)
    for h in range(n):
        for a in range(n):
            if h == a: continue
            assert pairs[(h, a)] == 1
