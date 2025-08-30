from __future__ import annotations

import types

from core.classes import ensure_class_features, apply_class_level_up, grant_starting_kit
from core.ac import calc_ac

# Prefer your shared helpers if present; otherwise fall back to tiny locals.
try:
    from tests.utils import make_melee, build_combat
except Exception:  # minimal fallbacks
    from engine.tbcombat import TBCombat, Team
    def make_melee(pid, team, x, y):
        o = types.SimpleNamespace()
        o.pid = pid; o.team_id = team; o.tx = x; o.ty = y
        o.name = f"P{pid}"
        o.hp = 10; o.max_hp = 10; o.ac = 10; o.alive = True
        o.level = 1; o.DEX = 10; o.STR = 10; o.CON = 10; o.INT = 10; o.WIS = 10; o.CHA = 10
        o.speed = 4
        return o
    def build_combat(actors, seed=1, cols=16, rows=16):
        return TBCombat(Team(0,"A",(255,0,0)), Team(1,"B",(0,0,255)), actors, cols, rows, seed=seed)


def _force_druid(actor, *, level=1):
    # Run class init/kit on the actor’s dict so fields become attributes.
    actor.__dict__.setdefault("class", "Druid")
    actor.__dict__["class"] = "Druid"
    actor.level = level
    ensure_class_features(actor.__dict__)
    grant_starting_kit(actor.__dict__)
    return actor


def _equip_wildshape(actor, *, form_cr=0.25, form_stats=None):
    """Put 'Wild Shape' in main hand and a form in off hand."""
    inv = actor.inventory
    # Ensure the forms list exists (grant_starting_kit does this).
    forms = inv.setdefault("forms", [])
    form = {
        "type": "wild_form",
        "id": "form_test",
        "name": "Test Beast",
        "cr": float(form_cr),
        "stats": (form_stats or {
            "hp": 30, "max_hp": 30, "ac": 14, "speed": 7,
            "STR": 12, "DEX": 15, "CON": 12, "INT": 3, "WIS": 12, "CHA": 6,
            "natural_weapon": {"name": "Bite", "dice": "1d8", "reach": 1, "finesse": False}
        }),
    }
    # Add/replace
    forms[:] = [form]
    # Pick Wild Shape in main hand
    wild = next(w for w in inv["weapons"] if w.get("name") == "Wild Shape")
    actor.equipped["main_hand_id"] = wild["id"]
    # Pick our form in off-hand
    actor.equipped["off_hand_id"] = form["id"]


def test_druid_table_and_flags():
    a = make_melee(1, 0, 4, 4); a.name = "Druid"
    a = _force_druid(a, level=1)
    # L1 table
    assert a.cantrips_known == 2
    assert a.spell_slots_total[1] == 2
    # Level up to 18: can cast while shaped
    for L in range(2, 19): apply_class_level_up(a.__dict__, L)
    assert a.wildshape_cast_while_shaped is True
    # Level up to 20: unlimited slots flag set
    for L in range(19, 21): apply_class_level_up(a.__dict__, L)
    assert a.spell_slots_unlimited is True


def test_wildshape_applies_form_stats_and_ignores_gear():
    a = make_melee(1, 0, 5, 5); a.name = "Druid"
    a = _force_druid(a, level=10)
    # Sanity: druid starts with leather (+1) + shield (+2)
    assert a.armor_bonus >= 0 and a.shield_bonus >= 0
    _equip_wildshape(a, form_cr=0.25)
    # Dummy foe (so we can build combat)
    d = make_melee(2, 1, 6, 5); d.name = "Dummy"
    from tests.utils import build_combat  # prefer your utils here if available
    try:
        cmb = build_combat([a, d], seed=1234)
    except Exception:
        cmb = build_combat([a, d], seed=1234)  # fallback variant above

    # Look for the start event and check stat overrides
    ws = [e for e in cmb.events if e.get("type") == "wildshape" and e.get("actor") == "Druid"]
    assert ws and ws[-1].get("started") is True
    # Stats swapped to beast block
    assert a.max_hp == 30 and a.hp == 30
    assert a.ac == 14 and a.speed == 7
    # Gear ignored while shaped
    assert a.armor_bonus == 0 and a.shield_bonus == 0


def test_wildshape_blocks_spells_until_18_then_allows():
    # Case 1: level 10 (blocked)
    a = make_melee(1, 0, 5, 5); a.name = "Druid10"
    a = _force_druid(a, level=10)
    _equip_wildshape(a, form_cr=0.25)
    d = make_melee(2, 1, 6, 5); d.name = "Dummy"
    class CastCtrl:  # try to cast a simple spell attack
        def decide(self, cmb, actor):
            return [{"type": "spell_attack", "target": d, "dice": "1d1", "ability": "WIS",
                     "normal_range": 12, "long_range": 24}]
    cmb = build_combat([a, d], seed=1); cmb.controllers[0] = CastCtrl()
    cmb.take_turn()
    blocked = [e for e in cmb.events if e.get("type") == "spell_blocked" and e.get("reason") == "wildshape"]
    assert blocked, "Expected spell to be blocked while shaped before level 18"

    # Case 2: level 18 (allowed)
    b = make_melee(3, 0, 5, 5); b.name = "Druid18"
    b = _force_druid(b, level=18)
    _equip_wildshape(b, form_cr=1.0)
    d2 = make_melee(4, 1, 6, 5); d2.name = "Dummy2"; d2.ac = 1
    cmb2 = build_combat([b, d2], seed=2); cmb2.controllers[0] = CastCtrl()
    cmb2.take_turn()
    cast_events = [e for e in cmb2.events if e.get("type") == "spell_attack" and e.get("actor") == "Druid18"]
    assert cast_events, "Expected spell_attack event once casting while shaped is unlocked at level 18"
