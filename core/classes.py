# core/classes.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional

from core.ac import calc_ac

# ---------- Item helpers (lightweight schema) ----------
# Weapon dicts are compatible with TBCombat's expectations.
def weapon(name: str, dice: str, *, reach: int = 1, finesse: bool = False, ability: str = "STR",
           ranged: bool = False, range_tuple: Tuple[int, int] = (8, 16)) -> Dict[str, Any]:
    d: Dict[str, Any] = {"type": "weapon", "name": name, "dice": dice, "reach": reach}
    if finesse:
        d["finesse"] = True
    if ability and not finesse:
        d["ability"] = ability.upper()
    if ranged:
        d["ranged"] = True
        d["range"] = (int(range_tuple[0]), int(range_tuple[1]))
    return d

def armor(name: str, armor_bonus: int) -> Dict[str, Any]:
    return {"type": "armor", "name": name, "armor_bonus": int(armor_bonus)}

# ---------- Class: starting kits ----------
# Add more classes later; for now we only populate Barbarian.
CLASS_STARTING_KIT: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "Barbarian": {
        "weapons": [
            weapon("Greataxe", "1d12", ability="STR"),
            weapon("Hand Axe", "1d6", ability="STR"),
            weapon("Hand Axe", "1d6", ability="STR"),
        ],
        "armors": [],  # barbarians can wear, but kit gives none; also Lizardkin can never equip armor
    },
}

# ---------- Class: feature application ----------
# Central switchboard for class init (at creation) and level-up steps.

# ASI (Ability Score Increase) levels for Barbarian.
_BARB_ASI_LEVELS = {4, 8, 12, 16, 19}

def _apply_barbarian_init(f: Dict[str, Any]) -> None:
    """Initialize Barbarian flags for a fresh L1 character (after stats are present)."""
    # Unarmored Defense is always available (applies only when no armor equipped).
    f["barb_unarmored_ac"] = True
    # Rage state (battle runtime, defaults off)
    f["rage_active"] = False
    f["rage_bonus_per_level"] = 0  # becomes 1 while raging
    f["resist_all"] = False
    f["_dealt_damage_this_turn"] = False

    # Feature flags, grow with level
    f["barb_extra_attacks"] = 0               # +1 at L5
    f["barb_crit_extra_dice"] = 0            # +1/+2/+3 at L9/13/17
    f["barb_initiative_advantage"] = False   # True at L7+
    f["barb_speed_bonus_if_unarmored"] = 0   # +2 at L5+
    f["barb_rage_capstone"] = False          # True at L15+
    f["barb_cap_24"] = False                 # True at L20 after STR/CON +4

    # HP at level 1 = 12 + CON mod (replace any default)
    con_mod = (int(f.get("CON", f.get("con", 10))) - 10) // 2
    base_hp = 12 + con_mod
    f["hp"] = max(1, base_hp)
    f["max_hp"] = max(int(f.get("max_hp", f["hp"])), f["hp"])

    # Recompute AC (so UD wins if applicable)
    f["ac"] = calc_ac(f)

def _apply_barbarian_level_features(f: Dict[str, Any], new_level: int) -> None:
    """Apply per-level feature switches for Barbarian (call on every level up)."""
    # Each level: +7 HP flat (race extras are handled elsewhere)
    f["max_hp"] = int(f.get("max_hp", f.get("hp", 1))) + 7
    # Heal up a bit if desired; we won't auto-heal now—leave current hp as-is

    # Feature thresholds
    if new_level >= 5:
        f["barb_extra_attacks"] = 1
        f["barb_speed_bonus_if_unarmored"] = 2
    if new_level >= 7:
        f["barb_initiative_advantage"] = True
    if new_level >= 9:
        # 9/13/17 -> 1/2/3
        bonus = 1 + (1 if new_level >= 13 else 0) + (1 if new_level >= 17 else 0)
        f["barb_crit_extra_dice"] = bonus
    if new_level >= 15:
        f["barb_rage_capstone"] = True
    if new_level >= 20:
        # STR+4, CON+4; caps to 24 (only for these two)
        for k in ("STR", "CON"):
            v = int(f.get(k, 10)) + 4
            f[k] = min(v, 24)
            f[k.lower()] = f[k]
        f["barb_cap_24"] = True
        # AC may change (UD improves)
        f["ac"] = calc_ac(f)

