from core.schedule import build_double_round_robin

def test_double_round_robin_properties():
    team_ids = list(range(6))
    fx = build_double_round_robin(team_ids, rounds=2, shuffle_seed=42)
    # Every pair meets exactly twice (home/away), and no team plays itself.
    pair_counts = {}
    for f in fx:
        assert f["home_id"] != f["away_id"]
        a, b = sorted([f["home_id"], f["away_id"]])
        pair_counts[(a,b)] = pair_counts.get((a,b), 0) + 1
    for i in range(len(team_ids)):
        for j in range(i+1, len(team_ids)):
            assert pair_counts.get((i,j), 0) == 2
