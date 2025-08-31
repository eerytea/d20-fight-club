from core.classes import ensure_class_features, grant_starting_kit
from engine.tbcombat import TBCombat

class Obj(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__

def make_simple_bout():
    a = Obj({"name": "A", "class": "Crusader", "level": 2, "team_id": 0,
             "STR":12,"DEX":10,"CON":12,"INT":10,"CHA":12, "hp": 15, "max_hp": 15})
    b = Obj({"name": "B", "class": "Defender", "level": 2, "team_id": 1,
             "STR":12,"DEX":10,"CON":12,"INT":10,"CHA":10, "hp": 15, "max_hp": 15})
    for p in (a,b):
        ensure_class_features(p); grant_starting_kit(p); p["alive"]=True
    tb = TBCombat(None, None, [a,b], width=8, height=8, seed=1)
    return tb, a, b

def test_engine_runs_one_round_smoke():
    tb, a, b = make_simple_bout()
    tb.controllers[a["team_id"]] = type("CtrlA", (), {"decide": lambda self, env, me: [{"type":"attack","target": b}]})()
    tb.controllers[b["team_id"]] = type("CtrlB", (), {"decide": lambda self, env, me: [{"type":"wait"}]})()
    tb.take_turn()
    tb.take_turn()
    assert len(tb.events) > 0
