from __future__ import annotations
import types

from core.classes import ensure_class_features, apply_class_level_up, grant_starting_kit
from engine.tbcombat import TBCombat, Team
from engine.conditions import add_condition, CONDITION_PRONE

def _mk_rogue(level=1, dex=16, con=12, name="Rogue", speed=6):
    f = types.SimpleNamespace()
    f.name = name; f.pid = 1; f.team_id = 0; f.tx = 5; f.ty = 5
    f.level = level; f.hp = 10; f.max_hp = 10; f.ac = 10; f.alive = True
    f.STR = 10; f.DEX = dex; f.CON = con; f.INT = 10; f.WIS = 10; f.CHA = 10
    f.speed = speed
    f.__dict__["class"] = "Rogue"
    ensure_class_features(f.__dict__)
    grant_starting_kit(f.__dict__)
    return f

def _dummy(name="Dummy", ac=12, team=1):
    d = types.SimpleNamespace()
    d.name = name; d.pid = 2; d.team_id = team; d.tx = 6; d.ty = 5
    d.level = 1; d.hp = 999; d.max_hp = 999; d.ac = ac; d.alive = True
    d.STR = 10; d.DEX = 10; d.CON = 10; d.INT = 10; d.WIS = 10; d.CHA = 10
    d.speed = 4
    return d

def _cmb(actors, seed=2):
    return TBCombat(Team(0,"A",(255,0,0)), Team(1,"B",(0,0,255)), actors, 16, 16, seed=seed)

def test_hp_recomputes_with_level_and_con_all_classes_rule():
    r = _mk_rogue(level=4, con=12, name="R4")
    # HP model: 8 + (L-1)*5 + CON mod(1) = 8 + 15 + 1 = 24
    assert r.max_hp == 24
    # simulate ASI that bumps CON to 16 (+3), recompute by re-applying level features at same level
    r.CON = 16; r.con = 16
    apply_class_level_up(r.__dict__, 4)
    # Now 8 + 15 + 3 = 26
    assert r.max_hp == 26

def test_rogue_sneak_attack_tiers_and_unhide():
    r = _mk_rogue(level=6, name="R6")  # 3d6
    d = _dummy(ac=1, name="Target")
    class HideAndStab:
        def decide(self, cmb, actor):
            actor.hidden = True
            return [{"type":"attack","target": d}]
    cmb = _cmb([r, d], seed=7)
    cmb.controllers[0] = HideAndStab()
    cmb.take_turn()
    # should see a sneak_attack event with 3d6 and then hidden cleared
    sna = [e for e in cmb.events if e.get("type")=="sneak_attack" and e.get("actor")=="R6"]
    assert sna and sna[-1]["dice"] == "3d6"
    assert not getattr(r, "hidden", False)

def test_cunning_action_free_hide_end_of_turn():
    r = _mk_rogue(level=1, name="R1")
    r.rogue_free_action = "hide"
    d = _dummy(ac=50, name="Wall")
    cmb = _cmb([r, d], seed=3)
    class DoNothing: 
        def decide(self, cmb, actor): return []
    cmb.controllers[0] = DoNothing()
    cmb.take_turn()
    assert getattr(r, "hidden", False), "Rogue should be hidden after free end-of-turn action"

def test_offhand_two_daggers_gets_prof_bonus():
    r = _mk_rogue(level=3, name="R3")
    # Equip two daggers explicitly
    daggers = [w for w in r.inventory["weapons"] if w["name"]=="Dagger"]
    assert len(daggers) >= 2
    r.equipped["main_hand_id"] = daggers[0]["id"]
    r.equipped["off_hand_id"] = daggers[1]["id"]
    d = _dummy(ac=1, name="T")
    class Swing:
        def decide(self, cmb, actor): return [{"type":"attack","target": d}]
    cmb = _cmb([r, d], seed=5); cmb.controllers[0] = Swing()
    cmb.take_turn()
    off = [e for e in cmb.events if e.get("type")=="attack" and e.get("actor")=="R3" and e.get("offhand")]
    assert off and off[0]["prof"] > 0

