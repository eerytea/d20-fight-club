from core.classes import ensure_class_features, grant_starting_kit

def mk(cls, **kw):
    p = {"class": cls, "level": kw.pop("level", 1),
         "STR":10,"DEX":10,"CON":10,"INT":10,"CHA":10, **kw}
    ensure_class_features(p); grant_starting_kit(p)
    return p

def test_monk_unarmored_uses_intelligence():
    m = mk("Monk", DEX=16, INT=14)
    assert m["ac"] == 10 + 3 + 2

def test_defender_style_bonus_ac():
    d1 = mk("Defender", DEX=10)
    d2 = mk("Archer", DEX=10)
    assert d1["ac"] == d2["ac"] + 1

def test_crusader_and_stalker_gain_ac_at_level_2():
    c = mk("Crusader", level=2)
    s = mk("Stalker", level=2)
    # With default 10/10/10 stats and starter gear, they each net +1 from class rules
    assert c["ac"] >= 11
    assert s["ac"] >= 11

def test_no_wis_anywhere_on_player():
    p = mk("Wizard")
    keys = {k.lower() for k in p.keys()}
    assert "wis" not in keys
