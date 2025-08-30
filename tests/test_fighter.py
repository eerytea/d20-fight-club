from __future__ import annotations
import types

from core.classes import ensure_class_features, grant_starting_kit
from engine.tbcombat import TBCombat, Team

def _mk(style: str, lvl=1, name=None):
    a = types.SimpleNamespace()
    a.name = name or style
    a.pid = 1; a.team_id = 0; a.tx = 5; a.ty = 5
    a.level = lvl; a.hp = 20; a.max_hp = 20; a.ac = 10; a.alive = True
    a.STR = 10; a.DEX = 10; a.CON = 10; a.INT = 10; a.WIS = 10; a.CHA = 10
    a.speed = 4
    a.__dict__["class"] = style
    ensure_class_features(a.__dict__)
    grant_starting_kit(a.__dict__)
    return a

def _dummy(ac=12, team=1, name="Dummy"):
    d = types.SimpleNamespace()
    d.name = name; d.pid = 2; d.team_id = team; d.tx = 6; d.ty = 5
    d.level = 1; d.hp = 999; d.max_hp = 999; d.ac = ac; d.alive = True
    d.STR = 10; d.DEX = 10; d.CON = 10; d.INT = 10; d.WIS = 10; d.CHA = 10
    d.speed = 4
    return d

def _cmb(actors, seed=7):
    return TBCombat(Team(0,"A",(255,0,0)), Team(1,"B",(0,0,255)), actors, 16, 16, seed=seed)

def test_archer_gets_plus2_to_hit_with_ranged():
    ar = _mk("Archer", lvl=1, name="Archer")
    dm = _dummy(ac=13)  # baseline: DEX mod 0, prof 2 -> needs 11; with +2 Archer can hit a point higher AC
    class Shoot:
        def decide(self, cmb, actor): return [{"type":"attack","target":dm}]
    cmb = _cmb([ar, dm], seed=3); cmb.controllers[0] = Shoot()
    cmb.take_turn()
    atk = next(e for e in cmb.events if e.get("type")=="attack" and e.get("actor")=="Archer" and not e.get("offhand"))
    # ensure style bonus was applied in the roll accounting
    assert atk["ranged"] is True
    assert atk["style_bonus"] == 2

def test_defender_has_plus_one_ac_always():
    df = _mk("Defender", lvl=1)
    # Plate +5, Shield +2, Dex 0, +1 style = 18
    assert df.ac == 18

def test_enforcer_two_handed_damage_advantage_records_rolls():
    en = _mk("Enforcer", lvl=5)  # also gets extra attack; we only check first hit's damage
    dm = _dummy(ac=1)
    class Swing:
        def decide(self, cmb, actor): return [{"type":"attack","target":dm}]
    cmb = _cmb([en, dm], seed=9); cmb.controllers[0] = Swing()
    cmb.take_turn()
    dmg_events = [e for e in cmb.events if e.get("type")=="damage" and e.get("actor")==en.name]
    assert dmg_events, "Expected at least one damage event"
    # At least one should include the two-rolled list
    assert any(isinstance(e.get("rolls"), list) and e.get("twohand_adv") for e in dmg_events)

def test_duelist_offhand_uses_proficiency_to_hit():
    du = _mk("Duelist", lvl=1, name="Duelist")
    dm = _dummy(ac=12)
    class Stab:
        def decide(self, cmb, actor): return [{"type":"attack","target":dm}]
    cmb = _cmb([du, dm], seed=5); cmb.controllers[0] = Stab()
    cmb.take_turn()
    off = [e for e in cmb.events if e.get("type")=="attack" and e.get("actor")=="Duelist" and e.get("offhand")]
    assert off, "Expected an off-hand attack event"
    # Off-hand should carry a non-zero proficiency on the to-hit calculation
    assert off[0]["prof"] > 0

def test_fighter_extra_attacks_scale_with_level():
    en = _mk("Enforcer", lvl=11, name="Enforcer")  # 3 swings main-hand (11 -> +2 extra)
    dm = _dummy(ac=1)
    class AttackOnce:
        def decide(self, cmb, actor): return [{"type":"attack","target":dm}]
    cmb = _cmb([en, dm], seed=4); cmb.controllers[0] = AttackOnce()
    cmb.take_turn()
    mains = [e for e in cmb.events if e.get("type")=="attack" and e.get("actor")=="Enforcer" and not e.get("offhand")]
    assert len(mains) == 3, f"expected 3 main-hand swings at level 11, saw {len(mains)}"
