# core/classes.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional

# ---------- Item helpers ----------
def weapon(name: str, dice: str, *, reach: int = 1, finesse: bool = False,
           ability: str = "STR", ranged: bool = False,
           range_tuple: Tuple[int, int] = (8, 16),
           versatile: bool = False, two_handed_dice: Optional[str] = None,
           two_handed: bool = False,
           unarmed_flag: bool = False, wildshape_flag: bool = False) -> Dict[str, Any]:
    d: Dict[str, Any] = {"type": "weapon", "name": name, "dice": dice, "reach": int(reach)}
    if finesse: d["finesse"] = True
    if ability and not finesse: d["ability"] = ability.upper()
    if ranged:
        d["ranged"] = True
        d["range"] = (int(range_tuple[0]), int(range_tuple[1]))
    if versatile:
        d["versatile"] = True
        if two_handed_dice: d["two_handed_dice"] = str(two_handed_dice)
    if two_handed:
        d["two_handed"] = True
    if unarmed_flag:
        d["unarmed"] = True
        d["versatile"] = True
        d["finesse"] = True
    if wildshape_flag:
        d["wildshape"] = True
    return d

def armor(name: str, armor_bonus: int) -> Dict[str, Any]:
    return {"type": "armor", "name": name, "armor_bonus": int(armor_bonus)}

def shield(name: str, shield_bonus: int = 2) -> Dict[str, Any]:
    return {"type": "shield", "name": name, "shield_bonus": int(shield_bonus)}

def wild_form(name: str, *, cr: float, stats: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"type": "wild_form", "name": name, "cr": float(cr), "stats": (stats or {})}

# ---------- Universal "Unarmed" option ----------
UNARMED_ITEM = weapon("Unarmed", "1d1", finesse=True, versatile=True, unarmed_flag=True)

# ---------- Class starting kits ----------
CLASS_STARTING_KIT: Dict[str, Dict[str, List[Dict[str, Any]]]]] = {
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
        "armors": [
            armor("Leather Armor", 1),
            armor("Scale Mail", 4),
            armor("Chain Mail", 3),  # your correction
        ],
        "shields": [shield("Shield", 2)],
    },
    "Druid": {
        "weapons": [
            weapon("Scimitar", "1d6", finesse=True),
            weapon("Wild Shape", "1d0", wildshape_flag=True),
        ],
        "armors": [armor("Leather Armor", 1)],
        "shields": [shield("Shield", 2)],
    },

    # Fighter styles as distinct class names
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
        "armors": [armor("Breastplate", 4)],
        "shields": [],
    },
    "Duelist": {
        "weapons": [
            weapon("Shortsword", "1d6", finesse=True),
            weapon("Shortsword", "1d6", finesse=True),
        ],
        "armors": [armor("Breastplate", 4)],
        "shields": [],
    },

    # Monk: no equipment
    "Monk": {
        "weapons": [],
        "armors": [],
        "shields": [],
    },

    # Rogue
    "Rogue": {
        "weapons": [
            weapon("Rapier", "1d8", finesse=True),
            weapon("Shortsword", "1d6", finesse=True),
            weapon("Dagger", "1d4", finesse=True),
            weapon("Dagger", "1d4", finesse=True),
        ],
        "armors": [armor("Leather Armor", 1)],
        "shields": [],
    },
}

FIGHTER_STYLE_CLASSES = {"Archer", "Defender", "Enforcer", "Duelist"}

# ---------- Proficiency Bonus ----------
def proficiency_for_level(level: int) -> int:
    L = max(1, int(level))
    return min(6, 2 + (L - 1) // 4)

# ---------- ASI schedules ----------
_BARB_ASI_LEVELS   = {4, 8, 12, 16, 19}
_BARD_ASI_LEVELS   = {4, 8, 12, 16, 19}
_CLERIC_ASI_LEVELS = {4, 8, 12, 16, 19}
_DRUID_ASI_LEVELS  = {4, 8, 12, 16, 19}
_FIGHTER_ASI_LEVELS= {4, 6, 8, 12, 14, 16, 19}
_MONK_ASI_LEVELS   = {4, 8, 12, 16, 19}
_ROGUE_ASI_LEVELS  = {4, 8, 10, 12, 16, 19}

# ---------- Spell tables (existing) ----------
# (Bard, Cleric, Druid tables preserved from previous patch; omitted here for brevity)
# You can keep your previously pasted tables unchanged.

# ---------- HP model (all classes): base-at-1 + per-level + current CON mod ----------
# Format: class key -> (base_hp, per_level_hp)
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
}

