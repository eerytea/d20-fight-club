from __future__ import annotations
from tests.utils import make_melee, build_combat

def test_bard_inspiration_once_per_battle_then_fails():
    # One bard (L1), one ally, one enemy
    bard = make_melee(1, 0, 5, 5); bard.name = "Bard"; bard.level = 1
    setattr(bard, "class", "Bard")
    setattr(bard, "bard_inspiration_uses_per_battle", 1)
    ally = make_melee(2, 0, 6, 5); ally.name = "Ally"
    enemy = make_melee(3, 1, 7, 5); enemy.name = "Enemy"

    class Ctl:
        def decide(self, cmb, actor):
            if actor.name == "Bard":
                # Try to inspire twice in the same turn
                return [{"type":"inspire","target":ally},{"type":"inspire","target":ally}]
            return [{"type":"attack","target": enemy if actor is ally else ally}]
    cmb = build_combat([bard, ally, enemy], seed=1)
    cmb.controllers[0] = Ctl()
    cmb.controllers[1] = Ctl()
    cmb.take_turn()  # Bard turn
    insp_events = [e for e in cmb.events if e.get("type") == "inspire"]
    assert len(insp_events) == 2
    assert insp_events[0].get("failed") is None
    assert insp_events[1].get("failed") is True

def test_bard_level6_aura_grants_advantage_on_charm_saves():
    # Ally making a save vs charm within 6 of a level 6 Bard
    bard = make_melee(1, 0, 5, 5); bard.name = "Bard"; bard.level = 6
    setattr(bard, "class", "Bard")
    setattr(bard, "bard_aura_charm_fear", True)
    ally = make_melee(2, 0, 9, 5)  # distance 4, inside 6
    enemy = make_melee(3, 1, 12, 5)

    cmb = build_combat([bard, ally, enemy], seed=2)
    # Trigger a save on ally directly (tagged 'charm')
    res = cmb.saving_throw(ally, "WIS", 12, tags=["charm"])
    # The event right after should show a tuple roll when advantage applied
    save_evts = [e for e in cmb.events if e.get("type") == "save"]
    assert save_evts, "expected a save event"
    roll_field = save_evts[-1]["roll"]
    assert isinstance(roll_field, tuple), "expected advantage (tuple roll) due to bard aura"
