# core/ac.py
from __future__ import annotations
from typing import Any, Dict

def _mod(stat: int) -> int:
    return (int(stat) - 10) // 2

def calc_ac(f: Dict[str, Any]) -> int:
    """Unified AC formula: 10 + DEX mod + armor_bonus.
    We keep it simple per project scope; if f already had an 'ac' set, we return
    the higher of the two (so callers can seed base_ac for special cases).
    """
    dex = int(f.get("DEX", f.get("dex", 10)))
    armor_bonus = int(f.get("armor_bonus", f.get("armor", 0)))
    computed = 10 + _mod(dex) + armor_bonus
    try:
        base = int(f.get("ac", computed))
    except Exception:
        base = computed
    return max(computed, base)
