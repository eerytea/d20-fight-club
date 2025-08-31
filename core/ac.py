# core/ac.py
from __future__ import annotations
from typing import Any, Dict

def _mod(v: int) -> int:
    return (int(v) - 10) // 2

def calc_ac(f: Dict[str, Any]) -> int:
    """
    Centralized AC math, updated for WIS->INT world and new class names.
    - Monk unarmored AC: 10 + DEX + INT (no armor, no shield)
    - Crusader: +1 AC at level 2+
    - Stalker:  +1 AC at level 2+
    - Defender style: +1 AC (fighter_defense_ac_bonus)
    """
    armor_bonus = int(f.get("armor_bonus", 0))
    shield_bonus = int(f.get("shield_bonus", 0))
    dex_mod = _mod(int(f.get("DEX", f.get("dex", 10))))
    int_mod = _mod(int(f.get("INT", f.get("int", f.get("WIS", 10)))))  # legacy WIS fallback
    con_mod = _mod(int(f.get("CON", f.get("con", 10))))

    eq = f.get("equipped", {}) or {}
    has_armor = bool(eq.get("armor_id"))
    has_shield = bool(eq.get("shield_id"))

    # Monk unarmored AC
    if bool(f.get("monk_unarmored_ac")) and not has_armor and not has_shield:
        ac = 10 + dex_mod + int_mod
    # Berserker (barbarian-style) unarmored defense if you use it
    elif bool(f.get("barb_unarmored_ac")) and not has_armor:
        ac = 10 + dex_mod + con_mod + (shield_bonus if has_shield else 0)
    else:
        ac = 10 + armor_bonus + shield_bonus + dex_mod

    # Fighter style: Defender +1 AC
    ac += int(f.get("fighter_defense_ac_bonus", 0))

    # Crusader +1 AC at level 2+
    if str(f.get("class", "")).strip().lower() == "crusader" and int(f.get("level", 1)) >= 2:
        ac += 1

    # Stalker +1 AC at level 2+
    if str(f.get("class", "")).strip().lower() == "stalker" and int(f.get("level", 1)) >= 2:
        ac += 1

    # Misc
    ac += int(f.get("ac_misc_bonus", 0))

    f["ac"] = int(ac)
    return int(ac)
