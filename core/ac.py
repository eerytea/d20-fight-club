# core/classes.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional

from core.ac import calc_ac

# ---------- Item helpers ----------
def weapon(name: str, dice: str, *, reach: int = 1, finesse: bool = False,
           ability: str = "STR", ranged: bool = False,
           range_tuple: Tuple[int, int] = (8, 16),
           versatile: bool = False, two_handed_dice: Optional[str] = None,
           unarmed_flag: bool = False, wildshape_flag: bool = False) -> Dict[str, Any]:
    """
    Generic weapon description used by engine & UI.
    - finesse -> uses max(STR, DEX)
    - versatile -> auto two-handed when off-hand empty; 'two_handed_dice' if provided
    - unarmed_flag -> universal unarmed (finesse, 1d1) unless race overrides unarmed_dice
    - wildshape_flag -> special equippable that means "start battle shaped" (off-hand = 'form')
    """
    d: Dict[str, Any] = {"type": "weapon", "name": name, "dice": dice, "reach": reach}
    if finesse: d["finesse"] = True
    if ability and not finesse: d["ability"] = ability.upper()
    if ranged:
        d["ranged"] = True
        d["range"] = (int(range_tuple[0]), int(range_tuple[1]))
    if versatile:
        d["versatile"] = True
        if two_handed_dice: d["two_handed_dice"] = str(two_handed_dice)
    if unarmed_flag:
        d["unarmed"] = True
        d["versatile"] = True
        d["finesse"] = True
    if wildshape_flag:
        d["wildshape"] = True
        # 'dice' is irrelevant; engine swaps stats from chosen form
    return d

def armor(name: str, armor_bonus: int) -> Dict[str, Any]:
    return {"type": "armor", "name": name, "armor_bonus": int(armor_bonus)}

def shield(name: str, shield_bonus: int = 2) -> Dict[str, Any]:
    return {"type": "shield", "name": name, "shield_bonus": int(shield_bonus)}

