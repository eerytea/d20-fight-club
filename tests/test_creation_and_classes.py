import pytest

from core.classes import ensure_class_features, grant_starting_kit, apply_class_level_up, proficiency_for_level

def make_player(cls, level=1, **stats):
    p = {
        "name": f"{cls} L{level}",
        "class": cls,
        "level": level,
        "STR": 10, "DEX": 10, "CON": 10, "INT": 10, "CHA": 10,
        **stats,
    }
    ensure_class_features(p)
    grant_starting_kit(p)
    if level > 1:
        for L in range(2, level + 1):
            apply_class_level_up(p, L)
    return p

def test_class_aliases_backwards_compat():
    for old, new in [
        ("Barbarian","Berserker"),
        ("Bard","Skald"),
        ("Cleric","War Priest"),
        ("Ranger","Stalker"),
        ("Paladin","Crusader"),
    ]:
        p = make_player(old, level=1)
        assert p["class"] == new

def test_standard_array_is_five_values_only():
    # Your project’s creation code should return 5 values; assert shape here if exposed.
    # If you don’t expose a roller, at least assert that players never have WIS.
    p = make_player("Wizard", level=1)
    assert "WIS" not in p and "wis" not in p

def test_hp_retro_with_dynamic_con():
    p = make_player("Crusader", level=5, CON=14)  # base 10 + 6*(lvl-1)=10+24=34 + CON mod (+2) => 36 max_hp
    assert p["max_hp"] == 36
    # Increase CON later; retro add should increase max_hp by +1 per +2 CON (mod bump)
    p["CON"] = 16
    ensure_class_features(p)  # recompute AC/HP
    assert p["max_hp"] == 37  # +1 from CON mod increase

def test_starting_kits_present():
    for cls in ["Berserker","Skald","War Priest","Druid","Archer","Defender","Enforcer","Duelist","Monk","Rogue","Stalker","Wizard","Crusader"]:
        p = make_player(cls)
        inv = p["inventory"]
        assert "weapons" in inv
        # Unarmed always present
        assert any(w.get("unarmed") for w in inv["weapons"])
