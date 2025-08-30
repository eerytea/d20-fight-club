from __future__ import annotations
import types

from core.classes import ensure_class_features, grant_starting_kit
from core.ac import calc_ac
from engine.tbcombat import TBCombat, Team

def _mk_ranger(lvl=1, DEX=14, CON=12, WIS=14, name="Ranger"):
    a = types.SimpleNamespace()
    a.name = name; a.pid = 1; a.team_id = 0; a.tx = 5; a.ty = 5
    a.level = lvl; a.hp = 1; a.max_hp = 1; a.ac = 10; a.alive = True
    a.STR = 10; a.DEX = DEX; a.CON = CON; a.INT = 10; a.WIS = WIS; a.CHA = 10
    a.speed = 4
    a.__dict__["class"] = "Ranger"
    ensure_class_features(a.__dict__)
    grant_starting_kit(a.__dict__)
    return a

def _dummy(ac=12, team=1, name="Dummy"):
    d = types.SimpleNamespace()
    d.name = name; d.pid = 2; d.team_id = team; d.tx = 50; d.ty = 5
    d.level = 1; d.hp = 999; d.max_hp = 999; d.ac = ac; d.alive = True
    d.STR = 10; d.DEX = 10; d.CON = 10; d.INT = 10; d.WIS = 10; d.CHA = 10
    d.speed = 4
    return d

def _cmb(actors, seed=7):
    return TBCombat(Team(0,"A",(255,0,0)), Team(1,"B",(0,0,255)), actors, 100, 10, seed=seed)

def test_ranger_kit_and_ac_and_hp():
    r = _mk_ranger(lvl=2, DEX=14, CON=12)  # DEX mod +2, CON mod +1
    # AC: 10 + Dex(2) + ScaleMail(4) + Ranger L2 (+1) = 17
    assert calc_ac(r.__dict__) == 17
    # HP: base 10 + con_mod(1) + (lvl-1)*6 = 10+1+6 = 17
    assert r.max_hp == 17
    # Longbow present and selected
    names = [w["name"] for w in r.inventory["weapons"]]
    assert "Longbow" in names and r.weapon["name"] == "Longbow"

def test_ranger_unlimited_range_at_18():
    r = _mk_ranger(lvl=18, DEX=14)
    d = _dummy(ac=12)
    class Shoot:
        def decide(self, cmb, actor): return [{"type":"attack","target":d}]
    cmb = _cmb([r, d], seed=2)
    cmb.controllers[0] = Shoot()
    cmb.take_turn()
    # Should not be out_of_range event at extreme distance
    assert not any(e.get("type")=="attack" and e.get("reason")=="out_of_range" for e in cmb.events)

def test_ranger_hide_bonus_at_10():
    r = _mk_ranger(lvl=10, DEX=14, WIS=10)
    e = _dummy(ac=12, team=1)
    class HideThenShoot:
        def decide(self, cmb, actor): return [{"type":"hide"}, {"type":"attack","target":e}]
    cmb = _cmb([r, e], seed=1)
    cmb.controllers[0] = HideThenShoot()
    cmb.take_turn()
    hide = next(ev for ev in cmb.events if ev.get("type")=="hide_attempt")
    assert hide["bonus10"] == 10