def _mod(x: int) -> int:
    return (int(x) - 10) // 2

def _recompute_hp_from_formula(f: Dict[str, Any]) -> None:
    cls = str(f.get("class", "Fighter")).capitalize()
    base, per = _HP_TABLE.get(cls, (8, 5))
    L = max(1, int(f.get("level", f.get("lvl", 1))))
    con = int(f.get("CON", f.get("con", 10)))
    con_mod = _mod(con)
    max_hp = base + (L - 1) * per + con_mod
    # Keep current HP unless it exceeds new max
    cur = int(f.get("hp", max_hp))
    f["max_hp"] = int(max_hp)
    f["hp"] = min(cur, int(max_hp))

# ---------- AC (imported utility) ----------
from core.ac import calc_ac

# ---------- Barbarian/Bard/Cleric/Druid/Fighter/Monk helpers ----------
# Keep the implementations you already have from earlier patches.
# Below we only add or adjust places that interact with HP recomputation
# and append the Rogue class.

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
    _recompute_hp_from_formula(f)
    f["ac"] = calc_ac(f)

def _apply_barbarian_level_features(f: Dict[str, Any], new_level: int) -> None:
    # other barbarian flags as you had before...
    if new_level >= 5:
        f["barb_extra_attacks"] = 1
        f["barb_speed_bonus_if_unarmored"] = 2
    if new_level >= 7:  f["barb_initiative_advantage"] = True
    if new_level >= 9:
        bonus = 1 + (1 if new_level >= 13 else 0) + (1 if new_level >= 17 else 0)
        f["barb_crit_extra_dice"] = bonus
    if new_level >= 15: f["barb_rage_capstone"] = True
    if new_level >= 20:
        for k in ("STR", "CON"):
            f[k] = min(int(f.get(k, 10)) + 4, 24); f[k.lower()] = f[k]
        f["barb_cap_24"] = True

def _apply_bard_init(f: Dict[str, Any]) -> None:
    f["spell_ability"] = "CHA"
    f["cantrips_known"] = 0; f["spells_known"] = 0
    f["known_cantrips"] = []; f["known_spells"] = []
    f["spell_slots_total"] = [0]*10; f["spell_slots_current"] = [0]*10
    f["bard_inspiration_uses_per_battle"] = 1
    f["bard_inspiration_unlimited"] = False
    f["bard_aura_charm_fear"] = False
    _recompute_hp_from_formula(f)
    f["ac"] = calc_ac(f)
    # apply casting table with your existing function

def _apply_bard_level_features(f: Dict[str, Any], new_level: int) -> None:
    if new_level >= 6: f["bard_aura_charm_fear"] = True
    if new_level >= 20:
        f["bard_inspiration_unlimited"] = True
        f["bard_inspiration_uses_per_battle"] = 999_999

def _apply_cleric_init(f: Dict[str, Any]) -> None:
    f["spell_ability"] = "WIS"
    f["cantrips_known"] = 0; f["spells_known"] = 0
    f["known_cantrips"] = []; f["known_spells"] = []
    f["spell_slots_total"] = [0]*10; f["spell_slots_current"] = [0]*10
    _recompute_hp_from_formula(f)
    f["ac"] = calc_ac(f)
    # apply casting table with your existing function

def _apply_cleric_level_features(f: Dict[str, Any], new_level: int) -> None:
    pass  # table update only (keep your existing slot/known updates)

