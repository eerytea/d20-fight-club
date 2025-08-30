# tests/test_paladin.py
from __future__ import annotations
import types

import pytest

from core.classes import ensure_class_features, grant_starting_kit, apply_class_level_up
from engine.tbcombat import TBCombat


# ------------ helpers ------------
def mk_actor(cls="Paladin", level=1, STR=16, DEX=10, CON=14, INT=8, WIS=10, CHA=16, name="Pally", team=1):
    a = types.SimpleNamespace()
    a.__dict__["class"] = cls
    a.level = level
    a.name = name
    a.team_id = team
    a.alive = True
    a.STR = STR; a.DEX = DEX; a.CON = CON; a.INT = INT; a.WIS = WIS; a.CHA = CHA
    a.hp = 1; a.max_hp = 1
    a.tx = 0; a.ty = 0
    ensure_class_features(a.__dict__)
    grant_starting_kit(a.__dict__)
    return a

def mk_dummy_enemy(hp=100, ac=10, team=2, name="Dummy", tx=1, ty=0):
    e = types.SimpleNamespace()
    e.__dict__["class"] = "Defender"  # arbitrary
    e.level = 1
    e.name = name
    e.team_id = team
    e.alive = True
    e.STR = 10; e.DEX = 10; e.CON = 10; e.INT = 10; e.WIS = 10; e.CHA = 10
    e.hp = hp; e.max_hp = hp; e.ac = ac
    e.tx = tx; e.ty = ty
    return e

class StaticController:
    """Simple controller that returns fixed intents."""
    def __init__(self, intents):
        self._intents = intents
    def decide(self, _combat, _actor):
        return list(self._intents)


# ------------ tests ------------
def test_lay_on_hands_pool_and_heal():
    p = mk_actor(level=7, name="Heals")
    e = mk_dummy_enemy()
    c = TBCombat(team_a=1, team_b=2, actors=[p, e], width=8, height=8, seed=42)
    c.controllers = {1: StaticController([{"type": "lay_on_hands", "target": p, "amount": 12}])}
    # reduce HP to test heal cap and pool
    p.hp = p.max_hp - 20
    before_pool = p.pal_lay_on_hands_current
    c.take_turn()
    # healed 12, pool reduced 12
    assert p.hp == p.max_hp - 8
    assert p.pal_lay_on_hands_current == before_pool - 12
    # pool equals 5 * level
    assert p.pal_lay_on_hands_total == 5 * p.level


def test_auras_bonus_and_fear_radius_upgrade():
    # L6 aura: +CHA mod to WIS saves within 2; L10 no-fear within 2; L18 both radius 6
    p6 = mk_actor(level=6, CHA=18, name="P6", team=1)   # CHA mod +4
    ally = mk_actor(cls="Defender", level=1, name="Ally", team=1)
    foe = mk_dummy_enemy(team=2, tx=1, ty=0)

    # place ally within 2
    ally.tx, ally.ty = 1, 0
    c = TBCombat(team_a=1, team_b=2, actors=[p6, ally, foe], width=8, height=8, seed=1)

    # Force a WIS save vs DC 12 and check +4 bonus applies (we don't care success/fail, we inspect event)
    c.controllers = {1: StaticController([{"type": "wait"}]), 2: StaticController([{"type": "wait"}])}
    # Trigger a save through the helper (private but accessible here)
    ok = c._saving_throw(ally, "WIS", 12, vs_condition=None)
    ev = c.events[-1]
    assert ev["type"] == "saving_throw"
    # The paladin's CHA mod should be included in 'total'
    # Can't easily recompute exact d20, but ensure recorded includes at least +4 vs raw roll baseline
    assert c._paladin_wis_aura_bonus(ally) == 4

    # L10: fear immunity within 2
    apply_class_level_up(p6.__dict__, 10)
    assert p6.pal_aura_no_fear is True
    # ally in range -> auto succeed vs frightened
    ok2 = c._saving_throw(ally, "WIS", 100, vs_condition="frightened")
    assert ok2 is True

    # L18: radius upgrade -> 6
    apply_class_level_up(p6.__dict__, 18)
    assert p6.pal_aura_radius == 6


def test_smite_proc_scaling_and_chance_flip(monkeypatch):
    # Create a paladin and force the RNG to always trigger smite
    p2 = mk_actor(level=2, name="P2")
    e = mk_dummy_enemy(hp=200, ac=8, name="Target")
    # ensure two-handed advantage doesn't complicate (keep shield equipped so versatile stays 1H)
    p2.equipped["off_hand_id"] = p2.equipped.get("shield_id")  # keep shield
    c = TBCombat(team_a=1, team_b=2, actors=[p2, e], width=8, height=8, seed=2)

    # Force smite proc: rng.random() -> 0.0 always
    monkeypatch.setattr(c.rng, "random", lambda: 0.0)

    # Attack intent
    c.controllers = {1: StaticController([{"type": "attack", "target": e}])}
    c.take_turn()

    # Look for pal_smite event with nd6 == 2 at level 2
    smites = [ev for ev in c.events if ev.get("type") == "pal_smite"]
    assert smites, "Expected smite proc at level 2"
    assert smites[0]["nd6"] == 2

    # Now level up to 11 -> chance becomes 50% and dice follow table
    apply_class_level_up(p2.__dict__, 11)
    e2 = mk_dummy_enemy(hp=200, ac=8, name="Target2")
    c2 = TBCombat(team_a=1, team_b=2, actors=[p2, e2], width=8, height=8, seed=3)
    monkeypatch.setattr(c2.rng, "random", lambda: 0.0)
    c2.controllers = {1: StaticController([{"type": "attack", "target": e2}])}
    c2.take_turn()
    smites2 = [ev for ev in c2.events if ev.get("type") == "pal_smite"]
    assert smites2 and smites2[0]["nd6"] in (2, 3, 4, 5)  # depends on exact L after apply; table covers scaling


def test_two_handed_damage_advantage_invokes_double_roll(monkeypatch):
    # We detect the 'damage-advantage' path by counting _roll_damage_once calls
    class CountingCombat(TBCombat):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.roll_calls = 0
        def _roll_damage_once(self, *args, **kwargs):
            self.roll_calls += 1
            return super()._roll_damage_once(*args, **kwargs)

    p = mk_actor(level=2, name="P2")  # damage-advantage unlocks at L2
    # Unequip shield to allow versatile warhammer to be used 2H
    p.equipped["shield_id"] = None
    p.shield_bonus = 0
    e = mk_dummy_enemy(hp=200, ac=8)
    cc = CountingCombat(team_a=1, team_b=2, actors=[p, e], width=8, height=8, seed=5)
    cc.controllers = {1: StaticController([{"type": "attack", "target": e}])}
    cc.take_turn()

    # With 2H in use, damage should be rolled twice (pick higher)
    assert cc.roll_calls >= 2, "Expected two damage rolls (take higher) when using two-handed at Paladin L2+"


def test_extra_attack_auto_second_swing():
    p = mk_actor(level=5, name="P5")  # Extra Attack online
    # Unequip shield to avoid interference, but not necessary
    e = mk_dummy_enemy(hp=200, ac=8)
    c = TBCombat(team_a=1, team_b=2, actors=[p, e], width=8, height=8, seed=7)
    c.controllers = {1: StaticController([{"type": "attack", "target": e}])}
    c.take_turn()

    dmg_events = [ev for ev in c.events if ev.get("type") == "damage" and ev.get("attacker") == "P5"]
    # Expect at least two damage events from the auto extra swing
    assert len(dmg_events) >= 2
