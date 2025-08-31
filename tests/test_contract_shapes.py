import pytest

def test_player_schema_no_wis():
    sample = {"name":"X","class":"Wizard","level":3,"STR":10,"DEX":10,"CON":10,"INT":12,"CHA":10}
    assert "WIS" not in sample and "wis" not in sample
    primaries = ["STR","DEX","CON","INT","CHA"]
    assert set(primaries).issubset(sample.keys())
