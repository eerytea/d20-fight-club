from __future__ import annotations

import types

from core.classes import ensure_class_features, grant_starting_kit
from engine.tbcombat import TBCombat, Team

def _mk_actor(name="A", lvl=17):
    a = types.SimpleNamespace()
    a.name = name; a.pid = 1; a.team_id = 0; a.tx = 5; a.ty = 5
    a.hp = 20; a.max_hp = 20; a.ac = 10; a.alive = True
    a.level = lvl
    a.STR = 10; a.DEX = 10; a.CON = 10; a.INT = 10; a.WIS = 10; a.CHA = 10
    a.speed = 4
    a.__dict__["class"] = "Cleric"  # anything non-barbarian/goblin to avoid extra riders
    ensure_class_features(a.__dict__)
    grant_starting_kit(a.__dict__)
    return a

def _mk_dummy(name="D", team=1):
    d = types.SimpleNamespace()
    d.name = name; d.pid = 2; d.team_id = team; d.tx = 6; d.ty = 5
    d.hp = 999; d.max_hp = 999; d.ac = 1; d.alive = True
    d.level = 1
    d.STR = 10; d.DEX = 10; d.CON = 10; d.INT = 10; d.WIS = 10; d.CHA = 10
    d.speed = 4
    return d

def _build(actors, seed=3):
    return TBCombat(Team(0,"A",(255,0,0)), Team(1,"B",(0,0,255)), actors, 16, 16, seed=seed)

def test_no_proficiency_added_to_weapon_damage():
    a = _mk_actor("Weap"); d = _mk_dummy()
    # Force Unarmed (1d1 finesse, mod 0), keep off-hand empty so there is no off-hand swing noise
    unarmed = next(w for w in a.inventory["weapons"] if w.get("unarmed"))
    a.equipped["main_hand_id"] = unarmed["id"]
    a.equipped["off_hand_id"] = None
    cmb = _build([a, d], seed=11)
    class AttackOnce:
        def decide(self, cmb, actor): return [{"type": "attack", "target": d}]
    cmb.controllers[0] = AttackOnce()
    cmb.take_turn()
    dmgs = [e["amount"] for e in cmb.events if e.get("type") == "damage" and e.get("actor") == "Weap"]
    # With 1d1 and mod 0, damage should be 1 (or 2 on a crit). If proficiency leaked in, it would be 1+prof (>=3).
    assert dmgs and all(val in (1, 2) for val in dmgs)

def test_no_proficiency_added_to_spell_damage():
    a = _mk_actor("Spell"); d = _mk_dummy("Dummy2")
    cmb = _build([a, d], seed=12)
    class CastOnce:
        def decide(self, cmb, actor):
            return [{"type":"spell_attack","target": d, "dice":"1d1", "ability":"WIS", "normal_range":12, "long_range":24}]
    cmb.controllers[0] = CastOnce()
    cmb.take_turn()
    dmgs = [e["amount"] for e in cmb.events if e.get("type") == "damage" and e.get("actor") == "Spell"]
    # 1d1 + WIS mod(0); expect 1 (or 2 on a crit). If proficiency leaked, we'd see 1+prof (>=3).
    assert dmgs and all(val in (1, 2) for val in dmgs)
