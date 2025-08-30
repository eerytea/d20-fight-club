# core/classes.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional

from core.ac import calc_ac

# ---------- Item helpers ----------
def weapon(name: str, dice: str, *, reach: int = 1, finesse: bool = False,
           ability: str = "STR", ranged: bool = False,
           range_tuple: Tuple[int, int] = (8, 16),
           versatile: bool = False, two_handed_dice: Optional[str] = None,
           unarmed_flag: bool = False) -> Dict[str, Any]:
    """
    Generic weapon description used by engine.
    - finesse -> uses max(STR, DEX)
    - versatile -> can be two-handed if off-hand is empty; two_handed_dice if provided
    - unarmed_flag -> marks this as the synthetic 'Unarmed' option (special handling)
    """
    d: Dict[str, Any] = {"type": "weapon", "name": name, "dice": dice, "reach": reach}
    if finesse:
        d["finesse"] = True
    if ability and not finesse:
        d["ability"] = ability.upper()
    if ranged:
        d["ranged"] = True
        d["range"] = (int(range_tuple[0]), int(range_tuple[1]))
    if versatile:
        d["versatile"] = True
        if two_handed_dice:
            d["two_handed_dice"] = str(two_handed_dice)
    if unarmed_flag:
        d["unarmed"] = True
        d["versatile"] = True
        d["finesse"] = True  # use better of STR/DEX
    return d

def armor(name: str, armor_bonus: int) -> Dict[str, Any]:
    # Body armor contributes to armor_bonus (10 + DEX + armor_bonus)
    return {"type": "armor", "name": name, "armor_bonus": int(armor_bonus)}

def shield(name: str, shield_bonus: int = 2) -> Dict[str, Any]:
    # Shield stacks with any AC candidate (normal, natural, UD)
    return {"type": "shield", "name": name, "shield_bonus": int(shield_bonus)}

# ---------- Class starting kits ----------
# Always append a synthetic "Unarmed" option to everyone's inventory (done in grant_starting_kit).
UNARMED_ITEM = weapon("Unarmed", "1d1", finesse=True, versatile=True, unarmed_flag=True)

CLASS_STARTING_KIT: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    # Barbarian (from previous drop)
    "Barbarian": {
        "weapons": [
            weapon("Greataxe", "1d12", ability="STR"),
            weapon("Hand Axe", "1d6", ability="STR"),
            weapon("Hand Axe", "1d6", ability="STR"),
        ],
        "armors": [],
        "shields": [],
    },
    # Bard (from previous, with finesse dagger)
    "Bard": {
        "weapons": [
            weapon("Rapier", "1d8", finesse=True),
            weapon("Longsword", "1d8", ability="STR", versatile=True, two_handed_dice="1d10"),
            weapon("Dagger", "1d4", finesse=True),
        ],
        "armors": [armor("Leather Armor", 1)],
        "shields": [],
    },
    # NEW: Cleric
    "Cleric": {
        "weapons": [
            weapon("Mace", "1d6", ability="STR"),
            weapon("Warhammer", "1d8", ability="STR", versatile=True, two_handed_dice="1d10"),
        ],
        "armors": [
            armor("Leather Armor", 1),
            armor("Scale Mail", 4),
            armor("Chain Mail", 6),
        ],
        "shields": [shield("Shield", 2)],
    },
}

