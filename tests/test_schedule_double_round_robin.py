from core.schedule import build_double_round_robin

def test_double_round_robin_pairs_and_weeks():
    team_ids = list(range(6))  # 6 teams
    fixtures = build_double_round_robin(team_ids, rounds=2, shuffle_seed=123)
    # For any unordered pair, there should be exactly two fixtures with opposite homes.
    pair_counts = {}
    home_map = {}
    for fx in fixtures:
        a, b = fx["home_id"], fx["away_id"]
        key = tuple(sorted((a, b)))
        pair_counts[key] = pair_counts.get(key, 0) + 1
        home_map.setdefault(key, set()).add(a)
    # n*(n-1)/2 pairs; each pair appears twice; and both teams host once
    assert len(pair_counts) == (len(team_ids) * (len(team_ids) - 1)) // 2
    assert all(c == 2 for c in pair_counts.values())
    assert all(len(homes) == 2 for homes in home_map.values())
    # Weeks should be 2*(n-1)
    max_week = max(fx["week"] for fx in fixtures)
    assert max_week + 1 == 2 * (len(team_ids) - 1)