def _barbarian_needs_asi(level: int) -> bool:
    return level in _BARB_ASI_LEVELS

def _allocate_asi_via_training(f: Dict[str, Any], points: int, *, hard_caps: Dict[str, int]) -> None:
    """
    Greedy ASI: push 'points' into ability scores using f['training']['growth_weights'] (if present).
    Caps default to 20, but STR/CON may be 24 for Barbarian capstone.
    """
    weights = (f.get("training") or {}).get("growth_weights") or {}
    # Fall back to simple fighter-ish weights if none
    default_weights = {"STR": 0.35, "DEX": 0.25, "CON": 0.25, "INT": 0.05, "WIS": 0.05, "CHA": 0.05}
    if not weights:
        weights = default_weights
    # Order by weight desc, then deterministic key order for stability
    order = sorted(weights.items(), key=lambda kv: (-kv[1], kv[0]))
    for _ in range(points):
        for k, _w in order:
            cap = hard_caps.get(k, 20)
            cur = int(f.get(k, 10))
            if cur < cap:
                f[k] = cur + 1
                f[k.lower()] = f[k]
                break

def ensure_class_features(f: Dict[str, Any]) -> None:
    """
    Call this after a fighter has its 'class' and base stats.
    Sets init flags and recomputes AC/HP if needed. Does not add levels.
    """
    cls = str(f.get("class", "Fighter")).capitalize()
    if cls == "Barbarian":
        _apply_barbarian_init(f)
    # (Add other classes here later)

def apply_class_level_up(f: Dict[str, Any], new_level: int) -> None:
    """
    Call this when a fighter levels up (class-specific track only).
    Does not handle XP thresholds; you should call this for each level gained.
    """
    cls = str(f.get("class", "Fighter")).capitalize()
    if cls == "Barbarian":
        _apply_barbarian_level_features(f, new_level)
        # ASI at 4/8/12/16/19: +2 split by training plan, cap 20 (24 for STR/CON if L20 cap toggled)
        if _barbarian_needs_asi(new_level):
            cap_24 = bool(f.get("barb_cap_24", False))
            caps = {"STR": (24 if cap_24 else 20), "CON": (24 if cap_24 else 20)}
            # Others default to 20
            for k in ("DEX", "INT", "WIS", "CHA"):
                caps.setdefault(k, 20)
            _allocate_asi_via_training(f, points=2, hard_caps=caps)
            f["ac"] = calc_ac(f)  # AC may change if DEX/CON moved

def grant_starting_kit(f: Dict[str, Any]) -> None:
    """
    Adds class starting equipment to the fighter's inventory and auto-equips sensible defaults.
    - Lizardkin: never equip armor; their 'armor_bonus' must remain 0.
    """
    cls = str(f.get("class", "Fighter")).capitalize()
    kit = CLASS_STARTING_KIT.get(cls)
    if not kit:
        return

    # Ensure inventory structs
    inv = f.setdefault("inventory", {})
    weapons: List[Dict[str, Any]] = inv.setdefault("weapons", [])
    armors: List[Dict[str, Any]] = inv.setdefault("armors", [])
    eq = f.setdefault("equipped", {})

    # Assign simple deterministic IDs (length-based)
    def _assign_id(prefix: str, idx: int) -> str:
        return f"{prefix}_{idx}"

    # Add weapons
    for w in kit.get("weapons", []):
        weapons.append({**w, "id": _assign_id("w", len(weapons))})
    # Add armors
    for a in kit.get("armors", []):
        armors.append({**a, "id": _assign_id("a", len(armors))})

    # Auto-equip: first weapon if any
    if weapons:
        eq["weapon_id"] = weapons[0]["id"]
        f["weapon"] = {k: v for k, v in weapons[0].items() if k != "id"}

    # Armor: equip first armor only if allowed (not Lizardkin)
    race = str(f.get("race", "")).lower()
    armor_allowed = (race != "lizardkin") and not bool(f.get("armor_prohibited", False))
    if armors and armor_allowed:
        eq["armor_id"] = armors[0]["id"]
        f["armor_bonus"] = int(armors[0].get("armor_bonus", 0))
    else:
        eq["armor_id"] = None
        f["armor_bonus"] = 0

    # Recompute AC after equipping
    f["ac"] = calc_ac(f)
