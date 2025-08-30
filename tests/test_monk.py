from __future__ import annotations
import types

from core.classes import ensure_class_features, apply_class_level_up, grant_starting_kit
from engine.tbcombat import TBCombat, Team

def _mk_monk(lvl=1, dex=14, wis=14, con=10, race_unarmed=None, speed=6, name="Monk"):
    a = types.SimpleNamespace()
    a.name = name; a.pid = 1; a.team_id = 0; a.tx = 5; a.ty = 5
    a.level = lvl; a.hp = 10; a.max_hp = 10; a.ac = 10; a.alive = True
    a.STR = 10; a.DEX = dex; a.CON = con; a.INT = 10; a.WIS = wis; a.CHA = 10
    a.speed = speed
    a.__dict__["class"] = "Monk"
    if race_unarmed:
        a.unarmed_dice = race_unarmed  # e.g., "1d6" from race
    ensure_class_features(a.__dict__)
    grant_starting_kit(a.__dict__)
    return a

def _dummy(name="Dummy", ac=10, team=1):
    d = types.SimpleNamespace()
    d.name = name; d.pid = 2; d.team_id = team; d.tx = 6; d.ty = 5
    d.level = 1; d.hp = 999; d.max_hp = 999; d.ac = ac; d.alive = True
    d.STR = 10; d.DEX = 10; d.CON = 10; d.INT = 10; d.WIS = 10; d.CHA = 10
    d.speed = 4
    return d

def _cmb(actors, seed=2):
    return TBCombat(Team(0,"A",(255,0,0)), Team(1,"B",(0,0,255)), actors, 16, 16, seed=seed)

def test_monk_unarmored_ac_and_hp_speed_and_die_progression():
    m = _mk_monk(lvl=1, dex=14, wis=14, con=12, race_unarmed="1d6", speed=6, name="M1")
    # AC = 10 + DEX(2) + WIS(2) = 14 (no armor/shield)
    assert m.ac == 14
    # HP = 8 + CON mod(1) at L1
    assert m.hp >= 9 and m.max_hp >= 9
    # Unarmed die at L1 should be max(race 1d6, monk 1d4) => 1d6
    assert m.unarmed_dice == "1d6"
    # Level to 5: speed bonus becomes +2 (replaces), unarmed stays 1d6 (vs monk 1d6)
    for L in range(2, 6): apply_class_level_up(m.__dict__, L)
    assert m.speed == 6 + 2
    assert m.unarmed_dice == "1d6"
    # Level to 11: die becomes 1d8 (beats race 1d6), speed bonus +3 at L6, +4 at L10 (replaced)
    for L in range(6, 12): apply_class_level_up(m.__dict__, L)
    assert m.unarmed_dice == "1d8"
    assert m.speed == 6 + 4
    # Level to 17: die 1d10
    for L in range(12, 18): apply_class_level_up(m.__dict__, L)
    assert m.unarmed_dice == "1d10"

def test_monk_offhand_unarmed_prof_before_15_and_with_weapon_after_15():
    # Pre-15: off-hand unarmed allowed and should add prof only if both are unarmed
    m = _mk_monk(lvl=10, dex=10, wis=10, name="Monk10")
    d = _dummy(ac=1)
    class PunchTwice:
        def decide(self, cmb, actor): return [{"type":"attack","target": d}]
    cmb = _cmb([m, d], seed=5); cmb.controllers[0] = PunchTwice()
    cmb.take_turn()
    off = [e for e in cmb.events if e.get("type")=="attack" and e.get("actor")=="Monk10" and e.get("offhand")]
    assert off, "Expected an off-hand unarmed attempt"
    assert off[0]["prof"] > 0  # off-hand prof because both are unarmed

    # At 15: even with a weapon equipped, off-hand uses proficiency
    m2 = _mk_monk(lvl=15, dex=10, wis=10, name="Monk15")
    # Give a simple dagger as off-hand weapon
    m2.inventory["weapons"].append({"type":"weapon","name":"Dagger","dice":"1d4","finesse":True,"id":"w_dag"})
    m2.equipped["off_hand_id"] = "w_dag"
    d2 = _dummy(ac=1, name="D2")
    cmb2 = _cmb([m2, d2], seed=6); cmb2.controllers[0] = PunchTwice()
    cmb2.take_turn()
    off2 = [e for e in cmb2.events if e.get("type")=="attack" and e.get("actor")=="Monk15" and e.get("offhand")]
    assert off2 and off2[0]["prof"] > 0

def test_monk_bonus_unarmed_after_two_unarmed_main_swings():
    # At L11 monk has +1 extra attack (so 2 main-hand swings) -> should get one bonus unarmed if both are unarmed
    m = _mk_monk(lvl=11, dex=10, wis=10, name="Monk11")
    d = _dummy(ac=1, name="DummyB")
    class AttackOnce:
        def decide(self, cmb, actor): return [{"type":"attack","target": d}]
    cmb = _cmb([m, d], seed=4); cmb.controllers[0] = AttackOnce()
    cmb.take_turn()
    mains = [e for e in cmb.events if e.get("type")=="attack" and e.get("actor")=="Monk11" and not e.get("offhand")]
    # 2 main swings + 1 bonus unarmed = 3
    assert len(mains) == 3
    bonus_tag = [e for e in cmb.events if e.get("type")=="attack_bonus_unarmed" and e.get("actor")=="Monk11"]
    assert bonus_tag, "Expected a bonus unarmed marker event"

