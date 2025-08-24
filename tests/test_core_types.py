# tests/test_core_types.py
from core.types import Career, Fixture, TableRow

def test_career_json_roundtrip():
    car = Career(
        seed=42,
        week=3,
        team_names=["A", "B"],
        team_colors=[(100,120,140), (150,90,60)],
        rosters={0: [], 1: []},
        fixtures=[Fixture(week=1, home_id=0, away_id=1, home_goals=2, away_goals=1, played=True)],
        table={0: TableRow(team_id=0, name="A", played=1, wins=1, goals_for=2, goals_against=1, points=3)}
    )
    s = car.to_json()
    car2 = Career.from_json(s)
    assert car2.seed == car.seed
    assert car2.week == car.week
    assert car2.team_names == car.team_names
    assert car2.fixtures[0].played is True
    assert car2.table[0].points == 3
