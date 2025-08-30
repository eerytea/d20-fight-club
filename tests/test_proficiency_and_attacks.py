from __future__ import annotations
from tests.utils import make_melee, build_combat

def test_weapon_attack_damage_includes_proficiency_bonus():
    # Bard L5 -> proficiency +3; STR/DEX 10 so no ability bonus; weapon 1d1 for deterministic base=1
    a = make_melee(1, 0, 5, 5); a.name = "Bard"; a.level = 5
    setattr(a, "class", "Bard")
    a.STR = 10; a.DEX = 10
    a.weapon = {"type":"weapon","name":"Test1","dice":"1d1","reach":1,"ability":"STR"}

    d = make_melee(2, 1, 6, 5); d.name = "Dummy"; d.hp = 999; d.max_hp = 999; d.ac = 1  # auto-hit

    class C:
        def decide(self, cmb, actor):
            return [{"type": "attack", "target": d}]
    cmb = build_combat([a, d], seed=3); cmb.controllers[0] = C()
    hp0 = d.hp
    cmb.take_turn()
    dmg = hp0 - d.hp
    # At least base(1) + prof(3) == 4; crit would be >= 5, so >= 4 is robust
    assert dmg >= 4

def test_spell_save_dc_uses_prof_plus_cha_when_not_provided():
    # Bard L5 (prof 3), CHA 18 (+4) -> DC 15
    caster = make_melee(1, 0, 5, 5); caster.name = "Bard"; caster.level = 5
    setattr(caster, "class", "Bard")
    caster.CHA = 18
    target = make_melee(2, 1, 6, 5); target.name = "Target"
    class Ctl:
        def decide(self, cmb, actor):
            if actor is caster:
                return [{"type":"spell_save","target": target, "save":"DEX", "dice": None}]
            return []
    cmb = build_combat([caster, target], seed=4)
    cmb.controllers[0] = Ctl(); cmb.controllers[1] = Ctl()
    cmb.take_turn()
    save_evts = [e for e in cmb.events if e.get("type") == "save" and e.get("target") == target.name]
    assert save_evts, "expected a save event"
    assert save_evts[-1]["dc"] == 15
