# tests/test_engine_smoke.py
from __future__ import annotations
from engine.tbcombat import TBCombat

def make_unit(pid, team_id):
    return {
        "pid": pid, "name": f"T{team_id}U{pid}", "team_id": team_id,
        "hp": 3, "max_hp": 3, "ac": 8, "alive": True,
        "STR": 12, "DEX": 10, "CON": 10, "INT": 8, "WIS": 8, "CHA": 8,
    }

def test_engine_turns_and_end_and_aliases():
    fighters = [make_unit(i, 0) for i in range(3)] + [make_unit(i, 1) for i in range(3)]
    c = TBCombat("Home", "Away", fighters, grid_w=7, grid_h=7, seed=42)
    assert c.events_typed is c.typed_events
    assert c.events is c.typed_events
    assert c.typed_events[0].get("type") == "round"
    c.step_action()
    for _ in range(500):
        if c.winner is not None: break
        c.take_turn()
    assert c.winner in (0, 1)
    assert c.typed_events[-1].get("type") == "end"
    assert c.typed_events[-1].get("winner") == c.winner

def test_occupancy_and_blocked():
    fighters = [make_unit(0,0), make_unit(1,0), make_unit(0,1), make_unit(1,1)]
    c = TBCombat("H", "A", fighters, grid_w=5, grid_h=5, seed=7)
    # positions must be unique (single occupancy)
    coords = [(a.x, a.y) for a in c.fighters_all if a.alive]
    assert len(coords) == len(set(coords))
    # blocked when moving out of bounds
    a = c.fighters_all[0]
    n0 = len(c.typed_events)
    c._move_actor_if_free(a, (-1, a.y))
    assert len(c.typed_events) == n0 + 1
    assert c.typed_events[-1]["type"] == "blocked"
    # blocked when moving onto occupied tile
    b = c.fighters_all[1]
    n1 = len(c.typed_events)
    c._move_actor_if_free(b, (a.x, a.y))
    assert len(c.typed_events) == n1 + 1
    assert c.typed_events[-1]["type"] == "blocked"