def _apply_druid_init(f: Dict[str, Any]) -> None:
    f["spell_ability"] = "WIS"
    f["cantrips_known"] = 0; f["spells_known"] = 0
    f["known_cantrips"] = []; f["known_spells"] = []
    f["spell_slots_total"] = [0]*10; f["spell_slots_current"] = [0]*10
    f["spell_slots_unlimited"] = False
    f["wildshape_allowed_cr"] = []
    f["wildshape_cast_while_shaped"] = False
    _recompute_hp_from_formula(f)
    f["ac"] = calc_ac(f)
    # apply casting table/CR list with your existing function

def _apply_druid_level_features(f: Dict[str, Any], new_level: int) -> None:
    pass  # handled by your existing table function

def _apply_fighter_init(f: Dict[str, Any]) -> None:
    f["fighter_extra_attacks"] = 0
    f["fighter_defense_ac_bonus"] = 0
    f["fighter_archery_bonus"] = 0
    f["fighter_enforcer_twohand_adv"] = False
    f["fighter_duelist_offhand_prof"] = False
    style = str(f.get("class", "Archer")).capitalize()
    if style == "Archer":
        f["fighter_archery_bonus"] = 2
    elif style == "Defender":
        f["fighter_defense_ac_bonus"] = 1
    elif style == "Enforcer":
        f["fighter_enforcer_twohand_adv"] = True
    elif style == "Duelist":
        f["fighter_duelist_offhand_prof"] = True
    _recompute_hp_from_formula(f)
    f["ac"] = calc_ac(f)

def _apply_fighter_level_features(f: Dict[str, Any], new_level: int) -> None:
    f["fighter_extra_attacks"] = 0
    if new_level >= 5:  f["fighter_extra_attacks"] = 1
    if new_level >= 11: f["fighter_extra_attacks"] = 2
    if new_level >= 20: f["fighter_extra_attacks"] = 3

# --- Monk init/level helpers (from previous drop, but HP now uses formula via _recompute_hp_from_formula) ---
def _apply_monk_init(f: Dict[str, Any]) -> None:
    # keep all previous monk flags and unarmed die logic
    # ...
    _recompute_hp_from_formula(f)
    f["ac"] = calc_ac(f)

def _apply_monk_level_features(f: Dict[str, Any], new_level: int) -> None:
    # keep previous monk feature flips (extra swings, evasion, etc)
    # ...
    pass

# ---------- Rogue ----------
def _apply_rogue_init(f: Dict[str, Any]) -> None:
    # core flags
    f["rogue_free_action"] = f.get("rogue_free_action", "auto")  # "auto" | "hide" | "dash" | "disengage"
    f["rogue_weapon_half"] = False            # L5
    f["rogue_evasion"] = False               # L7
    f["rogue_wis_saves_adv"] = False         # L15
    f["rogue_no_adv_on_me"] = False          # L18
    f["rogue_always_hit"] = False            # L20
    _recompute_hp_from_formula(f)
    f["ac"] = calc_ac(f)

def _apply_rogue_level_features(f: Dict[str, Any], new_level: int) -> None:
    f["rogue_weapon_half"] = (new_level >= 5)
    f["rogue_evasion"] = (new_level >= 7)
    f["rogue_wis_saves_adv"] = (new_level >= 15)
    f["rogue_no_adv_on_me"] = (new_level >= 18)
    f["rogue_always_hit"] = (new_level >= 20)

# ---------- ASI helpers ----------
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
    elif cls in FIGHTER_STYLE_CLASSES:
        _apply_fighter_init(f)
    elif cls == "Monk":
        _apply_monk_init(f)
    elif cls == "Rogue":
        _apply_rogue_init(f)
    # guarantee HP/AC derived
    _recompute_hp_from_formula(f)
    f["ac"] = calc_ac(f)

