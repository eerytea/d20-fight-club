# core/spells_meta.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple

"""
Lightweight spell metadata & helpers used by ratings/tactics.

You can extend SPELLS_CATALOG as you wire real spell lists.
Tags we use for role fit:
- "buff", "debuff", "healing", "ranged", "aoe"
Additionally:
- base_damage_cantrip: True (exactly one or a small set)
- die: damage die string for base cantrips (e.g., "1d10")
"""

# --- Minimal starter catalog (extend freely) ---
SPELLS_CATALOG: Dict[str, Dict[str, Any]] = {
    # Damage cantrips (examples; rename to your canonical names later)
    "Arcane Bolt": {"tags": ["ranged"], "base_damage_cantrip": True, "die": "1d10"},
    "Fire Bolt":   {"tags": ["ranged"], "base_damage_cantrip": True, "die": "1d10"},
    # Utility examples (non-damaging)
    "Mending Chant": {"tags": ["healing"]},
    "Battle Hymn":   {"tags": ["buff"]},
    "Sapping Hex":   {"tags": ["debuff"]},
    "Flame Burst":   {"tags": ["aoe", "ranged"]},  # leveled example (not a cantrip)
}

# For unknown spells, you can optionally set a default tag map here
DEFAULT_UNKNOWN_SPELL_TAGS: List[str] = []

def _parse_die(d: str) -> Tuple[int, int]:
    try:
        n, s = str(d).lower().split("d")
        return max(1, int(n)), max(1, int(s))
    except Exception:
        return (1, 6)

def tags_for_spell(name: str) -> List[str]:
    meta = SPELLS_CATALOG.get(str(name), {})
    return list(meta.get("tags", DEFAULT_UNKNOWN_SPELL_TAGS))

def is_base_damage_cantrip(name: str) -> bool:
    return bool(SPELLS_CATALOG.get(str(name), {}).get("base_damage_cantrip", False))

def base_cantrip_die(name: str) -> str:
    return str(SPELLS_CATALOG.get(str(name), {}).get("die", "1d10"))

def count_spell_tags(player: Dict[str, Any]) -> Dict[str, int]:
    """
    Count known spells by our role-relevant tags.
    """
    known = player.get("known_spells") or []
    out = {"buff": 0, "debuff": 0, "healing": 0, "ranged": 0, "aoe": 0}
    for s in known:
        for t in tags_for_spell(s):
            if t in out:
                out[t] += 1
    return out

def find_base_damage_cantrip(player: Dict[str, Any]) -> str | None:
    """
    Return the first known spell flagged as base damage cantrip, else None.
    """
    known = player.get("known_spells") or []
    for s in known:
        if is_base_damage_cantrip(s):
            return s
    # Fallback: if the player has NO known spells marked but is a Wizard,
    # you can choose to pretend they know one; we keep it None to be explicit.
    return None

def base_cantrip_die_and_tier(player: Dict[str, Any]) -> Tuple[str, int]:
    """
    Returns (die_string, tier) to estimate caster DPR.
    Tier usually grows with level (e.g., 1/5/11/17). We read any engine flag if present.
    """
    name = find_base_damage_cantrip(player)
    die = base_cantrip_die(name) if name else "1d8"
    tier = int(player.get("wiz_cantrip_tier", 1))
    return (die, max(1, tier))