def wild_form(name: str, *, cr: float, stats: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Placeholder container for a Wild Shape form (your future animals will fill these).
    'stats' (optional) may include: hp, max_hp, ac, speed, STR/DEX/CON/INT/WIS/CHA, natural_weapon:{dice, reach, finesse?}
    """
    return {"type": "wild_form", "name": name, "cr": float(cr), "stats": (stats or {})}

# ---------- Universal "Unarmed" option ----------
UNARMED_ITEM = weapon("Unarmed", "1d1", finesse=True, versatile=True, unarmed_flag=True)

# ---------- Class starting kits ----------
CLASS_STARTING_KIT: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    # Barbarian (unchanged other than global no-prof-to-damage handled in engine)
    "Barbarian": {
        "weapons": [
            weapon("Greataxe", "1d12", ability="STR"),
            weapon("Hand Axe", "1d6", ability="STR"),
            weapon("Hand Axe", "1d6", ability="STR"),
        ],
        "armors": [],
        "shields": [],
    },
    # Bard (kept; dagger is finesse)
    "Bard": {
        "weapons": [
            weapon("Rapier", "1d8", finesse=True),
            weapon("Longsword", "1d8", ability="STR", versatile=True, two_handed_dice="1d10"),
            weapon("Dagger", "1d4", finesse=True),
        ],
        "armors": [armor("Leather Armor", 1)],
        "shields": [],
    },
    # Cleric (kept)
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
    # NEW: Druid
    "Druid": {
        "weapons": [
            weapon("Scimitar", "1d6", finesse=True),
            weapon("Wild Shape", "1d0", wildshape_flag=True),  # selecting this in main-hand means "start shaped"
        ],
        "armors": [armor("Leather Armor", 1)],
        "shields": [shield("Shield", 2)],
        # inventory['forms'] will be populated later when you add animals
    },
}

# ---------- Proficiency Bonus (global) ----------
def proficiency_for_level(level: int) -> int:
    """1–4: +2, 5–8: +3, 9–12: +4, 13–16: +5, 17–20: +6"""
    L = max(1, int(level))
    return min(6, 2 + (L - 1) // 4)

# ---------- Barbarian + Bard + Cleric (unchanged from previous drop) ----------
_BARB_ASI_LEVELS = {4, 8, 12, 16, 19}
_BARD_ASI_LEVELS = {4, 8, 12, 16, 19}
_CLERIC_ASI_LEVELS = {4, 8, 12, 16, 19}

# Bard table (cantrips_known, spells_known, slots[1..9]) — kept
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

# Cleric table (cantrips_known, slots[1..9])
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

# Druid table (cantrips_known, slots[1..9]) from your screenshot
_DRUID_TABLE: Dict[int, Tuple[int, List[int]]] = {
    1:(2,[2,0,0,0,0,0,0,0,0]),  2:(2,[3,0,0,0,0,0,0,0,0]),
    3:(2,[4,2,0,0,0,0,0,0,0]),  4:(3,[4,3,0,0,0,0,0,0,0]),
    5:(3,[4,3,2,0,0,0,0,0,0]),  6:(3,[4,3,3,0,0,0,0,0,0]),
    7:(3,[4,3,3,1,0,0,0,0,0]),  8:(3,[4,3,3,2,0,0,0,0,0]),
    9:(3,[4,3,3,3,1,0,0,0,0]),  10:(4,[4,3,3,3,2,0,0,0,0]),
    11:(4,[4,3,3,3,2,1,0,0,0]), 12:(4,[4,3,3,3,2,1,0,0,0]),
    13:(4,[4,3,3,3,2,1,1,0,0]), 14:(4,[4,3,3,3,2,1,1,0,0]),
    15:(4,[4,3,3,3,2,1,1,1,0]), 16:(4,[4,3,3,3,2,1,1,1,0]),
    17:(4,[4,3,3,3,2,1,1,1,1]), 18:(4,[4,3,3,3,3,1,1,1,1]),
    19:(4,[4,3,3,3,3,2,1,1,1]), 20:(4,[4,3,3,3,3,2,2,1,1]),
}

# ---------- Class init/level-up hooks ----------
def _apply_barbarian_init(f: Dict[str, Any]) -> None:
    # (unchanged)
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

def _apply_bard_init(f: Dict[str, Any]) -> None:
    con_mod = (int(f.get("CON", f.get("con", 10))) - 10) // 2
    f["hp"] = max(1, 8 + con_mod)
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
    if not f.get("spell_slots_current"): f["spell_slots_current"] = pad[:]

def _apply_bard_level_features(f: Dict[str, Any], new_level: int) -> None:
    f["max_hp"] = int(f.get("max_hp", f.get("hp", 1))) + 5
    _apply_bard_casting_table_for_level(f, new_level)
    if new_level >= 6: f["bard_aura_charm_fear"] = True
    if new_level >= 20:
        f["bard_inspiration_unlimited"] = True
        f["bard_inspiration_uses_per_battle"] = 999_999

def _bard_needs_asi(level: int) -> bool:
    return level in _BARD_ASI_LEVELS

def _apply_cleric_init(f: Dict[str, Any]) -> None:
    con_mod = (int(f.get("CON", f.get("con", 10))) - 10) // 2
    f["hp"] = max(1, 8 + con_mod)
    f["max_hp"] = max(int(f.get("max_hp", f["hp"])), f["hp"])
    f["spell_ability"] = "WIS"
    f["cantrips_known"] = 0
    f["spells_known"] = 0
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
    if not f.get("spell_slots_current"): f["spell_slots_current"] = pad[:]

def _apply_cleric_level_features(f: Dict[str, Any], new_level: int) -> None:
    f["max_hp"] = int(f.get("max_hp", f.get("hp", 1))) + 5
    _apply_cleric_casting_table_for_level(f, new_level)

def _cleric_needs_asi(level: int) -> bool:
    return level in _CLERIC_ASI_LEVELS

# ----- NEW: Druid -----
_DRUID_ASI_LEVELS = {4, 8, 12, 16, 19}

def _druid_allowed_cr(level: int) -> List[float]:
    out: List[float] = []
    if level >= 2: out.append(0.25)
    if level >= 4: out.append(0.5)
    if level >= 8: out.append(1.0)
    return out

def _apply_druid_init(f: Dict[str, Any]) -> None:
    con_mod = (int(f.get("CON", f.get("con", 10))) - 10) // 2
    f["hp"] = max(1, 8 + con_mod)
    f["max_hp"] = max(int(f.get("max_hp", f["hp"])), f["hp"])

    f["spell_ability"] = "WIS"
    f["cantrips_known"] = 0
    f["spells_known"] = 0   # we treat “known”/prepared as sticky later; can stay 0 for now
    f["known_cantrips"] = []
    f["known_spells"] = []
    f["spell_slots_total"] = [0]*10
    f["spell_slots_current"] = [0]*10
    f["spell_slots_unlimited"] = False  # set True at level 20

    # Wild Shape gates
    f["wildshape_allowed_cr"] = _druid_allowed_cr(int(f.get("level", 1)))
    f["wildshape_cast_while_shaped"] = False  # becomes True at level 18

    f["ac"] = calc_ac(f)
    _apply_druid_casting_table_for_level(f, int(f.get("level", 1)))

def _apply_druid_casting_table_for_level(f: Dict[str, Any], L: int) -> None:
    cantrips, slots = _DRUID_TABLE.get(max(1, min(20, L)), (0, [0]*9))
    f["cantrips_known"] = cantrips
    pad = [0] + slots
    f["spell_slots_total"] = pad[:]
    if not f.get("spell_slots_current"): f["spell_slots_current"] = pad[:]
    # Level thresholds
    f["wildshape_allowed_cr"] = _druid_allowed_cr(L)
    f["wildshape_cast_while_shaped"] = (L >= 18)
    f["spell_slots_unlimited"] = (L >= 20)

def _apply_druid_level_features(f: Dict[str, Any], new_level: int) -> None:
    f["max_hp"] = int(f.get("max_hp", f.get("hp", 1))) + 5
    _apply_druid_casting_table_for_level(f, new_level)

def _druid_needs_asi(level: int) -> bool:
    return level in _DRUID_ASI_LEVELS

# ---------- Shared: ASI allocator ----------
def _allocate_asi_via_training(f: Dict[str, Any], points: int, *, hard_caps: Dict[str, int]) -> None:
    weights = (f.get("training") or {}).get("growth_weights") or {}
    default_weights = {"STR": 0.15, "DEX": 0.20, "CON": 0.20, "INT": 0.10, "WIS": 0.20, "CHA": 0.15}
    if not weights: weights = default_weights
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
    elif cls == "Druid":
        _apply_druid_init(f)
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
    elif cls == "Cleric":
        _apply_cleric_level_features(f, new_level)
        if _cleric_needs_asi(new_level):
            caps = {"STR": 20, "DEX": 20, "CON": 20, "INT": 20, "WIS": 20, "CHA": 20}
            _allocate_asi_via_training(f, points=2, hard_caps=caps)
            f["ac"] = calc_ac(f)
    elif cls == "Druid":
        _apply_druid_level_features(f, new_level)
        if _druid_needs_asi(new_level):
            caps = {"STR": 20, "DEX": 20, "CON": 20, "INT": 20, "WIS": 20, "CHA": 20}
            _allocate_asi_via_training(f, points=2, hard_caps=caps)
            f["ac"] = calc_ac(f)

def grant_starting_kit(f: Dict[str, Any]) -> None:
    """
    Adds class kit; sets up equipment model:
      - f['equipped']: main_hand_id, off_hand_id, armor_id, shield_id
      - Always injects the synthetic 'Unarmed' weapon.
      - For Druid: inventory also gets 'Wild Shape' weapon; inventory['forms'] list exists for your future animals.
      - Lizardkin: cannot equip body armor; shield still allowed.
    """
    cls = str(f.get("class", "Fighter")).capitalize()
    kit = CLASS_STARTING_KIT.get(cls, {"weapons": [], "armors": [], "shields": []})

    inv = f.setdefault("inventory", {})
    weapons: List[Dict[str, Any]] = inv.setdefault("weapons", [])
    armors: List[Dict[str, Any]] = inv.setdefault("armors", [])
    shields: List[Dict[str, Any]] = inv.setdefault("shields", [])
    forms: List[Dict[str, Any]] = inv.setdefault("forms", [])  # Wild Shape forms

    eq = f.setdefault("equipped", {})  # {"main_hand_id","off_hand_id","armor_id","shield_id"}

    def _assign_id(prefix: str, idx: int) -> str: return f"{prefix}_{idx}"

    # Inject class kit
    for w in kit.get("weapons", []):
        weapons.append({**w, "id": _assign_id("w", len(weapons))})
    for a in kit.get("armors", []):
        armors.append({**a, "id": _assign_id("a", len(armors))})
    for s in kit.get("shields", []):
        shields.append({**s, "id": _assign_id("s", len(shields))})

    # Universal Unarmed (front of list)
    if not any(w.get("unarmed") for w in weapons):
        weapons.insert(0, {**UNARMED_ITEM, "id": "unarmed"})

    # Druid: ensure 'forms' list exists (you'll populate later). Off-hand = chosen 'form'.
    if cls == "Druid":
        inv.setdefault("forms", forms)

    # Auto-equip defaults (class-appropriate)
    race = str(f.get("race", "")).lower()
    armor_allowed = (race != "lizardkin") and not bool(f.get("armor_prohibited", False))

    # Armor (prefer heaviest in kit for AC; you can change later in UI)
    if armor_allowed and armors:
        # simple: choose highest armor_bonus
        pick = max(armors, key=lambda a: int(a.get("armor_bonus", 0)))
        eq["armor_id"] = pick["id"]; f["armor_bonus"] = int(pick.get("armor_bonus", 0))
    else:
        eq["armor_id"] = None; f["armor_bonus"] = 0

    # Shield if available
    if shields:
        eq["shield_id"] = shields[0]["id"]
        f["shield_bonus"] = int(shields[0].get("shield_bonus", 0))
    else:
        eq["shield_id"] = None; f["shield_bonus"] = int(f.get("shield_bonus", 0))

    # Main hand default
    names = [w["name"] for w in weapons]
    main = weapons[0]
    # prefer iconic starter where present
    if cls == "Cleric" and "Mace" in names: main = weapons[names.index("Mace")]
    if cls == "Druid" and "Scimitar" in names: main = weapons[names.index("Scimitar")]
    eq["main_hand_id"] = main["id"]
    f["weapon"] = {k: v for k, v in main.items() if k != "id"}  # legacy field for engine

    # Off hand default -> Shield if any
    eq["off_hand_id"] = shields[0]["id"] if shields else None

    # AC refresh
    f["ac"] = calc_ac(f)
