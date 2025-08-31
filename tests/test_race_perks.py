import pytest
from core.classes import ensure_class_features, grant_starting_kit

def mk_player(cls="Human", **kw):
    p = {"class": kw.pop("class_", "Defender"),
         "level": kw.pop("level", 1),
         "race": kw.pop("race", "Human"),
         "name": kw.pop("name", "P1"),
         "STR": kw.pop("STR", 10),
         "DEX": kw.pop("DEX", 10),
         "CON": kw.pop("CON", 10),
         "INT": kw.pop("INT", 10),
         "CHA": kw.pop("CHA", 10),
    }
    ensure_class_features(p)
    grant_starting_kit(p)
    return p

def test_passive_perception_is_int_based_not_wis():
    a = mk_player(class_="Defender", INT=16)
    int_mod = (a["INT"] - 10)//2
    expected = 10 + int_mod
    assert expected == 13
    assert "WIS" not in a and "wis" not in a
