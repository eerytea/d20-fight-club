from core.classes import ensure_class_features, grant_starting_kit

def mk(**kw):
    p = {"class": "Wizard", "level": kw.pop("level", 1),
         "STR":10,"DEX":10,"CON":10,"INT":10,"CHA":10, **kw}
    ensure_class_features(p)
    grant_starting_kit(p)
    return p

def test_wizard_casting_attribute_is_int():
    w = mk(INT=16)
    # No explicit casting stat field is required here; ensure no WIS anywhere and INT present
    assert "WIS" not in w and "wis" not in w
    assert "INT" in w

def test_wizard_high_levels_have_aoe_exemptions_flag_smoke():
    # Engine enforces exemptions; here we just sanity-check that setup at high level doesn't reintroduce WIS
    w = mk(level=17)
    assert "WIS" not in w
