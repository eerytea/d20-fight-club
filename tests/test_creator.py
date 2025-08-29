# tests/test_creator.py
from __future__ import annotations

from core.creator import generate_fighter
from core.constants import RACES, DEV_TRAITS
from core.ac import calc_ac
from core.ratings import simulate_to_level

def test_generate_basic_fields():
    f = generate_fighter(seed=42)
    assert isinstance(f.get("name",""), str) and f["name"]
    assert f.get("race") in RACES
    assert isinstance(f.get("class",""), str) and f["class"]
    assert 18 <= int(f.get("age", 0)) <= 38
    assert 1 <= int(f.get("level", 0)) <= 20
    assert int(f.get("hp",0)) > 0 and int(f.get("max_hp",0)) >= int(f.get("hp",0))
    assert int(f.get("OVR",0)) >= 1
    assert int(f.get("potential",0)) >= int(f.get("OVR",0))

def test_origin_from_team_country():
    team = {"tid": 7, "country": "Avalon", "race_weights": {r: (1.0 if r=='human' else 0.0) for r in RACES}}
    f = generate_fighter(team=team, seed=7)
    assert f.get("origin") == "Avalon"
    assert f.get("race") == "human"

def test_racial_bonus_applied_high_elf_dex_int():
    team = {"race_weights": {r: (1.0 if r=='high_elf' else 0.0) for r in RACES}}
    f = generate_fighter(team=team, seed=123)
    dex = int(f.get("DEX", f.get("dex", 10)))
    expected_ac = 10 + (dex - 10)//2 + int(f.get("armor_bonus",0))
    assert f.get("ac") == expected_ac

def test_ac_formula_matches_helper():
    f = generate_fighter(seed=999)
    assert f["ac"] == calc_ac(f)

def test_dev_trait_sets_xp_rate():
    f = generate_fighter(seed=314)
    trait = f.get("dev_trait")
    assert trait in DEV_TRAITS
    assert abs(float(f.get("xp_rate", 0.0)) - DEV_TRAITS[trait]) < 1e-6

def test_potential_equals_simulated_level_20():
    f = generate_fighter(seed=2718)
    sim20 = simulate_to_level(f, 20)
    assert int(f.get("potential", 0)) == int(sim20.get("OVR", f["OVR"]))
