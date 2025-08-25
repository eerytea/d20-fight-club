from core.rng import child_seed, mix

def test_child_seed_stability():
    base = 1337
    a1 = child_seed(base, "preview:roster")
    a2 = child_seed(base, "preview:roster")
    b  = child_seed(base, "preview:schedule")
    assert a1 == a2
    assert a1 != b

def test_mix_composition():
    base = 42
    x = mix(base, "A", "B", "C")
    y = mix(mix(mix(base, "A"), "B"), "C")
    assert x == y
