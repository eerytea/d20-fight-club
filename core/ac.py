# core/ac.py
from __future__ import annotations
from typing import Any, Dict

def _mod(x: int) -> int:
    return (int(x) - 10) // 2

def calc_ac(f: Dict[str, Any]) -> int:
    """
    Best applicable AC (shield stacks with all):
      - Normal: 10 + DEX mod + armor_bonus + shield_bonus
      - Lizardkin: 13 + DEX mod + shield_bonus (ignores armor_bonus)
      - Barbarian Unarmored: 10 + DEX mod + CON mod + shield_bonus (only if no body armor)
      - After choosing max, add Golem +1.
    """
    dex = int(f.get("DEX", f.get("dex", 10)))
    con = int(f.get("CON", f.get("con", 10)))
    race = str(f.get("race", "")).lower()
    armor_bonus = int(f.get("armor_bonus", f.get("armor", 0)))
    shield_bonus = int(f.get("shield_bonus", 0))

    if race == "lizardkin":
        armor_bonus = 0  # body armor ignored

    candidates = []

    # Normal baseline
    candidates.append(10 + _mod(dex) + armor_bonus + shield_bonus)

    # Lizardkin natural
    if race == "lizardkin":
        candidates.append(13 + _mod(dex) + shield_bonus)

    # Barbarian unarmored defense (body armor only restriction; shield allowed)
    if bool(f.get("barb_unarmored_ac", False)) and armor_bonus == 0:
        candidates.append(10 + _mod(dex) + _mod(con) + shield_bonus)

    ac = max(candidates) if candidates else 10 + _mod(dex) + armor_bonus + shield_bonus

    # Respect any explicit 'ac' seed, but choose higher
    try:
        base = int(f.get("ac", ac))
    except Exception:
        base = ac
    ac = max(ac, base)

    # Golem +1 AFTER choosing best candidate
    if race == "golem":
        ac += 1

    return int(ac)
