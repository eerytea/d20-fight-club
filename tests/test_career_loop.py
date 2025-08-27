# tests/test_career_loop.py
from __future__ import annotations
from core.career import Career

def _user_fixture_for_week(car, w):
    for fx in car.fixtures_for_week(w):
        if str(fx["home_id"]) == str(car.user_tid) or str(fx["away_id"]) == str(car.user_tid):
            return fx
    return None

def test_sim_week_leaves_user_match_and_advances_after_finish():
    car = Career.new(seed=3, n_teams=4, team_size=2, user_team_id=0)
    wk = car.week
    user_fx = _user_fixture_for_week(car, wk)
    assert user_fx is not None

    # Sim AI-vs-AI — should not advance week because user's match remains
    car.simulate_week_ai()
    assert car.week == wk
    # User plays their match (record a simple 1–0)
    h, a = user_fx["home_id"], user_fx["away_id"]
    car.record_result({"home_id": h, "away_id": a, "k_home": 1, "k_away": 0, "winner": 0})

    # Call simulate again to trigger "all played? then advance"
    car.simulate_week_ai()
    assert car.week == wk + 1

def test_save_load_migration_and_bootstrap():
    # Fabricate an old-ish save dict (flat fixtures with aliases)
    old = {
        "seed": 9, "week": 1, "user_tid": 0,
        "teams": [{"tid": 0, "name": "A", "fighters": []}, {"tid": 1, "name": "B", "fighters": []}],
        "fixtures": [{"week": 1, "home_tid": 0, "away_tid": 1, "played": False, "k_home": 0, "k_away": 0, "winner": None}],
        # missing fixtures_by_week, no reputation/staff
    }
    car = Career.from_dict(old)
    # fixtures_by_week should be synthesized
    assert isinstance(car.fixtures_by_week, list) and car.fixtures_by_week
    # reputation/staff bootstrapped
    assert isinstance(car.reputation, dict) and "clubs" in car.reputation
    assert isinstance(car.staff, dict) and "by_club" in car.staff
