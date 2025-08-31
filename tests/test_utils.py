def mod(v: int) -> int:
    return (int(v) - 10) // 2

def test_mod_helper_symmetric():
    assert mod(10) == 0
    assert mod(8) == -1
    assert mod(12) == 1
    assert mod(16) == 3  # common case in our tests

def test_no_wis_in_stat_blocks_sample():
    sample = {"STR":10,"DEX":10,"CON":10,"INT":10,"CHA":10}
    assert "WIS" not in sample and "wis" not in sample
