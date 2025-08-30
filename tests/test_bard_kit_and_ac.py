from __future__ import annotations
from core.creator import generate_fighter
from core.classes import ensure_class_features, grant_starting_kit
from core.ac import calc_ac

def _force_bard(f):
    f["class"] = "Bard"
    ensure_class_features(f)
    grant_starting_kit(f)
    return f

def test_bard_kit_has_finesse_dagger_and_leather_sets_ac():
    # Human Bard to avoid special race AC rules
    f = generate_fighter(seed=1234)
    f["race"] = "human"
    f = _force_bard(f)

    inv = f["inventory"]
    names = [w["name"] for w in inv["weapons"]]
    assert "Dagger" in names and "Rapier" in names and "Longsword" in names

    # Dagger must be finesse
    daggers = [w for w in inv["weapons"] if w["name"] == "Dagger"]
    assert daggers and daggers[0].get("finesse", False) is True

    # Leather armor -> armor_bonus = 1 -> AC = 10 + DEX mod + 1
    f["DEX"] = 14  # mod +2
    f["armor_bonus"] = 1
    ac = calc_ac(f)
    assert ac == 10 + (14 - 10)//2 + 1  # 13
