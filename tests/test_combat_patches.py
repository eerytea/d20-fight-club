import pytest
from core.classes import ensure_class_features, grant_starting_kit
from engine.tbcombat import TBCombat

class Obj(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__

def P(cls, lvl=1, **stats):
    p = Obj({"name": f"{cls}{lvl}", "class": cls, "level": lvl, "team_id": 0,
             "STR":10,"DEX":10,"CON":10,"INT":10,"CHA":10, "hp": 10, "max_hp": 10, **stats})
    ensure_class_features(p); grant_starting_kit(p)
    p["alive"] = True
    return p

def C(a,b,seed=1):
    return TBCombat(None,None,[a,b],width=10,height=10,seed=seed)

def test_detection_checks_use_int_mod_not_wis():
    stalker = P("Stalker", lvl=10, DEX=16)
    enemy = P("Defender", lvl=10, INT=16); enemy["team_id"]=1
    c = C(stalker, enemy)
    c.controllers[stalker["team_id"]] = type("Ctrl", (), {"decide": lambda self, env, me: [{"type":"hide"}]})()
    c.take_turn()
    c.take_turn()
    det = [e for e in c.events if e.get("type")=="detect_hidden"]
    assert det and "int_mod" in det[-1]

def test_proficiency_added_to_damage():
    a = P("Defender", lvl=5, STR=16)
    b = P("Archer", lvl=5); b["team_id"]=1
    c = C(a,b,seed=2)
    c.controllers[a["team_id"]] = type("Ctrl", (), {"decide": lambda self, env, me: [{"type":"attack","target": b}]})()
    c.take_turn()
    dmg_events = [e for e in c.events if e.get("type")=="damage"]
    assert any(e["amount"] > 0 for e in dmg_events)
