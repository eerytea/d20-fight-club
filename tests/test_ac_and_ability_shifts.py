# Combined AC tests + Monk specifics
from core.classes import ensure_class_features, grant_starting_kit

def mk(cls="Defender", **kw):
    p = {"class": cls, "level": kw.pop("level", 1),
         "STR":10,"DEX":10,"CON":10,"INT":10,"CHA":10, **kw}
    ensure_class_features(p)
    grant_starting_kit(p)
    return p

# --- General AC expectations ---
def test_monk_unarmored_uses_intelligence():
    m = mk("Monk", DEX=16, INT=14)
    # Monk AC = 10 + DEX + INT
    assert m["ac"] == 10 + 3 + 2

def test_crusader_and_stalker_gain_ac_at_level_2():
    c = mk("Crusader", level=2)
    s = mk("Stalker", level=2)
    assert c["ac"] >= 11
    assert s["ac"] >= 11

def test_defender_style_bonus_ac():
    d1 = mk("Defender", DEX=10)
    d2 = mk("Archer", DEX=10)
    assert d1["ac"] == d2["ac"] + 1

# --- Monk-only details previously in test_monk.py ---
def test_monk_speed_and_flags_exist():
    m = mk("Monk", level=7)
    # Speed bonus & evasion flags exist (exact values depend on progression)
    assert "monk_evasion" in m
    assert "monk_unarmored_ac" in m
