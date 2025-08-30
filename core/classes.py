# core/classes.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple

from core.ac import calc_ac

# --- helpers to build equipment dict items ---
def weapon(name: str, dice: str, ability: str = "STR", finesse: bool = False,
           versatile: bool = False, two_handed_dice: str = "", two_handed: bool = False,
           ranged: bool = False, range_tuple: Tuple[int, int] = (8, 16), reach: int = 1,
           unarmed: bool = False) -> Dict[str, Any]:
    d = {"type": "weapon", "name": name, "dice": dice, "ability": ability,
         "finesse": finesse, "versatile": versatile, "two_handed_dice": two_handed_dice,
        "two_handed": two_handed, "ranged": ranged, "range": range_tuple, "reach": reach,
        "unarmed": unarmed}
    return d

def armor(name: str, bonus: int) -> Dict[str, Any]:
    return {"type": "armor", "name": name, "armor_bonus": int(bonus)}

def shield(name: str, bonus: int) -> Dict[str, Any]:
    return {"type": "shield", "name": name, "shield_bonus": int(bonus)}

UNARMED_ITEM = weapon("Unarmed Strike", "1d4", ability="STR", unarmed=True)

# ---------- Starting Kits ----------
CLASS_STARTING_KIT: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "Barbarian": {
        "weapons": [
            weapon("Greataxe", "1d12", ability="STR", two_handed=True),
            weapon("Hand Axe", "1d6", ability="STR"),
            weapon("Hand Axe", "1d6", ability="STR"),
        ],
        "armors": [],
        "shields": [],
    },
    "Bard": {
        "weapons": [
            weapon("Rapier", "1d8", finesse=True),
            weapon("Longsword", "1d8", ability="STR", versatile=True, two_handed_dice="1d10"),
            weapon("Dagger", "1d4", finesse=True),
        ],
        "armors": [armor("Leather Armor", 1)],
        "shields": [],
    },
    "Cleric": {
        "weapons": [
            weapon("Mace", "1d6", ability="STR"),
            weapon("Warhammer", "1d8", ability="STR", versatile=True, two_handed_dice="1d10"),
        ],
        "armors": [armor("Chain Shirt", 2)],
        "shields": [shield("Shield", 2)],
    },
    "Druid": {
        "weapons": [weapon("Scimitar", "1d6", finesse=True)],
        "armors": [armor("Leather Armor", 1)],
        "shields": [shield("Shield", 2)],
    },
    # Fighter styles:
    "Archer": {
        "weapons": [
            weapon("Longbow", "1d8", ability="DEX", ranged=True, range_tuple=(2, 4), two_handed=True),
        ],
        "armors": [armor("Chain Mail", 3)],
        "shields": [],
    },
    "Defender": {
        "weapons": [
            weapon("Longsword", "1d8", ability="STR", versatile=True, two_handed_dice="1d10"),
        ],
        "armors": [armor("Plate", 5)],
        "shields": [shield("Shield", 2)],
    },
    "Enforcer": {
        "weapons": [
            weapon("Halberd", "1d12", ability="STR", reach=2, two_handed=True),
        ],
        "armors": [armor("Scale Mail", 4)],  # retro rename
        "shields": [],
    },
    "Duelist": {
        "weapons": [
            weapon("Shortsword", "1d6", finesse=True),
            weapon("Shortsword", "1d6", finesse=True),
        ],
        "armors": [armor("Scale Mail", 4)],
        "shields": [],
    },

    # Monk: no equipment
    "Monk": {
        "weapons": [],
        "armors": [],
        "shields": [],
    },
    "Rogue": {
        "weapons": [
            weapon("Rapier", "1d8", finesse=True),
            weapon("Dagger", "1d4", finesse=True),
        ],
        "armors": [armor("Leather Armor", 1)],
        "shields": [],
    },

    # New: Ranger (no spells)
    "Ranger": {
        "weapons": [
            weapon("Longbow", "1d8", ability="DEX", ranged=True, range_tuple=(2, 4), two_handed=True),
            weapon("Shortsword", "1d6", finesse=True),
            weapon("Shortsword", "1d6", finesse=True),
        ],
        "armors": [armor("Scale Mail", 4), armor("Leather Armor", 1)],
        "shields": [],
    },
}

FIGHTER_STYLE_CLASSES = {"Archer", "Defender", "Enforcer", "Duelist"}

# ---------- HP TABLE ----------
_HP_TABLE: Dict[str, Tuple[int, int]] = {
    "Barbarian": (12, 7),
    "Bard":      (8, 5),
    "Cleric":    (8, 5),
    "Druid":     (8, 5),
    "Archer":    (10, 6),  # Fighter styles
    "Defender":  (10, 6),
    "Enforcer":  (10, 6),
    "Duelist":   (10, 6),
    "Monk":      (8, 5),
    "Rogue":     (8, 5),

    "Ranger":    (10, 6),
}

def _mod(x: int) -> int:
    return (int(x) - 10) // 2

def _recompute_hp_from_formula(f: Dict[str, Any]) -> None:
    cls = str(f.get("class", "Fighter")).capitalize()
    base, per = _HP_TABLE.get(cls, (8, 5))
    con_mod = _mod(int(f.get("CON", 10)))
    lvl = int(f.get("level", f.get("lvl", 1)))
    f["max_hp"] = int(base + max(0, lvl - 1) * per + con_mod)
    f["hp"] = min(int(f.get("hp", f["max_hp"])), f["max_hp"])

# … (rest of class-level feature helpers unchanged) …

