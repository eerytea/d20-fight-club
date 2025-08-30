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
      - Monk/Druid in Wildshape etc handled elsewhere if needed
    """
    dex = int(f.get("DEX", 10))
    dex_mod = _mod(dex)

    # Race-based natural armor (lizardkin)
    race = str(f.get("race", "")).lower()
    if race == "lizardkin":
        ac = 13 + dex_mod
        # Shields still stack
        ac += int(f.get("shield_bonus", 0))
        return ac

    # Baseline
    ac = 10 + dex_mod

    # Armor and shield
    ac += int(f.get("armor_bonus", 0))
    ac += int(f.get("shield_bonus", 0))

    # Fighter Defense style: +1 AC when wearing armor (already included via fighter_defense_ac_bonus)
    ac += int(f.get("fighter_defense_ac_bonus", 0))

    # Ranger L2: +1 AC always-on (no flags needed)
    try:
        if str(f.get("class", "")).capitalize() == "Ranger" and int(f.get("level", f.get("lvl", 1))) >= 2:
            ac += 1
    except Exception:
        pass

    return ac
