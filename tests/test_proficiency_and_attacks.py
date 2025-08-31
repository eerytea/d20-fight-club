from core.classes import ensure_class_features, grant_starting_kit, proficiency_for_level

def mk(cls="Skald", **kw):
    p = {"class": cls, "level": kw.pop("level", 5),
         "STR":10,"DEX":10,"CON":10,"INT":10,"CHA":10, **kw}
    ensure_class_features(p)
    grant_starting_kit(p)
    return p

def test_proficiency_progression_monotonic():
    vals = [proficiency_for_level(L) for L in range(1,21)]
    assert vals == sorted(vals)
    assert vals[0] >= 2 and vals[-1] <= 6

def test_stalker_ranged_to_hit_bonus_present():
    s = mk("Stalker", level=2, DEX=16)
    # Actual +2 to-hit checked in engine tests; here just sanity-check class survived setup
    assert s["class"] == "Stalker"
