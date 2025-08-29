# core/ac.py
from __future__ import annotations
from typing import Any, Dict

def _mod(stat: int) -> int:
    return (int(stat) - 10) // 2

def calc_ac(f: Dict[str, Any]) -> int:
    """AC:
      - Most races: 10 + DEX mod + armor_bonus
      - Lizardkin: 13 + DEX mod   (replaces armor formula)
      - Golem: +1 to whatever its computed AC is (after the chosen formula)
    """
    dex = int(f.get("DEX", f.get("dex", 10)))
    armor_bonus = int(f.get("armor_bonus", f.get("armor", 0)))
    race = str(f.get("race", "")).lower()

    if race == "lizardkin":
        computed = 13 + _mod(dex)
    else:
        computed = 10 + _mod(dex) + armor_bonus

    if race == "golem":
        computed += 1

    # If caller seeded 'ac', keep the higher of the two.
    try:
        base = int(f.get("ac", computed))
    except Exception:
        base = computed
    return max(computed, base)
