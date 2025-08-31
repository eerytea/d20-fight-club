from core.classes import ensure_class_features, grant_starting_kit

def mk(cls="Defender", **kw):
    p = {"class": cls, "level": kw.pop("level", 1),
         "STR":10,"DEX":10,"CON":10,"INT":10,"CHA":10, **kw}
    ensure_class_features(p)
    grant_starting_kit(p)
    return p

def test_defender_style_ac_bonus():
    d = mk("Defender", DEX=10)
    a = mk("Archer", DEX=10)
    assert d["ac"] == a["ac"] + 1

def test_enforcer_and_duelist_kits_present():
    e = mk("Enforcer")
    u = mk("Duelist")
    assert any(w["name"] == "Halberd" for w in e["inventory"]["weapons"])
    assert sum(1 for w in u["inventory"]["weapons"] if w["name"] == "Shortsword") >= 2
