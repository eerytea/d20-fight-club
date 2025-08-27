# tests/test_contract_shapes.py
from __future__ import annotations
from core.contracts import STAND_ROW_KEYS, EVENT_TYPES, FIXTURE_KEYS_REQ
from core.career import Career
from core import schedule as _sched
from engine.tbcombat import TBCombat

def _has_all_keys(d, req): return req.issubset(set(d.keys()))

def test_standings_row_keys_from_career_new():
    car = Career.new(seed=1, n_teams=4, team_size=2, user_team_id=0)
    rows = car.table_rows_sorted()
    assert isinstance(rows, list) and len(rows) == 4
    for row in rows:
        assert _has_all_keys(row, STAND_ROW_KEYS), f"Row keys drifted: {row.keys()}"

def test_typed_events_shape():
    home = [{"pid": i, "name": f"H{i}", "team_id": 0, "hp": 3, "max_hp": 3, "ac": 8, "alive": True,
             "STR": 12, "DEX": 10, "CON": 10, "INT": 8, "WIS": 8, "CHA": 8} for i in range(2)]
    away = [{"pid": i, "name": f"A{i}", "team_id": 1, "hp": 3, "max_hp": 3, "ac": 8, "alive": True,
             "STR": 12, "DEX": 10, "CON": 10, "INT": 8, "WIS": 8, "CHA": 8} for i in range(2)]
    c = TBCombat("Home", "Away", home + away, grid_w=7, grid_h=7, seed=42)
    for _ in range(500):
        if c.winner is not None: break
        c.take_turn()
    assert c.typed_events, "No events emitted"
    for e in c.typed_events:
        et = e.get("type")
        assert et in EVENT_TYPES, f"Unknown event type: {et}"
        if et == "round":   assert "round" in e
        if et == "move":    assert "name" in e and "to" in e
        if et == "hit":     assert "name" in e and "target" in e and "dmg" in e
        if et == "miss":    assert "name" in e and "target" in e
        if et == "blocked": assert "name" in e and "at" in e
        if et == "end":     assert "winner" in e
    assert c.typed_events[-1]["type"] == "end"

def test_schedule_fixture_keys_and_weeks():
    weeks = _sched.fixtures_double_round_robin(n_teams=4, start_week=1, comp_kind="league")
    assert isinstance(weeks, list) and len(weeks) > 0
    for w_index, wk in enumerate(weeks, start=1):
        assert isinstance(wk, list) and wk, f"Week {w_index} has no fixtures"
        for fx in wk:
            assert _has_all_keys(fx, FIXTURE_KEYS_REQ), f"Fixture keys drifted: {fx.keys()}"
            assert int(fx["week"]) == w_index
            assert fx.get("comp_kind") == "league"
            assert fx.get("played") in (False, 0)

def test_career_fixtures_for_week_are_canonical():
    car = Career.new(seed=2, n_teams=6, team_size=1, user_team_id=0)
    wk1 = car.fixtures_for_week(1)
    assert isinstance(wk1, list) and wk1
    for fx in wk1:
        assert _has_all_keys(fx, FIXTURE_KEYS_REQ)
        assert fx["week"] == 1