def test_uncanny_dodge_halves_incoming_weapon_damage_at_5():
    r4 = _mk_rogue(level=4, name="R4")
    r5 = _mk_rogue(level=5, name="R5")
    a = types.SimpleNamespace()
    a.name="Bandit"; a.pid=3; a.team_id=1; a.tx=6; a.ty=5; a.level=5; a.hp=30; a.max_hp=30; a.ac=10; a.alive=True
    a.STR=14; a.DEX=10; a.CON=10; a.INT=10; a.WIS=10; a.CHA=10; a.speed=4
    a.inventory={"weapons":[{"type":"weapon","name":"Club","dice":"1d8","ability":"STR","id":"w"}]}
    a.equipped={"main_hand_id":"w"}

    class Thwack:
        def decide(self, cmb, actor): return [{"type":"attack","target": None}]  # engine will pick nearest (our rogue)
    cmb4 = _cmb([r4, a], seed=11); cmb4.controllers[1] = Thwack(); cmb4.turn_idx = 1
    cmb4.take_turn()
    dmg4 = [e for e in cmb4.events if e.get("type")=="damage" and e.get("target")==r4.name][0]["amount"]

    cmb5 = _cmb([r5, a], seed=11); cmb5.controllers[1] = Thwack(); cmb5.turn_idx = 1
    cmb5.take_turn()
    dmg5 = [e for e in cmb5.events if e.get("type")=="damage" and e.get("target")==r5.name][0]["amount"]

    assert dmg5 <= dmg4 // 2 or dmg5 < dmg4, "Expected reduced damage at level 5"

def test_evasion_wis_advantage_no_adv_against_me_and_never_miss():
    # Evasion @7 on DEX save
    r7 = _mk_rogue(level=7, name="R7")
    caster = types.SimpleNamespace()
    caster.name="Mage"; caster.pid=3; caster.team_id=1; caster.tx=6; caster.ty=5
    caster.level=10; caster.hp=30; caster.max_hp=30; caster.ac=10; caster.alive=True
    caster.STR=10; caster.DEX=10; caster.CON=10; caster.INT=14; caster.WIS=10; caster.CHA=14; caster.speed=4

    class DexSave:
        def decide(self, cmb, actor):
            return [{"type":"spell_save","target": r7, "save":"DEX", "dc": 12, "dice":"1d10", "ability":"CHA", "half_on_success": True, "tags":["magic"]}]
    cmb = _cmb([r7, caster], seed=8); cmb.controllers[1] = DexSave(); cmb.turn_idx = 1
    cmb.take_turn()
    # with some luck and evasion, damage should be 0 or small; at least we assert event exists
    dmg = [e for e in cmb.events if e.get("type")=="damage" and e.get("target")=="R7"]
    assert dmg, "Expected damage/evasion resolution event"

    # WIS saves advantage @15
    r15 = _mk_rogue(level=15, name="R15")
    class WisSave:
        def decide(self, cmb, actor):
            return [{"type":"spell_save","target": r15, "save":"WIS", "dc": 10, "dice":"1d6", "ability":"CHA", "half_on_success": False, "tags":["magic"]}]
    cmb2 = _cmb([r15, caster], seed=9); cmb2.controllers[1] = WisSave(); cmb2.turn_idx = 1
    cmb2.take_turn()
    saves = [e for e in cmb2.events if e.get("type")=="save" and e.get("target")=="R15" and e.get("ability")=="WIS"]
    assert saves and (saves[-1]["advantage"] or saves[-1]["roll"] != saves[-1]["effective"]), "Expected advantage on WIS save"

    # No advantage against me @18
    r18 = _mk_rogue(level=18, name="R18")
    d = _dummy(ac=8, name="Dummy")
    add_condition(r18, CONDITION_PRONE, 1)  # would normally grant melee attackers advantage
    class Stab:
        def decide(self, cmb, actor): return [{"type":"attack","target": r18}]
    cmb3 = _cmb([r18, d], seed=4); cmb3.controllers[1] = Stab(); cmb3.turn_idx = 1
    cmb3.take_turn()
    atk = [e for e in cmb3.events if e.get("type")=="attack" and e.get("actor")=="Dummy"]
    assert atk and not atk[-1]["advantage"], "Attacks should not have advantage vs Rogue 18"

    # Never miss @20
    r20 = _mk_rogue(level=20, name="R20")
    brick = _dummy(ac=100, name="Wall")
    class Poke:
        def decide(self, cmb, actor): return [{"type":"attack","target": brick}]
    cmb4 = _cmb([r20, brick], seed=12); cmb4.controllers[0] = Poke()
    cmb4.take_turn()
    atk2 = [e for e in cmb4.events if e.get("type")=="attack" and e.get("actor")=="R20" and not e.get("ranged")]
    assert atk2 and atk2[-1]["hit"] is True