# ---------- Proficiency Bonus (global) ----------
def proficiency_for_level(level: int) -> int:
    """1–4: +2, 5–8: +3, 9–12: +4, 13–16: +5, 17–20: +6"""
    L = max(1, int(level))
    return min(6, 2 + (L - 1) // 4)

# ---------- Barbarian (as shipped) ----------
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

# ---------- Bard (as shipped) ----------
_BARD_ASI_LEVELS = {4, 8, 12, 16, 19}
# (cantrips_known, spells_known, slots[1..9]) – bard table (kept)
_BARD_TABLE: Dict[int, Tuple[int, int, List[int]]] = {
    1:(2,4,[2,0,0,0,0,0,0,0,0]),2:(2,5,[3,0,0,0,0,0,0,0,0]),
    3:(2,6,[4,2,0,0,0,0,0,0,0]),4:(3,7,[4,3,0,0,0,0,0,0,0]),
    5:(3,8,[4,3,2,0,0,0,0,0,0]),6:(3,9,[4,3,3,0,0,0,0,0,0]),
    7:(3,10,[4,3,3,1,0,0,0,0,0]),8:(3,11,[4,3,3,2,0,0,0,0,0]),
    9:(3,12,[4,3,3,3,1,0,0,0,0]),10:(4,14,[4,3,3,3,2,0,0,0,0]),
    11:(4,15,[4,3,3,3,2,1,0,0,0]),12:(4,15,[4,3,3,3,2,1,0,0,0]),
    13:(4,16,[4,3,3,3,2,1,1,0,0]),14:(4,18,[4,3,3,3,2,1,1,0,0]),
    15:(4,19,[4,3,3,3,2,1,1,1,0]),16:(4,19,[4,3,3,3,2,1,1,1,0]),
    17:(4,20,[4,3,3,3,2,1,1,1,1]),18:(4,22,[4,3,3,3,3,1,1,1,1]),
    19:(4,22,[4,3,3,3,3,2,1,1,1]),20:(4,22,[4,3,3,3,3,2,2,1,1]),
}

def _apply_bard_init(f: Dict[str, Any]) -> None:
    con_mod = (int(f.get("CON", f.get("con", 10))) - 10) // 2
    base_hp = 8 + con_mod
    f["hp"] = max(1, base_hp)
    f["max_hp"] = max(int(f.get("max_hp", f["hp"])), f["hp"])
    f["spell_ability"] = "CHA"
    f["cantrips_known"] = 0; f["spells_known"] = 0
    f["known_cantrips"] = []; f["known_spells"] = []
    f["spell_slots_total"] = [0]*10; f["spell_slots_current"] = [0]*10
    f["bard_inspiration_uses_per_battle"] = 1
    f["bard_inspiration_unlimited"] = False
    f["bard_aura_charm_fear"] = False
    f["ac"] = calc_ac(f)
    _apply_bard_casting_table_for_level(f, int(f.get("level", 1)))

def _apply_bard_casting_table_for_level(f: Dict[str, Any], L: int) -> None:
    cantrips, spells, slots = _BARD_TABLE.get(max(1, min(20, L)), (0, 0, [0]*9))
    f["cantrips_known"] = cantrips; f["spells_known"] = spells
    pad = [0] + slots
    f["spell_slots_total"] = pad[:]
    if not f.get("spell_slots_current"):
        f["spell_slots_current"] = pad[:]

def _apply_bard_level_features(f: Dict[str, Any], new_level: int) -> None:
    f["max_hp"] = int(f.get("max_hp", f.get("hp", 1))) + 5
    _apply_bard_casting_table_for_level(f, new_level)
    if new_level >= 6: f["bard_aura_charm_fear"] = True
    if new_level >= 20:
        f["bard_inspiration_unlimited"] = True
        f["bard_inspiration_uses_per_battle"] = 999_999

def _bard_needs_asi(level: int) -> bool:
    return level in _BARD_ASI_LEVELS

# ---------- Cleric (new) ----------
_CLERIC_ASI_LEVELS = {4, 8, 12, 16, 19}
# Cleric table (cantrips_known, slots[1..9]); clerics don't have "spells known" cap like bards, so we store 0.
_CLERIC_TABLE: Dict[int, Tuple[int, List[int]]] = {
    1:(3,[2,0,0,0,0,0,0,0,0]), 2:(3,[3,0,0,0,0,0,0,0,0]),
    3:(3,[4,2,0,0,0,0,0,0,0]), 4:(4,[4,3,0,0,0,0,0,0,0]),
    5:(4,[4,3,2,0,0,0,0,0,0]), 6:(4,[4,3,3,0,0,0,0,0,0]),
    7:(4,[4,3,3,1,0,0,0,0,0]), 8:(4,[4,3,3,2,0,0,0,0,0]),
    9:(4,[4,3,3,3,1,0,0,0,0]), 10:(5,[4,3,3,3,2,0,0,0,0]),
    11:(5,[4,3,3,3,2,1,0,0,0]), 12:(5,[4,3,3,3,2,1,0,0,0]),
    13:(5,[4,3,3,3,2,1,1,0,0]), 14:(5,[4,3,3,3,2,1,1,0,0]),
    15:(5,[4,3,3,3,2,1,1,1,0]), 16:(5,[4,3,3,3,2,1,1,1,0]),
    17:(5,[4,3,3,3,2,1,1,1,1]), 18:(5,[4,3,3,3,3,1,1,1,1]),
    19:(5,[4,3,3,3,3,2,1,1,1]), 20:(5,[4,3,3,3,3,2,2,1,1]),
}

def _apply_cleric_init(f: Dict[str, Any]) -> None:
    con_mod = (int(f.get("CON", f.get("con", 10))) - 10) // 2
    base_hp = 8 + con_mod
    f["hp"] = max(1, base_hp)
    f["max_hp"] = max(int(f.get("max_hp", f["hp"])), f["hp"])

    f["spell_ability"] = "WIS"
    f["cantrips_known"] = 0
    f["spells_known"] = 0  # clerics prepare; we keep 0 for uniformity
    f["known_cantrips"] = []
    f["known_spells"] = []
    f["spell_slots_total"] = [0]*10
    f["spell_slots_current"] = [0]*10

    f["ac"] = calc_ac(f)
    _apply_cleric_casting_table_for_level(f, int(f.get("level", 1)))

def _apply_cleric_casting_table_for_level(f: Dict[str, Any], L: int) -> None:
    cantrips, slots = _CLERIC_TABLE.get(max(1, min(20, L)), (0, [0]*9))
    f["cantrips_known"] = cantrips
    pad = [0] + slots
    f["spell_slots_total"] = pad[:]
    if not f.get("spell_slots_current"):
        f["spell_slots_current"] = pad[:]

def _apply_cleric_level_features(f: Dict[str, Any], new_level: int) -> None:
    f["max_hp"] = int(f.get("max_hp", f.get("hp", 1))) + 5
    _apply_cleric_casting_table_for_level(f, new_level)

def _cleric_needs_asi(level: int) -> bool:
    return level in _CLERIC_ASI_LEVELS

# ---------- Shared: ASI allocator ----------
def _allocate_asi_via_training(f: Dict[str, Any], points: int, *, hard_caps: Dict[str, int]) -> None:
    weights = (f.get("training") or {}).get("growth_weights") or {}
    default_weights = {"STR": 0.15, "DEX": 0.20, "CON": 0.20, "INT": 0.10, "WIS": 0.20, "CHA": 0.15}
    if not weights:
        weights = default_weights
    order = sorted(weights.items(), key=lambda kv: (-kv[1], kv[0]))
    for _ in range(points):
        for k, _w in order:
            cap = hard_caps.get(k, 20)
            cur = int(f.get(k, 10))
            if cur < cap:
                f[k] = cur + 1
                f[k.lower()] = f[k]
                break

# ---------- Public API ----------
def ensure_class_features(f: Dict[str, Any]) -> None:
    cls = str(f.get("class", "Fighter")).capitalize()
    if cls == "Barbarian":
        _apply_barbarian_init(f)
    elif cls == "Bard":
        _apply_bard_init(f)
    elif cls == "Cleric":
        _apply_cleric_init(f)
    # (others later)

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
    elif cls == "Cleric":
        _apply_cleric_level_features(f, new_level)
        if _cleric_needs_asi(new_level):
            caps = {"STR": 20, "DEX": 20, "CON": 20, "INT": 20, "WIS": 20, "CHA": 20}
            _allocate_asi_via_training(f, points=2, hard_caps=caps)
            f["ac"] = calc_ac(f)

def grant_starting_kit(f: Dict[str, Any]) -> None:
    """
    Adds class kit to inventory and auto-equips:
      - Main hand / Off hand / Armor / Shield tracked in f['equipped'].
      - Always adds 'Unarmed' to weapons.
      - Lizardkin: cannot equip body armor (shield allowed).
    """
    cls = str(f.get("class", "Fighter")).capitalize()
    kit = CLASS_STARTING_KIT.get(cls, {"weapons": [], "armors": [], "shields": []})

    inv = f.setdefault("inventory", {})
    weapons: List[Dict[str, Any]] = inv.setdefault("weapons", [])
    armors: List[Dict[str, Any]] = inv.setdefault("armors", [])
    shields: List[Dict[str, Any]] = inv.setdefault("shields", [])
    eq = f.setdefault("equipped", {})  # {"main_hand_id","off_hand_id","armor_id","shield_id"}

    def _assign_id(prefix: str, idx: int) -> str:
        return f"{prefix}_{idx}"

    # Append class kit
    for w in kit.get("weapons", []):
        weapons.append({**w, "id": _assign_id("w", len(weapons))})
    for a in kit.get("armors", []):
        armors.append({**a, "id": _assign_id("a", len(armors))})
    for s in kit.get("shields", []):
        shields.append({**s, "id": _assign_id("s", len(shields))})

    # Always add synthetic Unarmed option (front)
    if not any(w.get("unarmed") for w in weapons):
        weapons.insert(0, {**UNARMED_ITEM, "id": "unarmed"})

    # Auto-equip defaults
    # Armor: prefer Scale then Chain then Leather; Lizardkin can't wear armor
    race = str(f.get("race", "")).lower()
    armor_allowed = (race != "lizardkin") and not bool(f.get("armor_prohibited", False))
    armor_pick = None
    if armor_allowed and armors:
        # prefer Scale > Chain > Leather as spec suggested "Scale default"; fall back to first
        order = {"Scale Mail": 2, "Chain Mail": 1, "Leather Armor": 0}
        armors_sorted = sorted(armors, key=lambda a: order.get(a["name"], -1), reverse=True)
        armor_pick = armors_sorted[0]
        eq["armor_id"] = armor_pick["id"]
        f["armor_bonus"] = int(armor_pick.get("armor_bonus", 0))
    else:
        eq["armor_id"] = None
        f["armor_bonus"] = 0

    # Shield default for Cleric; allowed for all races/classes including Lizardkin
    shield_pick = shields[0] if shields else None
    if shield_pick:
        eq["shield_id"] = shield_pick["id"]
        f["shield_bonus"] = int(shield_pick.get("shield_bonus", 0))
    else:
        eq["shield_id"] = None
        f["shield_bonus"] = int(f.get("shield_bonus", 0))

    # Main hand: prefer Mace/primary, else first weapon
    main = None
    names = [w["name"] for w in weapons]
    if "Mace" in names:
        main = weapons[names.index("Mace")]
    else:
        main = weapons[0]
    eq["main_hand_id"] = main["id"]
    f["weapon"] = {k: v for k, v in main.items() if k != "id"}  # legacy field used by engine

    # Off hand: shield if available (and only if main is 1-handed or versatile used 1-hand)
    eq["off_hand_id"] = eq.get("off_hand_id")
    if shield_pick:
        eq["off_hand_id"] = shield_pick["id"]

    # AC recalc after equipping
    f["ac"] = calc_ac(f)
