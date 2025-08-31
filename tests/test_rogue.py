from core.classes import ensure_class_features, grant_starting_kit

def mk(**kw):
    p = {"class": "Rogue", "level": kw.pop("level", 1),
         "STR":10,"DEX":10,"CON":10,"INT":10,"CHA":10, **kw}
    ensure_class_features(p)
    grant_starting_kit(p)
    return p

def test_rogue_kit_and_no_wis():
    r = mk(DEX=14, INT=12)
    inv = r["inventory"]
    assert any(w["name"] in ("Shortsword","Dagger") for w in inv["weapons"])
    # Ensure wisdom is fully removed
    assert "WIS" not in r and "wis" not in r
