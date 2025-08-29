# tests/test_barbarian.py
from __future__ import annotations
from core.creator import generate_fighter
from core.classes import ensure_class_features, grant_starting_kit, apply_class_level_up
from core.ac import calc_ac
from tests.utils import make_melee, build_combat

def _force_barbarian(f):
    # If generator didn't pick Barbarian, force it and re-init
    f["class"] = "Barbarian"
    ensure_class_features(f)
    grant_starting_kit(f)
    return f

def test_barbarian_starting_kit_and_hp():
    f = generate_fighter(seed=101)
    f = _force_barbarian(f)
    inv = f.get("inventory", {})
    ws = inv.get("weapons", [])
    names = [w.get("name") for w in ws]
    assert "Greataxe" in names
    assert names.count("Hand Axe") >= 2
    # HP at L1 = 12 + CON mod
    expect_hp = 12 + (f["CON"] - 10)//2
    assert f["hp"] == expect_hp and f["max_hp"] >= expect_hp

def test_barbarian_unarmored_defense_beats_normal_when_con_high():
    f = generate_fighter(seed=202)
    f = _force_barbarian(f)
    f["DEX"] = 14; f["CON"] = 18  # DEX mod +2, CON mod +4
    f["armor_bonus"] = 0
    ac = calc_ac(f)
    # UD = 10 + 2 + 4 = 16; normal = 12; expect >= 16
    assert ac >= 16

def test_rage_bonus_damage_and_resistance_halving():
    # Make a Barbarian and a target, wire up a combat and manually rage then apply damage
    f = generate_fighter(seed=303); f = _force_barbarian(f)
    t = generate_fighter(seed=304)
    a = make_melee(1, 0, 5, 5); a.name = f["name"]; a.level = 7
    # copy rage fields onto engine fighter
    a.rage_active = True; a.resist_all = False; a.rage_bonus_per_level = 1
    d = make_melee(2, 1, 6, 5); d.name = t["name"]; d.hp = 40; d.max_hp = 40
    cmb = build_combat([a, d], seed=1)
    hp0 = d.hp
    cmb._apply_damage(a, d, 5)  # base 5; + level 7 => 12 total
    assert hp0 - d.hp == 12

    # Now test incoming resist_all
    d2 = make_melee(3, 1, 7, 5); d2.name = "Enemy"; a2 = make_melee(4, 0, 5, 6)
    a2.name = "Barb"; a2.hp = 40; a2.max_hp = 40; a2.resist_all = True
    cmb2 = build_combat([d2, a2], seed=2)
    hp0b = a2.hp
    cmb2._apply_damage(d2, a2, 11)
    assert hp0b - a2.hp == 11 // 2

def test_extra_attack_triggers_two_swings_at_level5():
    # Controller that issues a single 'attack' intent; engine should swing twice
    f = generate_fighter(seed=405); f = _force_barbarian(f)
    # level up to 5
    for L in range(2, 6): apply_class_level_up(f, L)
    a = make_melee(1, 0, 5, 5); a.name = f["name"]; a.level = 5; a.barb_extra_attacks = 1
    d = make_melee(2, 1, 6, 5); d.name = "Dummy"; d.hp = 999; d.max_hp = 999
    class Ctl:
        def decide(self, cmb, actor): return [{"type": "attack", "target": cmb.fighters[1]}]
    cmb = build_combat([a, d], seed=3); cmb.controllers[0] = Ctl()
    cmb.take_turn()
    # Count 'attack' events from the actor this turn (should be at least 2)
    attacks = [e for e in cmb.events if e.get("type") == "attack" and e.get("actor") == a.name]
    assert len(attacks) >= 2
