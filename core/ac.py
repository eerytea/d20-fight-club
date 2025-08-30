# core/ac.py
from __future__ import annotations
from typing import Any, Dict

def _mod(x: int) -> int:
    return (int(x) - 10) // 2

def calc_ac(f: Dict[str, Any]) -> int:
    """
    Best applicable AC (shield stacks with all unless explicitly noted):
      - Normal: 10 + DEX mod + armor_bonus + shield_bonus
      - Lizardkin: 13 + DEX mod + shield_bonus (ignores armor_bonus)
      - Barbarian UD: 10 + DEX mod + CON mod + shield_bonus (only if no body armor)
      - Monk UD: 10 + DEX mod + WIS mod (only if no armor and no shield)
      - After choosing max, add Golem +1.
      - Fighter (Defender): add +1 always-on.
    """
    dex = int(f.get("DEX", f.get("dex", 10)))
    con = int(f.get("CON", f.get("con", 10)))
    wis = int(f.get("WIS", f.get("wis", 10)))
    race = str(f.get("race", "")).lower()
    armor_bonus = int(f.get("armor_bonus", f.get("armor", 0)))
    shield_bonus = int(f.get("shield_bonus", 0))

    if race == "lizardkin":
        armor_bonus = 0

    candidates = []
    # Normal formula
    candidates.append(10 + _mod(dex) + armor_bonus + shield_bonus)

    # Lizardkin natural armor
    if race == "lizardkin":
        candidates.append(13 + _mod(dex) + shield_bonus)

    # Barbarian unarmored (no body armor)
    if bool(f.get("barb_unarmored_ac", False)) and armor_bonus == 0:
        candidates.append(10 + _mod(dex) + _mod(con) + shield_bonus)

    # Monk unarmored (no armor and no shield)
    if bool(f.get("monk_unarmored_ac", False)) and armor_bonus == 0 and shield_bonus == 0:
        candidates.append(10 + _mod(dex) + _mod(wis))

    ac = max(candidates) if candidates else 10 + _mod(dex) + armor_bonus + shield_bonus

    if race == "golem":
        ac += 1

    ac += int(f.get("fighter_defense_ac_bonus", 0))

    return int(ac)
