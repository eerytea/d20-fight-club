# tests/test_core_sim.py
from core.career import new_career
from core.sim import simulate_week_ai

def test_quick_demo_weeks():
    car = new_career(seed=7, team_count=20)
    # play three weeks
    for _ in range(3):
        simulate_week_ai(car)
    assert car.week == 4
    # all fixtures for weeks 1..3 should now be played
    assert all(f.played for f in car.fixtures if f.week <= 3)
    # table should have 20 rows and recorded games
    assert len(car.table) == 20
    assert sum(r.played for r in car.table.values()) > 0
