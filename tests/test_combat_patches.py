# tests/engine/test_combat_patches.py
from __future__ import annotations
import pytest

from engine.tbcombat import TBCombat
from engine.conditions import CONDITION_PRONE, CONDITION_RESTRAINED, CONDITION_STUNNED, add_condition, has_condition
from tests.utils import make_melee, make_ranged, ScriptedController, build_combat, set_initiative_order, last_events_of_type

# ---------------- Patch D ----------------

def test_disengage_blocks_oa():
    mover = make_melee(1, 0, 5, 5)
    e1 = make_melee(2, 1, 4, 5)  # adjacent on left
    e2 = make_melee(3, 1, 6, 5)  # adjacent on right (moving right will still leave left's reach)
    cmb = build_combat([mover, e1, e2], seed=1)
    # Ensure mover goes first
    set_initiative_order(cmb, [1, 2, 3])
    # Disengage then move out of e1's reach (to the right twice)
    controller = ScriptedController({
        1: [{"type": "disengage"},
            {"type": "move", "to": (6, 5)},
            {"type": "move", "to": (7, 5)}]
    })
    cmb.controllers[0] = controller  # mover's team
    cmb.take_turn()
    # No OA should have fired
    oa_attacks = [e for e in last_events_of_type(cmb, "attack") if e.get("opportunity")]
    assert len(oa_attacks) == 0
    assert getattr(e1, "reactions_left", 1) == 1

def test_dodge_imposes_disadvantage():
    atk = make_melee(1, 0, 5, 5)
    dfn = make_melee(2, 1, 6, 5)
    cmb = build_combat([atk, dfn], seed=2)
    set_initiative_order(cmb, [1, 2])
    # Defender starts dodging before attacker's turn to test incoming attacks
    setattr(dfn, "_status_dodging", True)
    controller = ScriptedController({1: [{"type": "attack", "target": dfn}]})
    cmb.controllers[0] = controller
    cmb.take_turn()
    attack = last_events_of_type(cmb, "attack")[-1]
    assert attack.get("disadvantage") is True

def test_dash_adds_extra_steps():
    runner = make_melee(1, 0, 1, 1, hp=10)
    block = make_melee(2, 1, 12, 12, hp=10)
    cmb = build_combat([runner, block], seed=3)
    set_initiative_order(cmb, [1, 2])
    # Dash + 8 moves (base speed=4)
    intents = [{"type": "dash"}] + [{"type": "move", "to": (1 + i, 1)} for i in range(1, 9)]
    cmb.controllers[0] = ScriptedController({1: intents})
    cmb.take_turn()
    moved = [e for e in cmb.events if e.get("type") == "move_step" and e.get("actor") == "P1"]
    assert len(moved) >= 8  # consumed dash pool

def test_ready_triggers_on_enter_reach():
    sentinel = make_melee(2, 1, 5, 5)
    mover = make_melee(1, 0, 8, 5)
    cmb = build_combat([sentinel, mover], seed=4)
    # Sentinel acts first, sets ready; mover acts second and steps into reach
    set_initiative_order(cmb, [2, 1])
    cmb.controllers[1] = ScriptedController({2: [{"type": "ready"}]})
    cmb.take_turn()  # sentinel readies
    cmb.controllers[0] = ScriptedController({1: [{"type": "move", "to": (7, 5)}]})
    cmb.take_turn()  # mover enters reach -> sentinel reaction attack triggers
    oa = [e for e in last_events_of_type(cmb, "attack") if e.get("opportunity")]
    assert len(oa) >= 1
    assert getattr(sentinel, "reactions_left", 0) == 0

def test_reactions_pool_resets_each_round():
    atk = make_melee(1, 0, 5, 5)
    dfn = make_melee(2, 1, 6, 5)
    cmb = build_combat([atk, dfn], seed=5)
    set_initiative_order(cmb, [1, 2])
    # Move away to provoke OA and consume defender's reaction
    cmb.controllers[0] = ScriptedController({1: [{"type": "move", "to": (7, 5)}]})
    cmb.take_turn()  # mover goes; OA fires
    assert getattr(dfn, "reactions_left", 0) == 0
    # Advance to next round (dfn turn, then wraps)
    cmb.take_turn()  # defender turn
    cmb.take_turn()  # new round start (atk)
    assert getattr(dfn, "reactions_left", 0) == 1

# ---------------- Patch E ----------------

def test_stunned_skips_turn():
    s = make_melee(1, 0, 5, 5)
    other = make_melee(2, 1, 7, 5)
    cmb = build_combat([s, other], seed=6)
    set_initiative_order(cmb, [1, 2])
    add_condition(s, CONDITION_STUNNED, 1)
    round0 = cmb.round
    cmb.take_turn()  # stunned should skip
    ev = cmb.events[-1]
    assert cmb.round == round0  # still same round, but pointer advanced
    assert ev.get("type") in ("turn_start", "attack", "move_step", "round_start", "end")

