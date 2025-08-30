# core/classes.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional

from core.ac import calc_ac

# ---------- Item helpers ----------
def weapon(name: str, dice: str, *, reach: int = 1, finesse: bool = False,
           ability: str = "STR", ranged: bool = False,
           range_tuple: Tuple[int, int] = (8, 16)) -> Dict[str, Any]:
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
    # Leather -> AC = 11 + DEX == 10 + DEX + 1
    return {"type": "armor", "name": name, "armor_bonus": int(armor_bonus)}

# ---------- Class starting kits ----------
CLASS_STARTING_KIT: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "Barbarian": {
        "weapons": [
            weapon("Greataxe", "1d12", ability="STR"),
            weapon("Hand Axe", "1d6", ability="STR"),
            weapon("Hand Axe", "1d6", ability="STR"),
        ],
        "armors": [],
    },
    "Bard": {
        "weapons": [
            weapon("Rapier", "1d8", finesse=True),
            weapon("Longsword", "1d8", ability="STR"),
            weapon("Dagger", "1d4", finesse=True),  # <-- flipped to finesse
        ],
        "armors": [
            armor("Leather Armor", 1),
        ],
    },
}

# ---------- Proficiency Bonus (global) ----------
def proficiency_for_level(level: int) -> int:
    """1–4: +2, 5–8: +3, 9–12: +4, 13–16: +5, 17–20: +6"""
    L = max(1, int(level))
    return min(6, 2 + (L - 1) // 4)

# ---------- Barbarian (as shipped previously) ----------
_BARB_ASI_LEVELS = {4, 8, 12, 16, 19}

def _apply_barbarian_init(f: Dict[str, Any]) -> None:
    f["barb_unarmored_ac"] = True
    f["rage_active"] = False
    f["rage_bonus_per_level"] = 0
    f["resist_all"] = False
    f["_dealt_damage_this_turn"] = False
    f["barb_extra_attacks"] = 0
    f["barb_crit_extra_dice"] = 0
    f["barb_initiative_advantage"] = False
    f["barb_speed_bonus_if_unarmored"] = 0
    f["barb_rage_capstone"] = False
    f["barb_cap_24"] = False
    con_mod = (int(f.get("CON", f.get("con", 10))) - 10) // 2
    base_hp = 12 + con_mod
    f["hp"] = max(1, base_hp)
    f["max_hp"] = max(int(f.get("max_hp", f["hp"])), f["hp"])
    f["ac"] = calc_ac(f)

def _apply_barbarian_level_features(f: Dict[str, Any], new_level: int) -> None:
    f["max_hp"] = int(f.get("max_hp", f.get("hp", 1))) + 7
    if new_level >= 5:
        f["barb_extra_attacks"] = 1
        f["barb_speed_bonus_if_unarmored"] = 2
    if new_level >= 7:
        f["barb_initiative_advantage"] = True
    if new_level >= 9:
        bonus = 1 + (1 if new_level >= 13 else 0) + (1 if new_level >= 17 else 0)
        f["barb_crit_extra_dice"] = bonus
    if new_level >= 15:
        f["barb_rage_capstone"] = True
    if new_level >= 20:
        for k in ("STR", "CON"):
            v = int(f.get(k, 10)) + 4
            f[k] = min(v, 24)
            f[k.lower()] = f[k]
        f["barb_cap_24"] = True
        f["ac"] = calc_ac(f)

def _barbarian_needs_asi(level: int) -> bool:
    return level in _BARB_ASI_LEVELS

# ---------- Bard ----------
_BARD_ASI_LEVELS = {4, 8, 12, 16, 19}

# (cantrips_known, spells_known, slots[1..9])
_BARD_TABLE: Dict[int, Tuple[int, int, List[int]]] = {
    1:  (2, 4,  [2,0,0,0,0,0,0,0,0]),
    2:  (2, 5,  [3,0,0,0,0,0,0,0,0]),
    3:  (2, 6,  [4,2,0,0,0,0,0,0,0]),
    4:  (3, 7,  [4,3,0,0,0,0,0,0,0]),
    5:  (3, 8,  [4,3,2,0,0,0,0,0,0]),
    6:  (3, 9,  [4,3,3,0,0,0,0,0,0]),
    7:  (3,10,  [4,3,3,1,0,0,0,0,0]),
    8:  (3,11,  [4,3,3,2,0,0,0,0,0]),
    9:  (3,12,  [4,3,3,3,1,0,0,0,0]),
    10: (4,14,  [4,3,3,3,2,0,0,0,0]),
    11: (4,15,  [4,3,3,3,2,1,0,0,0]),
    12: (4,15,  [4,3,3,3,2,1,0,0,0]),
    13: (4,16,  [4,3,3,3,2,1,1,0,0]),
    14: (4,18,  [4,3,3,3,2,1,1,0,0]),
    15: (4,19,  [4,3,3,3,2,1,1,1,0]),
    16: (4,19,  [4,3,3,3,2,1,1,1,0]),
    17: (4,20,  [4,3,3,3,2,1,1,1,1]),
    18: (4,22,  [4,3,3,3,3,1,1,1,1]),
    19: (4,22,  [4,3,3,3,3,2,1,1,1]),
    20: (4,22,  [4,3,3,3,3,2,2,1,1]),
}

def _apply_bard_init(f: Dict[str, Any]) -> None:
    con_mod = (int(f.get("CON", f.get("con", 10))) - 10) // 2
    base_hp = 8 + con_mod
    f["hp"] = max(1, base_hp)
    f["max_hp"] = max(int(f.get("max_hp", f["hp"])), f["hp"])

    f["spell_ability"] = "CHA"
    f["cantrips_known"] = 0
    f["spells_known"] = 0
    f["known_cantrips"] = []
    f["known_spells"] = []
    f["spell_slots_total"] = [0]*10
    f["spell_slots_current"] = [0]*10

    f["bard_inspiration_uses_per_battle"] = 1
    f["bard_inspiration_unlimited"] = False
    f["bard_aura_charm_fear"] = False

    f["ac"] = calc_ac(f)
    _apply_bard_casting_table_for_level(f, int(f.get("level", 1)))

def _apply_bard_casting_table_for_level(f: Dict[str, Any], L: int) -> None:
    cantrips, spells, slots = _BARD_TABLE.get(max(1, min(20, L)), (0, 0, [0]*9))
    f["cantrips_known"] = cantrips
    f["spells_known"] = spells
    pad = [0] + slots
    f["spell_slots_total"] = pad[:]
    if not f.get("spell_slots_current"):
        f["spell_slots_current"] = pad[:]

def _apply_bard_level_features(f: Dict[str, Any], new_level: int) -> None:
    f["max_hp"] = int(f.get("max_hp", f.get("hp", 1))) + 5
    _apply_bard_casting_table_for_level(f, new_level)
    if new_level >= 6:
        f["bard_aura_charm_fear"] = True
    if new_level >= 20:
        f["bard_inspiration_unlimited"] = True
        f["bard_inspiration_uses_per_battle"] = 999_999

def _bard_needs_asi(level: int) -> bool:
    return level in _BARD_ASI_LEVELS

# ---------- Shared: ASI allocator ----------
def _allocate_asi_via_training(f: Dict[str, Any], points: int, *, hard_caps: Dict[str, int]) -> None:
    weights = (f.get("training") or {}).get("growth_weights") or {}
    default_weights = {"STR": 0.15, "DEX": 0.20, "CON": 0.20, "INT": 0.10, "WIS": 0.15, "CHA": 0.20}
    if not weights:
        weights = default_weights
    order = sorted(weights.items(), key=lambda kv: (-kv[1], kv[0]))
    for _ in range(points):
        for k, _w in order:
            cap = hard_caps.get(k, 20)
            cur = int(f.get(k, 10))
            if cur < cap:
                f[k] = cur + 1
                f[k].__class__  # keep mypy quiet
                f[k.lower()] = f[k]
                break

# ---------- Public API ----------
def ensure_class_features(f: Dict[str, Any]) -> None:
    cls = str(f.get("class", "Fighter")).capitalize()
    if cls == "Barbarian":
        _apply_barbarian_init(f)
    elif cls == "Bard":
        _apply_bard_init(f)
    # others later

def apply_class_level_up(f: Dict[str, Any], new_level: int) -> None:
    cls = str(f.get("class", "Fighter")).capitalize()
    if cls == "Barbarian":
        _apply_barbarian_level_features(f, new_level)
        if _barbarian_needs_asi(new_level):
            cap_24 = bool(f.get("barb_cap_24", False))
            caps = {"STR": (24 if cap_24 else 20), "CON": (24 if cap_24 else 20),
                    "DEX": 20, "INT": 20, "WIS": 20, "CHA": 20}
            _allocate_asi_via_training(f, points=2, hard_caps=caps)
            f["ac"] = calc_ac(f)
    elif cls == "Bard":
        _apply_bard_level_features(f, new_level)
        if _bard_needs_asi(new_level):
            caps = {"STR": 20, "DEX": 20, "CON": 20, "INT": 20, "WIS": 20, "CHA": 20}
            _allocate_asi_via_training(f, points=2, hard_caps=caps)
            f["ac"] = calc_ac(f)

def grant_starting_kit(f: Dict[str, Any]) -> None:
    cls = str(f.get("class", "Fighter")).capitalize()
    kit = CLASS_STARTING_KIT.get(cls)
    if not kit:
        return
    inv = f.setdefault("inventory", {})
    weapons: List[Dict[str, Any]] = inv.setdefault("weapons", [])
    armors: List[Dict[str, Any]] = inv.setdefault("armors", [])
    eq = f.setdefault("equipped", {})
    def _assign_id(prefix: str, idx: int) -> str: return f"{prefix}_{idx}"
    for w in kit.get("weapons", []):
        weapons.append({**w, "id": _assign_id("w", len(weapons))})
    for a in kit.get("armors", []):
        armors.append({**a, "id": _assign_id("a", len(armors))})
    if weapons:
        eq["weapon_id"] = weapons[0]["id"]
        f["weapon"] = {k: v for k, v in weapons[0].items() if k != "id"}
    race = str(f.get("race", "")).lower()
    armor_allowed = (race != "lizardkin") and not bool(f.get("armor_prohibited", False))
    if armors and armor_allowed:
        eq["armor_id"] = armors[0]["id"]
        f["armor_bonus"] = int(armors[0].get("armor_bonus", 0))
    else:
        eq["armor_id"] = None
        f["armor_bonus"] = 0
    f["ac"] = calc_ac(f)
