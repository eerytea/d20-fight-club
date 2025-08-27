from __future__ import annotations

from engine.tbcombat import TBCombat

def make_unit(pid, team_id):
    # Small HP + low AC so fights resolve quickly
    return {
        "pid": pid,
        "name": f"T{team_id}U{pid}",
        "team_id": team_id,
        "hp": 3,
        "max_hp": 3,
        "ac": 8,
        "alive": True,
        "STR": 12, "DEX": 10, "CON": 10, "INT": 8, "WIS": 8, "CHA": 8,
    }

def test_engine_turns_and_end():
    home = [make_unit(i, 0) for i in range(3)]
    away = [make_unit(i, 1) for i in range(3)]
    fighters = home + away

    c = TBCombat("Home", "Away", fighters, grid_w=7, grid_h=7, seed=42)

    # Aliases exist
    assert c.events_typed is c.typed_events
    assert c.events is c.typed_events

    # First event is round marker
    assert len(c.typed_events) >= 1
    assert c.typed_events[0].get("type") == "round"

    # Alias method works
    c.step_action()  # same as take_turn

    # Run until someone wins (should be quick with hp=3)
    for _ in range(500):
        if c.winner is not None:
            break
        c.take_turn()

    # We should have a winner within reasonable steps
    assert c.winner in (0, 1)

    # Last event should be 'end' with winner
    assert c.typed_events[-1].get("type") == "end"
    assert c.typed_events[-1].get("winner") == c.winner

def test_move_blocked_event_out_of_bounds():
    home = [make_unit(0, 0)]
    away = [make_unit(0, 1)]
    fighters = home + away

    c = TBCombat("H", "A", fighters, grid_w=5, grid_h=5, seed=7)

    # Force a blocked move (out of bounds)
    a = c.fighters_all[0]
    prev_len = len(c.typed_events)
    c._move_actor_if_free(a, (-1, a.y))  # definitely out of bounds
    assert len(c.typed_events) == prev_len + 1
    assert c.typed_events[-1]["type"] == "blocked"