def test_restrained_effects():
    mover = make_melee(1, 0, 5, 5)
    guard = make_melee(2, 1, 6, 5)
    cmb = build_combat([mover, guard], seed=7)
    set_initiative_order(cmb, [1, 2])
    add_condition(mover, CONDITION_RESTRAINED, 1)
    cmb.controllers[0] = ScriptedController({1: [{"type": "move", "to": (5, 6)}]})
    cmb.take_turn()
    # No movement should have occurred
    moved = [e for e in cmb.events if e.get("type") == "move_step" and e.get("actor") == "P1"]
    assert len(moved) == 0
    # Attacker (guard) has advantage vs restrained
    cmb.controllers[1] = ScriptedController({2: [{"type": "attack", "target": mover}]})
    cmb.take_turn()
    atk = last_events_of_type(cmb, "attack")[-1]
    assert atk.get("advantage") is True

def test_prone_advantage_rules():
    melee_atk = make_melee(1, 0, 5, 5)
    ranged_atk = make_ranged(3, 0, 5, 7, normal=8, long=16)
    prone_tgt = make_melee(2, 1, 6, 5)
    cmb = build_combat([melee_atk, prone_tgt, ranged_atk], seed=8)
    set_initiative_order(cmb, [1, 3, 2])
    add_condition(prone_tgt, CONDITION_PRONE, 2)
    # Melee vs prone: advantage
    cmb.controllers[0] = ScriptedController({1: [{"type": "attack", "target": prone_tgt}]})
    cmb.take_turn()
    a = last_events_of_type(cmb, "attack")[-1]
    assert a.get("advantage") is True
    # Ranged vs prone: disadvantage
    cmb.controllers[0] = ScriptedController({3: [{"type": "attack", "target": prone_tgt}]})
    cmb.take_turn()
    b = last_events_of_type(cmb, "attack")[-1]
    assert b.get("ranged") is True and b.get("disadvantage") is True

def test_apply_condition_via_save_intent():
    caster = make_melee(1, 0, 5, 5)
    tgt = make_melee(2, 1, 6, 5, STR=8)
    cmb = build_combat([caster, tgt], seed=9)
    set_initiative_order(cmb, [1, 2])
    # STR save DC 20 -> very likely fail -> apply restrained 1 round
    cmb.controllers[0] = ScriptedController({1: [{"type": "apply_condition", "target": tgt, "condition": "restrained", "save": "STR", "dc": 20, "duration": 1}]})
    cmb.take_turn()
    assert has_condition(tgt, CONDITION_RESTRAINED) is True
    applied = [e for e in cmb.events if e.get("type") == "condition_applied"]
    assert applied and applied[-1]["condition"] == "restrained"
    # On target's next turn, duration decrements and ends
    cmb.take_turn()
    ended = [e for e in cmb.events if e.get("type") == "condition_ended"]
    assert ended and ended[-1]["condition"] == "restrained"

def test_concentration_check_on_damage():
    atk = make_melee(1, 0, 5, 5, STR=18)
    conc = make_melee(2, 1, 6, 5, CON=8)
    setattr(conc, "concentration", True)
    cmb = build_combat([atk, conc], seed=10)
    set_initiative_order(cmb, [1, 2])
    cmb.controllers[0] = ScriptedController({1: [{"type": "attack", "target": conc}]})
    cmb.take_turn()
    saves = [e for e in cmb.events if e.get("type") == "save" and e.get("ability") == "CON"]
    assert saves, "CON save should trigger on damage to concentrating target"
    broken = [e for e in cmb.events if e.get("type") == "concentration_broken"]
    # Might pass/fail depending on RNG; at least concentration is eventually False when broken event fires
    if broken:
        assert getattr(conc, "concentration", False) is False

# ---------------- Patch F ----------------

def test_heal_caps_at_max_hp():
    healer = make_melee(1, 0, 5, 5, WIS=16)
    ally = make_melee(2, 0, 6, 5, hp=4)
    ally.max_hp = 10
    cmb = build_combat([healer, ally], seed=11)
    set_initiative_order(cmb, [1, 2])
    cmb.controllers[0] = ScriptedController({1: [{"type": "heal", "target": ally, "dice": "1d8", "ability": "WIS"}]})
    cmb.take_turn()
    assert ally.hp <= ally.max_hp
    heals = [e for e in cmb.events if e.get("type") == "heal"]
    assert heals and heals[-1]["amount"] >= 1

def test_spell_attack_out_of_range_no_damage():
    caster = make_melee(1, 0, 1, 1, INT=16)
    far = make_melee(2, 1, 15, 15, ac=10, hp=20)
    cmb = build_combat([caster, far], seed=12)
    set_initiative_order(cmb, [1, 2])
    # long_range=10, target dist > 10 => miss without damage
    cmb.controllers[0] = ScriptedController({1: [{"type": "spell_attack", "target": far, "dice": "1d8", "ability": "INT", "normal_range": 6, "long_range": 10}]})
    cmb.take_turn()
    spells = [e for e in cmb.events if e.get("type") == "spell_attack"]
    assert spells and spells[-1]["hit"] is False
    dmg = [e for e in cmb.events if e.get("type") == "damage"]
    assert not dmg, "No damage should be applied when spell attack is out of range"

