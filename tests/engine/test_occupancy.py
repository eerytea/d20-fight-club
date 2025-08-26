from engine.tbcombat import TBCombat

def make_f(pid, name, team, x, y):
    # simple object with the expected attributes
    class F: pass
    f = F()
    f.pid = pid
    f.name = name
    f.team_id = team
    f.x, f.y = x, y
    f.tx, f.ty = x, y
    f.hp = 10
    f.max_hp = 10
    f.alive = True
    return f

def test_spawn_collisions_are_resolved():
    fighters = [
        make_f(1, "A", 0, 1, 1),
        make_f(2, "B", 1, 1, 1),  # same tile as A
    ]
    tb = TBCombat("T0", "T1", fighters, GRID_W=6, GRID_H=6, seed=123)
    seen = set()
    for f in tb.fighters:
        assert (f.x, f.y) not in seen
        seen.add((f.x, f.y))

def test_blocked_event_on_occupied_move():
    a = make_f(1, "A", 0, 2, 2)
    b = make_f(2, "B", 1, 3, 2)
    tb = TBCombat("T0", "T1", [a, b], GRID_W=6, GRID_H=6, seed=123)

    # Force a to try stepping into b's tile directly
    before_len = len(tb.typed_events)
    tb._move_actor_if_free(a, (3, 2))  # internal helper; UI drives normal step_action()
    new_events = tb.typed_events[before_len:]
    assert (a.x, a.y) == (2, 2)
    assert any(ev.get("type") == "blocked" for ev in new_events)