def ensure_class_features(f: Dict[str, Any]) -> None:
    cls = str(f.get("class", "Fighter")).capitalize()
    if cls == "Barbarian":
        _apply_barbarian_init(f)
    elif cls == "Bard":
        _apply_bard_init(f)
    elif cls == "Cleric":
        _apply_cleric_init(f)
    elif cls == "Druid":
        _apply_druid_init(f)
    elif cls in FIGHTER_STYLE_CLASSES:
        _apply_fighter_init(f)
    elif cls == "Monk":
        _apply_monk_init(f)
    elif cls == "Rogue":
        _apply_rogue_init(f)

    # derived
    _recompute_hp_from_formula(f)
    f["ac"] = calc_ac(f)

def apply_class_level_up(f: Dict[str, Any], new_level: int) -> None:
    # (no changes needed for Ranger here; Ranger perks are handled in combat & ac)
    cls = str(f.get("class", "Fighter")).capitalize()
    # existing class level-ups unchanged…
    return

def grant_starting_kit(f: Dict[str, Any]) -> None:
    """
    Adds class kit; sets up equipment model:
      - f['equipped']: main_hand_id, off_hand_id, armor_id, shield_id
      - Always injects 'Unarmed'.
      - Lizardkin: cannot equip body armor; shield still allowed.
      - Two-handed main-hand clears off-hand/shield.
    """
    cls = str(f.get("class", "Fighter")).capitalize()
    kit = CLASS_STARTING_KIT.get(cls, {"weapons": [], "armors": [], "shields": []})

    inv = f.setdefault("inventory", {})
    weapons: List[Dict[str, Any]] = inv.setdefault("weapons", [])
    armors: List[Dict[str, Any]] = inv.setdefault("armors", [])
    shields: List[Dict[str, Any]] = inv.setdefault("shields", [])
    forms: List[Dict[str, Any]] = inv.setdefault("forms", [])  # for Druids

    eq = f.setdefault("equipped", {})

    def _assign_id(prefix: str, idx: int) -> str:
        return f"{prefix}_{idx}"

    for w in kit.get("weapons", []):
        weapons.append({**w, "id": _assign_id("w", len(weapons))})
    for a in kit.get("armors", []):
        armors.append({**a, "id": _assign_id("a", len(armors))})
    for s in kit.get("shields", []):
        shields.append({**s, "id": _assign_id("s", len(shields))})

    # Universal Unarmed
    if not any(w.get("unarmed") for w in weapons):
        weapons.insert(0, {**UNARMED_ITEM, "id": "unarmed"})

    # Armor allowance (lizardkin rule enforced)
    race = str(f.get("race", "")).lower()
    armor_allowed = (race != "lizardkin") and not bool(f.get("armor_prohibited", False))

    if armor_allowed and armors:
        pick = max(armors, key=lambda a: int(a.get("armor_bonus", 0)))
        eq["armor_id"] = pick["id"]
        f["armor_bonus"] = int(pick.get("armor_bonus", 0))
    else:
        eq["armor_id"] = None
        f["armor_bonus"] = 0

    # Shield
    if shields:
        eq["shield_id"] = shields[0]["id"]
        f["shield_bonus"] = int(shields[0].get("shield_bonus", 0))
    else:
        eq["shield_id"] = None
        f["shield_bonus"] = 0

    # Choose main-hand: pick something sensible per class
    names = [w["name"] for w in weapons]
    main = weapons[0]
    if cls == "Cleric" and "Mace" in names: main = weapons[names.index("Mace")]
    if cls == "Druid" and "Scimitar" in names: main = weapons[names.index("Scimitar")]
    if cls == "Archer" and "Longbow" in names: main = weapons[names.index("Longbow")]
    if cls == "Defender" and "Longsword" in names: main = weapons[names.index("Longsword")]
    if cls == "Enforcer" and "Halberd" in names: main = weapons[names.index("Halberd")]
    if cls == "Ranger" and "Longbow" in names: main = weapons[names.index("Longbow")]
    if cls == "Duelist" and "Shortsword" in names: main = weapons[names.index("Shortsword")]
    if cls == "Monk":
        main = weapons[0]  # Unarmed preferred
    if cls == "Rogue" and "Rapier" in names:
        main = weapons[names.index("Rapier")]

    eq["main_hand_id"] = main["id"]
    f["weapon"] = {k: v for k, v in main.items() if k != "id"}

    # Off-hand default
    if cls == "Duelist":
        others = [w for w in weapons if w["name"] == "Shortsword" and w["id"] != main["id"]]
        eq["off_hand_id"] = others[0]["id"] if others else None
    elif cls == "Defender" and shields:
        eq["off_hand_id"] = shields[0]["id"]
    elif cls == "Rogue":
        daggers = [w for w in weapons if w["name"] == "Dagger"]
        eq["off_hand_id"] = daggers[0]["id"] if daggers else None
    elif cls == "Ranger":
        ss = [w for w in weapons if w["name"] == "Shortsword" and w["id"] != main["id"]]
        eq["off_hand_id"] = ss[0]["id"] if ss else None
    else:
        eq["off_hand_id"] = None

    # Two-handed enforcement
    if bool(main.get("two_handed", False)):
        eq["off_hand_id"] = None
        eq["shield_id"] = None
        f["shield_bonus"] = 0

    if cls == "Druid":
        inv.setdefault("forms", forms)

    # finalize derived
    _recompute_hp_from_formula(f)
    f["ac"] = calc_ac(f)
