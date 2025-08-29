# tests/test_creator_extras.py
from __future__ import annotations
from core.creator import generate_fighter
from core.ac import calc_ac
from core.constants import RACE_SPEED
from tests.utils import make_melee, build_combat

def test_race_speed_mapping_some_samples():
    assert generate_fighter(team={"race_weights":{"human":1.0}}, seed=1)["speed"] == RACE_SPEED["human"] == 6
    assert generate_fighter(team={"race_weights":{"wood_elf":1.0}}, seed=2)["speed"] == RACE_SPEED["wood_elf"] == 7
    assert generate_fighter(team={"race_weights":{"dwarf":1.0}}, seed=3)["speed"] == RACE_SPEED["dwarf"] == 5
    assert generate_fighter(team={"race_weights":{"goblin":1.0}}, seed=4)["speed"] == RACE_SPEED["goblin"] == 5

def test_golem_ac_has_plus_one():
    f = generate_fighter(team={"race_weights":{"golem":1.0}}, seed=10)
    # recompute to be explicit
    ac = calc_ac(f)
    # baseline 10+Dex+armor, then +1 for golem OR lizardkin override (not here)
    dex = f["DEX"]; armor = f.get("armor_bonus", 0)
    baseline = 10 + (dex - 10)//2 + armor
    assert ac == baseline + 1

def test_lizardkin_ac_formula_13_plus_dex():
    f = generate_fighter(team={"race_weights":{"lizardkin":1.0}}, seed=11)
    ac = calc_ac(f)
    expect = 13 + (f["DEX"] - 10)//2
    assert ac == expect

def test_goblin_damage_bonus_per_level_applies_globally():
    # Make a goblin and a target, then call _apply_damage via combat to avoid RNG on hitting
    gob = generate_fighter(team={"race_weights":{"goblin":1.0}}, seed=12)
    t = generate_fighter(team={"race_weights":{"human":1.0}}, seed=13)
    # Adapt to engine Fighter shape
    a = make_melee(1, 0, 5, 5, STR=10); a.name=gob["name"]; a.level=gob["level"]; a.dmg_bonus_per_level = gob.get("dmg_bonus_per_level",0)
    d = make_melee(2, 1, 6, 5, STR=10); d.name=t["name"]; d.hp = 30; d.max_hp = 30
    cmb = build_combat([a, d], seed=1)
    hp0 = d.hp
    cmb._apply_damage(a, d, 2)  # base damage 2 -> expect + level (1) = 3 total
    assert hp0 - d.hp == 2 + a.level
