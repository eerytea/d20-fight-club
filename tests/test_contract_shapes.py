# tests/test_contract_shapes.py
from __future__ import annotations

from typing import Dict, Any, List

from core.contracts import (
    STAND_ROW_KEYS,
    EVENT_TYPES,
    FIXTURE_KEYS_REQ,
)
from core.career import Career
from core import schedule as _sched
from engine.tbcombat import TBCombat


def _has_all_keys(d: Dict[str, Any], req: set[str]) -> bool:
    return req.issubset(set(d.keys()))


def test_standings_row_keys_from_career_new():
    # Smaller league to keep things snappy
    car = Career.new(seed=1, n_teams=4, team_size=2, user_team_id=0)
    rows = car.table_rows_sorted()
    assert isinstance(rows, list) and len(rows) == 4
    for row in rows:
        assert _has_all_keys(row, STAND_ROW_KEYS), f"Row keys drifted: {row.keys()}"


def test_typed_events_shape():
    # Minimal fight, quick resolution so we definitely reach 'end'
    home = [
        {"pid": 0, "name": "H0", "team_id": 0, "hp": 3, "max_hp": 3, "ac": 8, "alive": True, "STR": 12, "DEX": 10, "CON": 10, "INT": 8, "WIS": 8, "CHA": 8},
        {"pid": 1, "name": "H1", "team_id": 0, "hp": 3, "max_hp": 3, "ac": 8, "alive": True, "STR": 12, "DEX": 10, "CON": 10, "INT": 8, "WIS": 8, "CHA": 8},
    ]
    away = [
        {"pid": 0, "name": "A0", "team_id": 1, "hp": 3, "max_hp": 3, "ac": 8, "alive": True, "STR": 12, "DEX": 10, "CON": 10, "INT": 8, "WIS": 8, "CHA": 8},
        {"pid": 1, "name": "A1", "team_id": 1, "hp": 3, "max_hp": 3, "ac": 8, "alive": True, "STR": 12, "DEX": 10, "CON": 10, "INT": 8, "WIS": 8, "CHA": 8},
    ]
    c = TBCombat("Home", "Away", home + away, grid_w=7, grid_h=7, seed=42)

    # Run to completion (bounded loop)
    for _ in range(500):
        if c.winner is not None:
            break
        c.take_turn()

    assert c.winner in (0, 1, None)
    assert c.typed_events, "No events emitted"

    # All event types must be from our contract
    for e in c.typed_events:
        et = e.get("type")
        assert et in EVENT_TYPES, f"Unknown event type: {et}"

        # If specific types appear, they should carry their expected fields
        if et == "round":
            assert "round" in e
        elif et == "move":
            assert "name" in e and "to" in e
        elif et == "hit":
            assert "name" in e and "target" in e and "dmg" in e
        elif et == "miss":
            assert "name" in e and "target" in e
        elif et == "blocked":
            assert "name" in e and "at" in e
        elif et == "end":
            assert "winner" in e

    # Last event should be 'end' for a concluded match
    assert c.typed_events[-1]["type"] == "end"


def test_schedule_fixture_keys_and_weeks():
    weeks = _sched.fixtures_double_round_robin(n_teams=4, start_week=1, comp_kind="league")
    assert isinstance(weeks, list) and len(weeks) > 0
    # Each week is a list of canonical fixtures with proper week numbering
    for w_index, wk in enumerate(weeks, start=1):
        assert isinstance(wk, list) and wk, f"Week {w_index} has no fixtures"
        for fx in wk:
            # must have canonical keys
            assert _has_all_keys(fx, FIXTURE_KEYS_REQ), f"Fixture keys drifted: {fx.keys()}"
            # week field matches the outer index (1-based)
            assert int(fx["week"]) == w_index
            # comp kind should be plumbed through
            assert fx.get("comp_kind") == "league"
            # played defaults to False
            assert fx.get("played") in (False, 0)


def test_career_fixtures_for_week_are_canonical():
    car = Career.new(seed=2, n_teams=6, team_size=1, user_team_id=0)
    wk1 = car.fixtures_for_week(1)
    assert isinstance(wk1, list) and wk1
    for fx in wk1:
        assert _has_all_keys(fx, FIXTURE_KEYS_REQ), f"Fixture keys drifted: {fx.keys()}"
        assert fx["week"] == 1
