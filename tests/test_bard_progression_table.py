from __future__ import annotations
from core.creator import generate_fighter
from core.classes import ensure_class_features, apply_class_level_up

def test_bard_spell_counts_progression_l1_l6_l20():
    f = generate_fighter(seed=777)
    f["class"] = "Bard"
    ensure_class_features(f)

    # L1
    assert f["cantrips_known"] == 2
    assert f["spells_known"] == 4
    assert f["spell_slots_total"][1] == 2

    # Level to 6
    for L in range(2, 7): apply_class_level_up(f, L)
    assert f["cantrips_known"] == 3
    assert f["spells_known"] == 9
    assert f["spell_slots_total"][3] == 3  # 3rd-level slots at L6: 0, but table has 0; ensure 0
    assert f["bard_aura_charm_fear"] is True

    # Level to 20
    for L in range(7, 21): apply_class_level_up(f, L)
    assert f["cantrips_known"] == 4
    assert f["spells_known"] == 22
    assert f["spell_slots_total"][7] >= 1  # high-level slots present
    assert f.get("bard_inspiration_unlimited", False) is True
