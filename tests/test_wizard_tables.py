# tests/test_wizard_tables.py
from __future__ import annotations
import types

from core.classes import ensure_class_features, apply_class_level_up

def _mk_wizard(level=1, INT=16, CON=10, name="Wiz"):
    w = types.SimpleNamespace()
    w.name = name
    w.__dict__["class"] = "Wizard"
    w.level = level
    w.INT = INT
    w.CON = CON
    w.DEX = 10; w.STR = 8; w.WIS = 10; w.CHA = 10
    w.hp = 1; w.max_hp = 1; w.ac = 10
    ensure_class_features(w.__dict__)
    return w

def test_wizard_cantrips_and_slots_progression():
    # Spot check a few rows from the table
    w1 = _mk_wizard(level=1)
    assert w1.cantrips_known == 3
    # slots_total padded with a leading 0 (index == spell level)
    # L1 slots = 2
    assert w1.spell_slots_total[1] == 2 and sum(w1.spell_slots_total[2:]) == 0

    w5 = _mk_wizard(level=5)
    assert w5.cantrips_known == 4
    # L1..L3 = 4,3,2
    assert w5.spell_slots_total[1:4] == [4,3,2]

    w11 = _mk_wizard(level=11)
    # L1..L6 = 4,3,3,3,2,1
    assert w11.spell_slots_total[1:7] == [4,3,3,3,2,1]

    w17 = _mk_wizard(level=17)
    # L1..L9 = 4,3,3,3,2,1,1,1,1
    assert w17.spell_slots_total[1:10] == [4,3,3,3,2,1,1,1,1]

def test_wizard_spell_math_and_flags():
    w = _mk_wizard(level=7, INT=18)  # INT mod +4, prof +3 at L7
    # Attack bonus = prof + INT mod = 7
    assert w.spell_attack_bonus == 7
    # Save DC = 8 + prof + INT mod = 15
    assert w.spell_save_dc == 15

    # Level flags
    assert w.wiz_cantrip_tier == 2         # 5–10 => tier 2
    assert w.wiz_adv_vs_blind_deaf is True # L7+
    assert w.wiz_aoe_ally_exempt == 1      # L3=1, L10=2, L17=3

    # Level up and re-check deriveds refresh
    apply_class_level_up(w.__dict__, 17)
    assert w.wiz_cantrip_tier == 4         # 17–20 => tier 4
    assert w.wiz_aoe_ally_exempt == 3      # L17 => 3
    # Slots should reflect 17th row now
    assert w.spell_slots_total[9] == 1

def test_wizard_hp_is_retroactive_with_con():
    w = _mk_wizard(level=10, CON=14)  # base 6 + (L-1)*4 + CON mod(2)
    # max_hp = 6 + 9*4 + 2 = 44
    assert w.max_hp == 44
    # Bump CON and ensure recompute bumps HP
    w.CON = 16
    apply_class_level_up(w.__dict__, 10)  # re-apply level (recompute deriveds)
    # Now CON mod = 3 -> 45
    assert w.max_hp == 45
