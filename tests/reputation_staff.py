# tests/test_reputation_staff.py
from __future__ import annotations
from core.career import Career

def test_reputation_updates_on_result_and_staff_seeded():
    car = Career.new(seed=4, n_teams=4, team_size=1, user_team_id=0)
    # Pick two teams from week 1 and award home a win
    fx = car.fixtures_for_week(1)[0]
    h, a = fx["home_id"], fx["away_id"]

    # Elo before
    r_before_h = car.reputation["clubs"][str(h)]
    r_before_a = car.reputation["clubs"][str(a)]

    car.record_result({"home_id": h, "away_id": a, "k_home": 2, "k_away": 0, "winner": 0})

    r_after_h = car.reputation["clubs"][str(h)]
    r_after_a = car.reputation["clubs"][str(a)]
    assert r_after_h != r_before_h and r_after_a != r_before_a
    assert r_after_h > r_before_h
    assert r_after_a < r_before_a

    # Staff should be seeded for each club
    by_club = car.staff.get("by_club", {})
    assert by_club and all(k in by_club for k in (str(h), str(a)))
    for tid, roles in by_club.items():
        assert set(roles.keys()) == {"coach", "scout", "physio"}
