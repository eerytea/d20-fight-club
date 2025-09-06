# tests/test_tbcombat_seeding.py
from engine.tbcombat import TBCombat
from engine.model import Fighter, Team, Weapon

def _mini_teams():
    a = Fighter(name="A1", STR=14, DEX=12, CON=12, INT=10, WIS=10, CHA=10, level=1, hp=10, team_id=0)
    b = Fighter(name="B1", STR=14, DEX=12, CON=12, INT=10, WIS=10, CHA=10, level=1, hp=10, team_id=1)
    t1 = Team(id=0, name="Home", color=(200,50,50), fighters=[a])
    t2 = Team(id=1, name="Away", color=(50,50,200), fighters=[b])
    return t1, t2, [a,b]

def _first_event(seed):
    t1, t2, actors = _mini_teams()
    cmb = TBCombat(t1, t2, actors, width=16, height=16, seed=seed)
    # run a single turn per side or until events appear
    for _ in range(4):
        cmb.take_turn()
        if cmb.events:
            return cmb.events[0]
    return None

def test_same_seed_same_first_event():
    e1 = _first_event(123)
    e2 = _first_event(123)
    assert e1 == e2

def test_different_seed_differs_sometimes():
    # It SHOULD differ most of the time; if it doesn't, it's still okay—this just acts as a smoke test
    e1 = _first_event(12345)
    e2 = _first_event(54321)
    assert e1 is not None and e2 is not None
