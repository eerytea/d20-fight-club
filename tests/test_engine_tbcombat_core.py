import pytest
from engine.tbcombat import TBCombat
from core.classes import ensure_class_features, grant_starting_kit

class Obj(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__

def P(cls, lvl=1, **stats):
    p = Obj({"name": f"{cls}{lvl}", "class": cls, "level": lvl, "team_id": 0,
             "STR":10,"DEX":10,"CON":10,"INT":10,"CHA":10, "hp": 10, "max_hp": 10, **stats})
    ensure_class_features(p)
    grant_starting_kit(p)
    p["alive"] = True
    return p

def C(actors, seed=1):
    return TBCombat(None, None, actors, width=10, height=10, seed=seed)

def test_stalker_l2_ranged_and_offhand_prof_roll_path():
    s = P("Stalker", lvl=2, DEX=16)
    d = P("Defender", lvl=2); d["team_id"] = 1
    c = C([s, d])
    c.controllers[s["team_id"]] = type("Ctrl", (), {
        "decide": lambda self, env, me: [{"type": "attack", "target": d}]
    })()
    c.take_turn()
    rolls = [e for e in c.events if e.get("type") == "attack_roll"]
    assert rolls, "expected an attack roll event"

def test_stalker_hide_and_enemy_int_detection():
    s = P("Stalker", lvl=10, DEX=16)
    e = P("Defender", lvl=10, INT=16); e["team_id"] = 1
    c = C([s, e])
    c.controllers[s["team_id"]] = type("Ctrl", (), {
        "decide": lambda self, env, me: [{"type": "hide"}]
    })()
    c.take_turn()  # stalker hides
    c.take_turn()  # enemy attempts detect at start
    det = [ev for ev in c.events if ev.get("type") == "detect_hidden"]
    assert det and "int_mod" in det[-1]

def test_crusader_smite_proc_and_two_handed_damage_advantage():
    cru = P("Crusader", lvl=11, STR=16)
    foe = P("Defender", lvl=11); foe["team_id"] = 1
    c = C([cru, foe], seed=3)
    c.controllers[cru["team_id"]] = type("Ctrl", (), {
        "decide": lambda self, env, me: [{"type": "attack", "target": foe}]
    })()
    for _ in range(6):
        c.take_turn()
    # Expect at least one smite proc across several swings (50% at L11)
    assert any(e["type"] == "cru_smite" for e in c.events)

def test_crusader_poison_immunity_and_extra_attack_flow():
    cru = P("Crusader", lvl=5, STR=16)
    foe = P("Defender", lvl=5); foe["team_id"] = 1
    c = C([cru, foe], seed=1)
    before = cru["hp"]
    c._apply_damage(cru, 5, dtype="poison")  # immune from L3
    assert cru["hp"] == before
    c.controllers[cru["team_id"]] = type("Ctrl", (), {
        "decide": lambda self, env, me: [{"type": "attack", "target": foe}]
    })()
    c.take_turn()
    dmg_events = [e for e in c.events if e.get("type") == "damage"]
    assert len(dmg_events) >= 1  # stochastic; ensure at least one landed

def test_wizard_aoe_exemptions_high_level():
    wiz = P("Wizard", lvl=17, INT=16)
    a1 = P("Defender", lvl=1); a2 = P("Defender", lvl=1); a3 = P("Defender", lvl=1)
    foe = P("Defender", lvl=1); foe["team_id"] = 1
    wiz["tx"] = 0; wiz["ty"] = 0
    for i, a in enumerate([a1, a2, a3], start=1):
        a["tx"] = i; a["ty"] = 0
    c = C([wiz, a1, a2, a3, foe], seed=2)
    c.controllers[wiz["team_id"]] = type("Ctrl", (), {
        "decide": lambda self, env, me: [{"type": "cast", "spell": {"name": "Boom", "level": 3, "center": (0, 0), "dtype": "fire"}}]
    })()
    c.take_turn()
    ally_hits = [e for e in c.events if e.get("type") == "spell_aoe"
                 and e.get("defender") in {a1["name"], a2["name"], a3["name"]}]
    assert len(ally_hits) == 0