def apply_class_level_up(f: Dict[str, Any], new_level: int) -> None:
    cls = str(f.get("class", "Fighter")).capitalize()
    if cls == "Barbarian":
        _apply_barbarian_level_features(f, new_level)
        if new_level in _BARB_ASI_LEVELS:
            cap_24 = bool(f.get("barb_cap_24", False))
            caps = {"STR": (24 if cap_24 else 20), "CON": (24 if cap_24 else 20), "DEX":20,"INT":20,"WIS":20,"CHA":20}
            _allocate_asi_via_training(f, 2, hard_caps=caps)
    elif cls == "Bard":
        _apply_bard_level_features(f, new_level)
        if new_level in _BARD_ASI_LEVELS:
            _allocate_asi_via_training(f, 2, hard_caps={"STR":20,"DEX":20,"CON":20,"INT":20,"WIS":20,"CHA":20})
    elif cls == "Cleric":
        _apply_cleric_level_features(f, new_level)
        if new_level in _CLERIC_ASI_LEVELS:
            _allocate_asi_via_training(f, 2, hard_caps={"STR":20,"DEX":20,"CON":20,"INT":20,"WIS":20,"CHA":20})
    elif cls == "Druid":
        _apply_druid_level_features(f, new_level)
        if new_level in _DRUID_ASI_LEVELS:
            _allocate_asi_via_training(f, 2, hard_caps={"STR":20,"DEX":20,"CON":20,"INT":20,"WIS":20,"CHA":20})
    elif cls in FIGHTER_STYLE_CLASSES:
        _apply_fighter_level_features(f, new_level)
        if new_level in _FIGHTER_ASI_LEVELS:
            _allocate_asi_via_training(f, 2, hard_caps={"STR":20,"DEX":20,"CON":20,"INT":20,"WIS":20,"CHA":20})
    elif cls == "Monk":
        _apply_monk_level_features(f, new_level)
        if new_level in _MONK_ASI_LEVELS:
            _allocate_asi_via_training(f, 2, hard_caps={"STR":20,"DEX":20,"CON":20,"INT":20,"WIS":20,"CHA":20})
    elif cls == "Rogue":
        _apply_rogue_level_features(f, new_level)
        if new_level in _ROGUE_ASI_LEVELS:
            _allocate_asi_via_training(f, 2, hard_caps={"STR":20,"DEX":20,"CON":20,"INT":20,"WIS":20,"CHA":20})

    # recompute derived after level/ASI changes
    f["level"] = int(new_level)
    _recompute_hp_from_formula(f)
    f["ac"] = calc_ac(f)

def grant_starting_kit(f: Dict[str, Any]) -> None:
    """
    Adds class kit; sets up equipment model:
      - f['equipped']: main_hand_id, off_hand_id, armor_id, shield_id
      - Always injects 'Unarmed'.
      - Druid: inventory['forms'] exists (for Wild Shape).
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

    def _assign_id(prefix: str, idx: int) -> str: return f"{prefix}_{idx}"

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
        eq["armor_id"] = pick["id"]; f["armor_bonus"] = int(pick.get("armor_bonus", 0))
    else:
        eq["armor_id"] = None; f["armor_bonus"] = 0

    if shields:
        eq["shield_id"] = shields[0]["id"]; f["shield_bonus"] = int(shields[0].get("shield_bonus", 0))
    else:
        eq["shield_id"] = None; f["shield_bonus"] = int(f.get("shield_bonus", 0))

    # Defaults per class
    names = [w["name"] for w in weapons]
    main = weapons[0]
    if cls == "Cleric" and "Mace" in names: main = weapons[names.index("Mace")]
    if cls == "Druid" and "Scimitar" in names: main = weapons[names.index("Scimitar")]
    if cls == "Archer" and "Longbow" in names: main = weapons[names.index("Longbow")]
    if cls == "Defender" and "Longsword" in names: main = weapons[names.index("Longsword")]
    if cls == "Enforcer" and "Halberd" in names: main = weapons[names.index("Halberd")]
    if cls == "Duelist" and "Shortsword" in names: main = weapons[names.index("Shortsword")]
    if cls == "Monk":
        main = weapons[0]  # Unarmed
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
        # prefer a Dagger off-hand if available
        daggers = [w for w in weapons if w["name"] == "Dagger"]
        eq["off_hand_id"] = daggers[0]["id"] if daggers else None
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