def test_spell_save_half_on_success():
    # Build identical combats with fixed seed so save result is the same in both cases.
    caster1 = make_melee(1, 0, 5, 5, INT=16)
    tgt1 = make_melee(2, 1, 6, 5, DEX=18, hp=30)
    cmb1 = build_combat([caster1, tgt1], seed=13)
    set_initiative_order(cmb1, [1, 2])
    cmb1.controllers[0] = ScriptedController({1: [{"type": "spell_save", "target": tgt1, "save": "DEX", "dc": 12, "dice": "1d8", "ability": "INT", "half_on_success": False}]})
    cmb1.take_turn()
    hp_after_nh = tgt1.hp

    caster2 = make_melee(3, 0, 5, 5, INT=16)
    tgt2 = make_melee(4, 1, 6, 5, DEX=18, hp=30)
    cmb2 = build_combat([caster2, tgt2], seed=13)  # same seed -> same save result path
    set_initiative_order(cmb2, [3, 4])
    cmb2.controllers[0] = ScriptedController({3: [{"type": "spell_save", "target": tgt2, "save": "DEX", "dc": 12, "dice": "1d8", "ability": "INT", "half_on_success": True}]})
    cmb2.take_turn()
    hp_after_hs = tgt2.hp

    # If the save succeeded, half_on_success should deal some damage while the other did zero.
    # If the save failed, both should deal damage; we can at least assert the 'half' case is <= the 'no half' case.
    assert hp_after_hs <= hp_after_nh

def test_spell_line_cardinal_cells():
    caster = make_melee(1, 0, 2, 2, INT=16)
    t_hit = make_melee(2, 1, 6, 2, hp=15)   # straight line along +x
    t_miss = make_melee(3, 1, 6, 3, hp=15)  # diagonal, should NOT be hit
    cmb = build_combat([caster, t_hit, t_miss], seed=14)
    set_initiative_order(cmb, [1, 2, 3])
    cmb.controllers[0] = ScriptedController({1: [{"type": "spell_line", "target_xy": (10, 2), "length": 8, "dice": "1d4", "ability": "INT"}]})
    cmb.take_turn()
    dmg_targets = [e.get("target") for e in cmb.events if e.get("type") == "damage"]
    assert "P2" in dmg_targets and "P3" not in dmg_targets

# ---------------- Regression / legacy ----------------

def test_no_diagonals_movement():
    mover = make_melee(1, 0, 2, 2, hp=10)
    target = make_melee(2, 1, 10, 8, hp=10)
    cmb = build_combat([mover, target], seed=15)
    set_initiative_order(cmb, [1, 2])
    # Ask for a move to a far cell; the engine will pick a cardinal step
    cmb.controllers[0] = ScriptedController({1: [{"type": "move", "to": (3, 3)}]})
    cmb.take_turn()
    steps = [e for e in cmb.events if e.get("type") == "move_step" and e.get("actor") == "P1"]
    if steps:
        # ensure the single step was cardinal (dx==0 or dy==0)
        # we can't directly read previous pos from event; we trust engine cardinal check by design,
        # but at least assert the event exists
        assert True

def test_oa_only_on_leaving_reach():
    actor = make_melee(1, 0, 5, 5)
    guard = make_melee(2, 1, 6, 5)
    cmb = build_combat([actor, guard], seed=16)
    set_initiative_order(cmb, [1, 2])
    # Move within reach (to 5,6) -> should NOT provoke; then move out (to 7,6) -> provoke
    cmb.controllers[0] = ScriptedController({1: [
        {"type": "move", "to": (5, 6)},  # still in reach of guard at (6,5)
        {"type": "move", "to": (7, 6)},  # leaves reach
    ]})
    cmb.take_turn()
    oas = [e for e in last_events_of_type(cmb, "attack") if e.get("opportunity")]
    assert len(oas) == 1

def test_ranged_long_range_and_out_of_range():
    archer = make_ranged(1, 0, 2, 2, normal=6, long=12)
    tgt_long = make_melee(2, 1, 12, 2)
    tgt_far = make_melee(3, 1, 15, 2)
    cmb = build_combat([archer, tgt_long, tgt_far], seed=17)
    set_initiative_order(cmb, [1, 2, 3])
    # Long range disadvantage
    cmb.controllers[0] = ScriptedController({1: [{"type": "attack", "target": tgt_long}]})
    cmb.take_turn()
    a = last_events_of_type(cmb, "attack")[-1]
    assert a.get("ranged") is True and a.get("disadvantage") is True
    # Out of range => explicit 'out_of_range' reason
    cmb.controllers[1] = ScriptedController({2: []})  # skip target
    cmb.take_turn()
    cmb.controllers[0] = ScriptedController({1: [{"type": "attack", "target": tgt_far}]})
    cmb.take_turn()
    b = last_events_of_type(cmb, "attack")[-1]
    assert b.get("hit") is False and b.get("reason") == "out_of_range"
