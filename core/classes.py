# core/classes.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional

from core.ac import calc_ac

# ---------- Aliases for backwards-compat (load/migration) ----------
_CLASS_ALIASES = {
    "Barbarian": "Berserker",
    "Bard": "Skald",
    "Cleric": "War Priest",
    "Ranger": "Stalker",
    "Paladin": "Crusader",
}

def _norm_class(name: str) -> str:
    nm = str(name or "").strip()
    cap = nm[:1].upper() + nm[1:]
    return _CLASS_ALIASES.get(cap, cap)

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
CLASS_STARTING_KIT: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "Berserker": {
        "weapons": [
            weapon("Greataxe", "1d12", ability="STR", two_handed=True),
            weapon("Hand Axe", "1d6", ability="STR"),
            weapon("Hand Axe", "1d6", ability="STR"),
        ],
        "armors": [],
        "shields": [],
    },
    "Skald": {
        "weapons": [
            weapon("Rapier", "1d8", finesse=True),
            weapon("Longsword", "1d8", ability="STR", versatile=True, two_handed_dice="1d10"),
            weapon("Dagger", "1d4", finesse=True),
        ],
        "armors": [armor("Leather Armor", 1)],
        "shields": [],
    },
    "War Priest": {
        "weapons": [
            weapon("Mace", "1d6", ability="STR"),
            weapon("Warhammer", "1d8", ability="STR", versatile=True, two_handed_dice="1d10"),
        ],
        "armors": [
            armor("Leather Armor", 1),
            armor("Scale Mail", 4),
            armor("Chain Mail", 3),
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
    # Fighter styles as distinct "classes"
    "Archer": {
        "weapons": [weapon("Longbow", "1d8", ability="DEX", ranged=True, range_tuple=(2, 4), two_handed=True)],
        "armors": [armor("Chain Mail", 3)],
        "shields": [],
    },
    "Defender": {
        "weapons": [weapon("Longsword", "1d8", ability="STR", versatile=True, two_handed_dice="1d10")],
        "armors": [armor("Plate", 5)],
        "shields": [shield("Shield", 2)],
    },
    "Enforcer": {
        "weapons": [weapon("Halberd", "1d12", ability="STR", reach=2, two_handed=True)],
        "armors": [armor("Scale Mail", 4)],
        "shields": [],
    },
    "Duelist": {
        "weapons": [weapon("Shortsword", "1d6", finesse=True), weapon("Shortsword", "1d6", finesse=True)],
        "armors": [armor("Scale Mail", 4)],
        "shields": [],
    },
    "Monk": {"weapons": [], "armors": [], "shields": []},

    "Stalker": {
        "weapons": [
            weapon("Longbow", "1d8", ability="DEX", ranged=True, range_tuple=(2, 4), two_handed=True),
            weapon("Shortsword", "1d6", finesse=True),
            weapon("Shortsword", "1d6", finesse=True),
        ],
        "armors": [armor("Scale Mail", 4), armor("Leather Armor", 1)],
        "shields": [],
    },

    "Wizard": {
        "weapons": [
            weapon("Dagger", "1d4", finesse=True),
            weapon("Quarterstaff", "1d6", versatile=True, two_handed_dice="1d8"),
        ],
        "armors": [armor("Leather Armor", 1)],
        "shields": [],
    },

    "Crusader": {
        "weapons": [weapon("Warhammer", "1d8", ability="STR", versatile=True, two_handed_dice="1d10")],
        "armors": [armor("Chain Mail", 3)],
        "shields": [shield("Shield", 2)],
    },
}

FIGHTER_STYLE_CLASSES = {"Archer", "Defender", "Enforcer", "Duelist"}

# ---------- Proficiency Bonus ----------
def proficiency_for_level(level: int) -> int:
    L = max(1, int(level))
    return min(6, 2 + (L - 1) // 4)

# ---------- ASI schedules ----------
_BERSERKER_ASI   = {4, 8, 12, 16, 19}
_SKALD_ASI       = {4, 8, 12, 16, 19}
_WARPRIEST_ASI   = {4, 8, 12, 16, 19}
_DRUID_ASI       = {4, 8, 12, 16, 19}
_FIGHTER_ASI     = {4, 6, 8, 12, 14, 16, 19}
_MONK_ASI        = {4, 8, 12, 16, 19}
_STALKER_ASI     = {4, 8, 12, 16, 19}
_WIZARD_ASI      = {4, 8, 12, 16, 19}
_CRUSADER_ASI    = {4, 8, 12, 16, 19}

# ---------- HP retrocompute for all classes ----------
def _mod(x: int) -> int:
    return (int(x) - 10) // 2

_HP_TABLE: Dict[str, Tuple[int, int]] = {
    "Berserker": (12, 7),
    "Skald":     (8, 5),
    "War Priest":(8, 5),
    "Druid":     (8, 5),
    "Archer":    (10, 6),
    "Defender":  (10, 6),
    "Enforcer":  (10, 6),
    "Duelist":   (10, 6),
    "Monk":      (8, 5),
    "Stalker":   (10, 6),
    "Wizard":    (6, 4),
    "Crusader":  (10, 6),
}

def _recompute_hp_from_formula(f: Dict[str, Any]) -> None:
    cls = _norm_class(f.get("class", ""))
    base, per = _HP_TABLE.get(cls, (8, 5))
    con_mod = _mod(int(f.get("CON", f.get("con", 10))))
    lvl = int(f.get("level", f.get("lvl", 1)))
    f["max_hp"] = int(base + max(0, lvl - 1) * per + con_mod)
    f["hp"] = min(int(f.get("hp", f["max_hp"])), f["max_hp"])

# ---------- SKALD (Bard) ----------
def _apply_skald_init(f: Dict[str, Any]) -> None:
    f["spell_ability"] = "CHA"
    f["cantrips_known"] = 0; f["spells_known"] = 0
    f["known_cantrips"] = []; f["known_spells"] = []
    f["spell_slots_total"] = [0]*10; f["spell_slots_current"] = [0]*10
    f["skald_aura_charm_fear"] = False
    f["ac"] = calc_ac(f)
    _apply_skald_casting_for_level(f, int(f.get("level", 1)))

def _apply_skald_casting_for_level(f: Dict[str, Any], L: int) -> None:
    _TABLE = {
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
    cantrips, spells, slots = _TABLE.get(max(1, min(20, L)), (0, 0, [0]*9))
    f["cantrips_known"] = cantrips; f["spells_known"] = spells
    pad = [0] + slots
    f["spell_slots_total"] = pad[:]
    if not f.get("spell_slots_current"): f["spell_slots_current"] = pad[:]

def _apply_skald_level(f: Dict[str, Any], L: int) -> None:
    _apply_skald_casting_for_level(f, L)
    if L >= 6: f["skald_aura_charm_fear"] = True

def _skald_needs_asi(L: int) -> bool:
    return L in _SKALD_ASI

# ---------- WAR PRIEST (Cleric) ----------
def _apply_warpriest_init(f: Dict[str, Any]) -> None:
    f["spell_ability"] = "INT"  # WIS -> INT (global change)
    f["cantrips_known"] = 0; f["spells_known"] = 0
    f["known_cantrips"] = []; f["known_spells"] = []
    f["spell_slots_total"] = [0]*10; f["spell_slots_current"] = [0]*10
    f["ac"] = calc_ac(f)
    _apply_warpriest_casting_for_level(f, int(f.get("level", 1)))

def _apply_warpriest_casting_for_level(f: Dict[str, Any], L: int) -> None:
    _TABLE = {
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
    cantrips, slots = _TABLE.get(max(1, min(20, L)), (0, [0]*9))
    f["cantrips_known"] = cantrips
    pad = [0] + slots
    f["spell_slots_total"] = pad[:]
    if not f.get("spell_slots_current"): f["spell_slots_current"] = pad[:]

def _apply_warpriest_level(f: Dict[str, Any], L: int) -> None:
    _apply_warpriest_casting_for_level(f, L)

def _warpriest_needs_asi(L: int) -> bool:
    return L in _WARPRIEST_ASI

# ---------- DRUID ----------
def _druid_allowed_cr(L: int) -> List[float]:
    out: List[float] = []
    if L >= 2: out.append(0.25)
    if L >= 4: out.append(0.5)
    if L >= 8: out.append(1.0)
    return out

def _apply_druid_init(f: Dict[str, Any]) -> None:
    f["spell_ability"] = "INT"  # WIS -> INT (global change)
    f["cantrips_known"] = 0; f["spells_known"] = 0
    f["known_cantrips"] = []; f["known_spells"] = []
    f["spell_slots_total"] = [0]*10; f["spell_slots_current"] = [0]*10
    f["spell_slots_unlimited"] = False
    f["wildshape_allowed_cr"] = _druid_allowed_cr(int(f.get("level", 1)))
    f["wildshape_cast_while_shaped"] = False
    f["ac"] = calc_ac(f)
    _apply_druid_casting_for_level(f, int(f.get("level", 1)))

def _apply_druid_casting_for_level(f: Dict[str, Any], L: int) -> None:
    _TABLE = {
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
    cantrips, slots = _TABLE.get(max(1, min(20, L)), (0, [0]*9))
    f["cantrips_known"] = cantrips
    pad = [0] + slots
    f["spell_slots_total"] = pad[:]
    if not f.get("spell_slots_current"): f["spell_slots_current"] = pad[:]
    f["wildshape_allowed_cr"] = _druid_allowed_cr(L)
    f["wildshape_cast_while_shaped"] = (L >= 18)
    f["spell_slots_unlimited"] = (L >= 20)

def _apply_druid_level(f: Dict[str, Any], L: int) -> None:
    _apply_druid_casting_for_level(f, L)

def _druid_needs_asi(L: int) -> bool:
    return L in _DRUID_ASI

# ---------- FIGHTER styles ----------
def _apply_fighter_init(f: Dict[str, Any]) -> None:
    f["fighter_extra_attacks"] = 0
    f["fighter_defense_ac_bonus"] = 0
    f["fighter_archery_bonus"] = 0
    f["fighter_enforcer_twohand_adv"] = False
    f["fighter_duelist_offhand_prof"] = False

    style = _norm_class(f.get("class", ""))
    if style == "Archer":
        f["fighter_archery_bonus"] = 2
    elif style == "Defender":
        f["fighter_defense_ac_bonus"] = 1
    elif style == "Enforcer":
        f["fighter_enforcer_twohand_adv"] = True
    elif style == "Duelist":
        f["fighter_duelist_offhand_prof"] = True

    f["ac"] = calc_ac(f)

def _apply_fighter_level(f: Dict[str, Any], L: int) -> None:
    f["fighter_extra_attacks"] = 0
    if L >= 5:  f["fighter_extra_attacks"] = 1
    if L >= 11: f["fighter_extra_attacks"] = 2
    if L >= 20: f["fighter_extra_attacks"] = 3

def _fighter_needs_asi(L: int) -> bool:
    return L in _FIGHTER_ASI

# ---------- MONK ----------
def _parse_die(d: str) -> int:
    try: return int(str(d).split("d", 1)[1])
    except Exception: return 4

def _fmt_die(sides: int) -> str:
    return f"1d{int(sides)}"

def _monk_die_sides_for_level(L: int) -> int:
    if L >= 17: return 10
    if L >= 11: return 8
    if L >= 5:  return 6
    return 4

def _update_monk_unarmed_die(f: Dict[str, Any]) -> None:
    L = int(f.get("level", 1))
    monk_sides = _monk_die_sides_for_level(L)
    race_die = str(f.get("_race_unarmed_dice", f.get("unarmed_dice", "1d1")))
    race_sides = _parse_die(race_die) if "d" in str(race_die) else 1
    chosen = max(monk_sides, race_sides)
    f["unarmed_dice"] = _fmt_die(chosen)

def _apply_monk_init(f: Dict[str, Any]) -> None:
    if "unarmed_dice" in f and not f.get("_race_unarmed_dice"):
        f["_race_unarmed_dice"] = f["unarmed_dice"]
    f["monk_unarmored_ac"] = True
    f["monk_extra_attacks"] = 0
    f["monk_offhand_prof_even_with_weapon"] = False
    f["monk_evasion"] = False
    f["monk_global_saves_adv"] = False
    f["poison_immune"] = False
    f.setdefault("_base_speed", int(f.get("speed", 4)))
    f["monk_speed_bonus"] = 0
    _update_monk_unarmed_die(f)
    f["ac"] = calc_ac(f)

def _apply_monk_level(f: Dict[str, Any], L: int) -> None:
    f["monk_extra_attacks"] = (1 if L >= 5 else 0) + (1 if L >= 20 else 0)
    f["monk_offhand_prof_even_with_weapon"] = (L >= 15)
    f["monk_evasion"] = (L >= 7)
    f["poison_immune"] = (L >= 10)
    f["monk_global_saves_adv"] = (L >= 14)
    _update_monk_unarmed_die(f)

def _monk_needs_asi(L: int) -> bool:
    return L in _MONK_ASI

# ---------- WIZARD ----------
_WIZ_CANTRIPS = {1:3,2:3,3:3,4:4,5:4,6:4,7:4,8:4,9:4,10:5,11:5,12:5,13:5,14:5,15:5,16:5,17:5,18:5,19:5,20:5}
_WIZ_SLOTS = {
    1:[2,0,0,0,0,0,0,0,0], 2:[3,0,0,0,0,0,0,0,0], 3:[4,2,0,0,0,0,0,0,0], 4:[4,3,0,0,0,0,0,0,0],
    5:[4,3,2,0,0,0,0,0,0], 6:[4,3,3,0,0,0,0,0,0], 7:[4,3,3,1,0,0,0,0,0], 8:[4,3,3,2,0,0,0,0,0],
    9:[4,3,3,3,1,0,0,0,0],10:[4,3,3,3,2,0,0,0,0],11:[4,3,3,3,2,1,0,0,0],12:[4,3,3,3,2,1,0,0,0],
    13:[4,3,3,3,2,1,1,0,0],14:[4,3,3,3,2,1,1,0,0],15:[4,3,3,3,2,1,1,1,0],16:[4,3,3,3,2,1,1,1,0],
    17:[4,3,3,3,2,1,1,1,1],18:[4,3,3,3,3,1,1,1,1],19:[4,3,3,3,3,2,1,1,1],20:[4,3,3,3,3,2,2,1,1],
}
def _wiz_cantrips_known(L: int) -> int: return _WIZ_CANTRIPS[max(1, min(20, L))]
def _wiz_slots_for_level(L: int) -> List[int]: return _WIZ_SLOTS[max(1, min(20, L))][:]

def _cantrip_tier(L: int) -> int:
    if L >= 17: return 4
    if L >= 11: return 3
    if L >= 5:  return 2
    return 1

def _apply_wizard_init(f: Dict[str, Any]) -> None:
    L = int(f.get("level", 1))
    f["spell_ability"] = "INT"
    f["cantrips_known"] = _wiz_cantrips_known(L)
    f["known_cantrips"] = f.get("known_cantrips", [])
    f["known_spells"] = f.get("known_spells", [])
    pad = [0] + _wiz_slots_for_level(L)
    f["spell_slots_total"] = pad[:]
    if not f.get("spell_slots_current"): f["spell_slots_current"] = pad[:]
    int_mod = _mod(int(f.get("INT", f.get("int", 10))))
    prof = proficiency_for_level(L)
    f["spell_attack_bonus"] = prof + int_mod
    f["spell_save_dc"] = 8 + prof + int_mod
    f["wiz_cantrip_tier"] = _cantrip_tier(L)
    f["wiz_adv_vs_blind_deaf"] = (L >= 7)
    f["wiz_aoe_ally_exempt"] = 3 if L >= 17 else (2 if L >= 10 else (1 if L >= 3 else 0))
    f["ac"] = calc_ac(f)

def _apply_wizard_level(f: Dict[str, Any], L: int) -> None:
    _apply_wizard_init(f)

def _wizard_needs_asi(L: int) -> bool:
    return L in _WIZARD_ASI

# ---------- CRUSADER (Paladin) ----------
def _cru_smite_nd6(L: int) -> int:
    if L >= 17: return 5
    if L >= 13: return 4
    if L >= 9:  return 4
    if L >= 5:  return 3
    if L >= 2:  return 2
    return 0

def _cru_smite_chance(L: int) -> float:
    if L >= 11: return 0.50
    if L >= 2:  return 0.10
    return 0.0

def _apply_crusader_init(f: Dict[str, Any]) -> None:
    L = int(f.get("level", 1))
    total = 5 * L
    f.setdefault("cru_lay_on_hands_total", total)
    f.setdefault("cru_lay_on_hands_current", total)

    f["cru_twohand_damage_adv"] = (L >= 2)   # two-handed (or versatile used 2H): roll damage twice, take higher
    f["poison_immune"] = (L >= 3)
    f["cru_extra_attacks"] = 1 if L >= 5 else 0

    # Auras
    cha_mod = _mod(int(f.get("CHA", f.get("cha", 10))))
    f["cru_aura_radius"] = 6 if L >= 18 else 2
    f["cru_aura_int_bonus"] = cha_mod if L >= 6 else 0  # +CHA to INT saves
    f["cru_aura_no_fear"] = bool(L >= 10)

    # Smite-like proc
    f["cru_smite_chance"] = _cru_smite_chance(L)
    f["cru_smite_nd6"] = _cru_smite_nd6(L)

    f["ac"] = calc_ac(f)  # includes +1 AC at L2 via calc_ac

def _apply_crusader_level(f: Dict[str, Any], L: int) -> None:
    _apply_crusader_init(f)

def _crusader_needs_asi(L: int) -> bool:
    return L in _CRUSADER_ASI

# ---------- Shared: ASI allocator ----------
def _allocate_asi_via_training(f: Dict[str, Any], points: int, *, hard_caps: Dict[str, int]) -> None:
    weights = (f.get("training") or {}).get("growth_weights") or {}
    # Drop WIS, fold its weight into INT by default
    default_weights = {"STR": 0.20, "DEX": 0.20, "CON": 0.20, "INT": 0.25, "CHA": 0.15}
    if not weights: weights = default_weights
    # On-the-fly migrate legacy "WIS" weight to INT
    if "WIS" in weights:
        weights["INT"] = weights.get("INT", 0.0) + weights.pop("WIS", 0.0)
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
    cls = _norm_class(f.get("class", ""))
    f["class"] = cls  # normalize
    if cls == "Berserker":
        # flags used by AC calc (barbarian unarmored, etc.) if you support them
        f["barb_unarmored_ac"] = True
        f["ac"] = calc_ac(f)
    elif cls == "Skald":
        _apply_skald_init(f)
    elif cls == "War Priest":
        _apply_warpriest_init(f)
    elif cls == "Druid":
        _apply_druid_init(f)
    elif cls in FIGHTER_STYLE_CLASSES:
        _apply_fighter_init(f)
    elif cls == "Monk":
        _apply_monk_init(f)
    elif cls == "Wizard":
        _apply_wizard_init(f)
    elif cls == "Stalker":
        # Stalker perks mostly live in combat/AC; AC gives +1 at L2
        f["ac"] = calc_ac(f)
    elif cls == "Crusader":
        _apply_crusader_init(f)

    _recompute_hp_from_formula(f)
    f["ac"] = calc_ac(f)

def apply_class_level_up(f: Dict[str, Any], new_level: int) -> None:
    cls = _norm_class(f.get("class", ""))
    if cls == "Berserker":
        if new_level in _BERSERKER_ASI:
            caps = {"STR":20, "DEX":20, "CON":20, "INT":20, "CHA":20}
            _allocate_asi_via_training(f, points=2, hard_caps=caps)
    elif cls == "Skald":
        _apply_skald_level(f, new_level)
        if _skald_needs_asi(new_level):
            caps = {"STR":20, "DEX":20, "CON":20, "INT":20, "CHA":20}
            _allocate_asi_via_training(f, points=2, hard_caps=caps)
    elif cls == "War Priest":
        _apply_warpriest_level(f, new_level)
        if _warpriest_needs_asi(new_level):
            caps = {"STR":20, "DEX":20, "CON":20, "INT":20, "CHA":20}
            _allocate_asi_via_training(f, points=2, hard_caps=caps)
    elif cls == "Druid":
        _apply_druid_level(f, new_level)
        if _druid_needs_asi(new_level):
            caps = {"STR":20, "DEX":20, "CON":20, "INT":20, "CHA":20}
            _allocate_asi_via_training(f, points=2, hard_caps=caps)
    elif cls in FIGHTER_STYLE_CLASSES:
        _apply_fighter_level(f, new_level)
        if _fighter_needs_asi(new_level):
            caps = {"STR":20, "DEX":20, "CON":20, "INT":20, "CHA":20}
            _allocate_asi_via_training(f, points=2, hard_caps=caps)
    elif cls == "Monk":
        _apply_monk_level(f, new_level)
        if _monk_needs_asi(new_level):
            caps = {"STR":20, "DEX":20, "CON":20, "INT":20, "CHA":20}
            _allocate_asi_via_training(f, points=2, hard_caps=caps)
    elif cls == "Wizard":
        _apply_wizard_level(f, new_level)
        if _wizard_needs_asi(new_level):
            caps = {"STR":20, "DEX":20, "CON":20, "INT":20, "CHA":20}
            _allocate_asi_via_training(f, points=2, hard_caps=caps)
    elif cls == "Stalker":
        if new_level in _STALKER_ASI:
            caps = {"STR":20, "DEX":20, "CON":20, "INT":20, "CHA":20}
            _allocate_asi_via_training(f, points=2, hard_caps=caps)
    elif cls == "Crusader":
        _apply_crusader_level(f, new_level)
        if _crusader_needs_asi(new_level):
            caps = {"STR":20, "DEX":20, "CON":20, "INT":20, "CHA":20}
            _allocate_asi_via_training(f, points=2, hard_caps=caps)

    _recompute_hp_from_formula(f)
    f["ac"] = calc_ac(f)

def grant_starting_kit(f: Dict[str, Any]) -> None:
    """
    Adds class kit; sets up equipment model:
      - f['equipped']: main_hand_id, off_hand_id, armor_id, shield_id
      - Always injects the synthetic 'Unarmed' weapon.
      - Lizardkin: cannot equip body armor; shield still allowed. (Consider race_tags in future.)
      - Two-handed main-hand clears off-hand and shield.
    """
    cls = _norm_class(f.get("class", ""))
    kit = CLASS_STARTING_KIT.get(cls, {"weapons": [], "armors": [], "shields": []})

    inv = f.setdefault("inventory", {})
    weapons: List[Dict[str, Any]] = inv.setdefault("weapons", [])
    armors: List[Dict[str, Any]] = inv.setdefault("armors", [])
    shields: List[Dict[str, Any]] = inv.setdefault("shields", [])
    forms: List[Dict[str, Any]] = inv.setdefault("forms", [])  # for Druids

    eq = f.setdefault("equipped", {})

    def _assign_id(prefix: str, idx: int) -> str: return f"{prefix}_{idx}"

    for w in kit.get("weapons", []): weapons.append({**w, "id": _assign_id("w", len(weapons))})
    for a in kit.get("armors", []):  armors.append({**a, "id": _assign_id("a", len(armors))})
    for s in kit.get("shields", []): shields.append({**s, "id": _assign_id("s", len(shields))})

    # Universal Unarmed
    if not any(w.get("unarmed") for w in weapons):
        weapons.insert(0, {**UNARMED_ITEM, "id": "unarmed"})

    # Armor allowance (name-based for now; consider race_tags later)
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

    # Main-hand defaults
    names = [w["name"] for w in weapons]
    main = weapons[0]
    if cls == "War Priest" and "Mace" in names: main = weapons[names.index("Mace")]
    if cls == "Druid" and "Scimitar" in names: main = weapons[names.index("Scimitar")]
    if cls == "Archer" and "Longbow" in names: main = weapons[names.index("Longbow")]
    if cls == "Defender" and "Longsword" in names: main = weapons[names.index("Longsword")]
    if cls == "Enforcer" and "Halberd" in names: main = weapons[names.index("Halberd")]
    if cls == "Duelist" and "Shortsword" in names: main = weapons[names.index("Shortsword")]
    if cls == "Wizard" and "Quarterstaff" in names: main = weapons[names.index("Quarterstaff")]
    if cls == "Monk": main = weapons[0]
    if cls == "Stalker" and "Longbow" in names: main = weapons[names.index("Longbow")]
    if cls == "Crusader" and "Warhammer" in names: main = weapons[names.index("Warhammer")]

    eq["main_hand_id"] = main["id"]
    f["weapon"] = {k: v for k, v in main.items() if k != "id"}

    # Off-hand defaults
    if cls == "Duelist":
        others = [w for w in weapons if w["name"] == "Shortsword" and w["id"] != main["id"]]
        eq["off_hand_id"] = others[0]["id"] if others else None
    elif cls == "Defender" and shields:
        eq["off_hand_id"] = shields[0]["id"]
    elif cls == "Stalker":
        ss = [w for w in weapons if w["name"] == "Shortsword" and w["id"] != main["id"]]
        eq["off_hand_id"] = ss[0]["id"] if ss else None
    elif cls == "Crusader" and shields:
        eq["off_hand_id"] = shields[0]["id"]
    else:
        eq["off_hand_id"] = None

    # Two-handed enforcement
    if bool(main.get("two_handed", False)):
        eq["off_hand_id"] = None
        eq["shield_id"] = None
        f["shield_bonus"] = 0

    if cls == "Druid":
        inv.setdefault("forms", forms)

    _recompute_hp_from_formula(f)
    f["ac"] = calc_ac(f)