def test_deflect_missiles_reduces_ranged_damage_to_zero_in_easy_case():
    # Make reduction large: level 10, DEX mod +2; attacker deals tiny damage with a ranged weapon
    m = _mk_monk(lvl=10, dex=14, wis=10, name="MonkDM"); m.ac = 1  # ensure hit
    a = types.SimpleNamespace()
    a.name="Archer"; a.pid=3; a.team_id=1; a.tx=6; a.ty=5; a.level=1; a.hp=20; a.max_hp=20; a.ac=10; a.alive=True
    a.STR=10; a.DEX=10; a.CON=10; a.INT=10; a.WIS=10; a.CHA=10; a.speed=4
    a.inventory={"weapons":[{"type":"weapon","name":"Test Bow","dice":"1d1","ranged":True,"ability":"DEX","range":(8,16),"id":"wbow"}]}
    a.equipped={"main_hand_id":"wbow"}
    d = _dummy(ac=1)  # unused
    cmb = _cmb([m, a], seed=9)
    class Shoot:
        def decide(self, cmb, actor): 
            return [{"type":"attack","target": m}]
    cmb.controllers[1] = Shoot()
    cmb.turn_idx = 1  # make archer go first for test determinism
    cmb.take_turn()
    dmgs = [e for e in cmb.events if e.get("type")=="damage" and e.get("target")=="MonkDM"]
    assert dmgs and all(e["amount"] == 0 for e in dmgs), "Expected ranged damage reduced to 0"

def test_evasion_and_global_save_advantage_and_poison_immunity():
    # Monk L14: global save advantage; L10+: poison immune
    m = _mk_monk(lvl=14, dex=14, wis=12, name="MonkSav")
    target = _dummy(ac=1, name="T")
    cmb = _cmb([m, target], seed=12)
    # Cast DEX save spell that normally halves on success
    class CastDexSave:
        def decide(self, cmb, actor):
            return [{"type":"spell_save","target": m, "save":"DEX", "dc": 10, "dice":"1d8", "ability":"CHA", "half_on_success": True, "tags":["magic"]}]
    caster = types.SimpleNamespace()
    caster.name="Mage"; caster.pid=3; caster.team_id=1; caster.tx=6; caster.ty=5; caster.level=10; caster.hp=30; caster.max_hp=30; caster.ac=10; caster.alive=True
    caster.STR=10; caster.DEX=10; caster.CON=10; caster.INT=14; caster.WIS=10; caster.CHA=14; caster.speed=4
    cmb.fighters.append(caster); cmb.controllers[1] = CastDexSave()
    cmb.turn_idx = 2  # mage turn
    cmb.take_turn()
    # With advantage and decent Dex, expect save success often -> damage 0. Seeded for determinism.
    dmg = [e for e in cmb.events if e.get("type")=="damage" and e.get("target")=="MonkSav"]
    assert dmg and dmg[-1]["amount"] == 0

    # Poison immunity: spell attack with poison damage should do 0
    class PoisonBolt:
        def decide(self, cmb, actor):
            return [{"type":"spell_attack","target": m, "dice":"1d6", "ability":"CHA", "normal_range":12, "long_range":24, "damage_type":"poison"}]
    cmb2 = _cmb([m, caster], seed=13); cmb2.controllers[1] = PoisonBolt()
    cmb2.turn_idx = 1
    cmb2.take_turn()
    dmg2 = [e for e in cmb2.events if e.get("type")=="damage" and e.get("target")=="MonkSav"]
    assert dmg2 and dmg2[-1]["amount"] == 0

def test_monk_extra_attacks_at_5_and_20():
    m5 = _mk_monk(lvl=5, name="Monk5"); d = _dummy(ac=1, name="D")
    class AttackOnce:
        def decide(self, cmb, actor): return [{"type":"attack","target": d}]
    cmb = _cmb([m5, d], seed=3); cmb.controllers[0] = AttackOnce()
    cmb.take_turn()
    mains5 = [e for e in cmb.events if e.get("type")=="attack" and e.get("actor")=="Monk5" and not e.get("offhand")]
    assert len(mains5) >= 2  # 1 base +1 extra

    m20 = _mk_monk(lvl=20, name="Monk20"); d2 = _dummy(ac=1, name="D2")
    cmb2 = _cmb([m20, d2], seed=4); cmb2.controllers[0] = AttackOnce()
    cmb2.take_turn()
    mains20 = [e for e in cmb2.events if e.get("type")=="attack" and e.get("actor")=="Monk20" and not e.get("offhand")]
    assert len(mains20) >= 3  # 1 base +2 extra at 20
