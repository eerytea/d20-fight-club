# tests/engine/test_race_perks.py
from __future__ import annotations
from core.creator import generate_fighter
from tests.utils import make_melee, build_combat, set_initiative_order
from engine.tbcombat import TBCombat

def test_dwarf_extra_hp_at_l1():
    d = generate_fighter(team={"race_weights":{"dwarf":1.0}}, seed=1)
    base_con = d["CON"]
    # min expected hp = 10 + con mod + 1
    expect_min = 10 + (base_con - 10)//2 + 1
    assert d["max_hp"] >= expect_min

def test_lizardkin_unarmed_die():
    liz = generate_fighter(team={"race_weights":{"lizardkin":1.0}}, seed=2)
    assert liz.get("unarmed_dice") == "1d6"

def test_elf_sleep_immunity_prevents_condition():
    caster = make_melee(1, 0, 5, 5)
    elf = generate_fighter(team={"race_weights":{"high_elf":1.0}}, seed=3)
    tgt = make_melee(2, 1, 6, 5); tgt.name = elf["name"]; tgt.sleep_immune = True
    cmb = build_combat([caster, tgt], seed=3)
    set_initiative_order(cmb, [1, 2])
    # Simulate a sleep spell save that fails and would apply 'sleep'
    cmb._cast_spell_save(caster=cmb.fighters[0], target=cmb.fighters[1], save="WIS", dc=30, dice=None,
                         tags=["magic","sleep"], apply_condition_on_fail=("sleep", 1))
    # Should log condition_ignored instead of condition_applied
    names = [e["type"] for e in cmb.events if e.get("type") in ("condition_applied","condition_ignored")]
    assert "condition_ignored" in names and "condition_applied" not in names

def test_dwarf_poison_advantage_and_resistance():
    d = generate_fighter(team={"race_weights":{"dwarf":1.0}}, seed=4)
    atk = make_melee(1, 0, 5, 5); tgt = make_melee(2, 1, 6, 5)
    # copy dwarf flags onto tgt test fighter
    for k in ("adv_vs_poison","poison_resist"):
        setattr(tgt, k, d.get(k, False))
    cmb = build_combat([atk, tgt], seed=4)
    # Force a poison save
    cmb.saving_throw(tgt, "CON", 12, tags=["poison"])
    saves = [e for e in cmb.events if e.get("type") == "save"]
    assert saves[-1]["advantage"] is True
    # Apply poison damage and verify halved
    hp0 = tgt.hp
    cmb._apply_damage(atk, tgt, 7, damage_type="poison")
    assert hp0 - tgt.hp == 7 // 2

def test_gnome_mental_magic_advantage():
    g = generate_fighter(team={"race_weights":{"gnome":1.0}}, seed=5)
    tgt = make_melee(1, 0, 5, 5);  # reuse as gnome target to check save
    tgt.adv_vs_magic_mental = g.get("adv_vs_magic_mental", False)
    cmb = build_combat([tgt, make_melee(2,1,6,5)], seed=5)
    cmb.saving_throw(tgt, "WIS", 12, tags=["magic"])
    saves = [e for e in cmb.events if e.get("type") == "save"]
    assert saves[-1]["advantage"] is True
