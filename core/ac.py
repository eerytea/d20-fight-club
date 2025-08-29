# core/ac.py
from __future__ import annotations
from typing import Any, Dict

def _mod(x: int) -> int:
    return (int(x) - 10) // 2

def calc_ac(f: Dict[str, Any]) -> int:
    """
    Returns the best applicable AC, considering:
      - Normal: 10 + DEX mod + armor_bonus
      - Lizardkin: 13 + DEX mod (ignores armor; armor prohibited elsewhere)
      - Barbarian Unarmored Defense: 10 + DEX mod + CON mod (when no armor)
      - Golem: +1 to the final chosen AC
    """
    dex = int(f.get("DEX", f.get("dex", 10)))
    con = int(f.get("CON", f.get("con", 10)))
    race = str(f.get("race", "")).lower()
    armor_bonus = int(f.get("armor_bonus", f.get("armor", 0)))

    # Lizardkin ignore armor entirely
    if race == "lizardkin":
        armor_bonus = 0

    candidates = []

    # Normal
    candidates.append(10 + _mod(dex) + armor_bonus)

    # Lizardkin natural armor
    if race == "lizardkin":
        candidates.append(13 + _mod(dex))

    # Barbarian Unarmored Defense only if no armor equipped
    if bool(f.get("barb_unarmored_ac", False)) and armor_bonus == 0:
        candidates.append(10 + _mod(dex) + _mod(con))

    ac = max(candidates) if candidates else 10 + _mod(dex) + armor_bonus

    # Respect any explicit 'ac' seed, but choose higher
    try:
        base = int(f.get("ac", ac))
    except Exception:
        base = ac
    ac = max(ac, base)

    # Golem +1
    if race == "golem":
        ac += 1

    return int(ac)
