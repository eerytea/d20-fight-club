# core/ratings.py
from __future__ import annotations
from typing import Dict, Any, Tuple, List
from core.spells_meta import count_spell_tags, base_cantrip_die_and_tier

# ---------- tuning constants ----------
# Baseline AC used when computing offense score (the "sparring dummy" benchmark).
OFFENSE_BASELINE_AC: int = 12
# Normalization cap for spell-count features (e.g., 5 spells in a category is treated as 1.0)
ROLE_SPELL_COUNT_CAP: int = 5

# ---------- helpers ----------
def clamp01(x: float) -> float: return max(0.0, min(1.0, x))
def mod(stat: int) -> int: return (stat - 10) // 2
def die_avg_from_str(d: str) -> float:
    try:
        n, s = str(d).lower().split("d")
        n, s = max(1, int(n)), max(1, int(s))
        return n * (1 + s) / 2.0
    except Exception:
        return (1 + 6) / 2.0
def die_avg(sides: int) -> float: return (1 + int(sides)) / 2.0

def proficiency(level: int) -> int:
    if level <= 4:  return 2
    if level <= 8:  return 3
    if level <= 12: return 4
    if level <= 16: return 5
    return 6

# ---------- class aliases (legacy -> new) ----------
CLASS_ALIASES: Dict[str, str] = {
    "barbarian": "berserker",
    "ranger": "stalker",
    "paladin": "crusader",
    "bard": "skald",
    "cleric": "war_priest",
    "warlock": "wizard",
    "sorcerer": "wizard",
}

def _normalize_class_key(cls: str) -> str:
    c = (cls or "fighter").strip().lower()
    return CLASS_ALIASES.get(c, c)

# ---------- class profiles ----------
CLASS_PROFILES: Dict[str, Dict[str, Any]] = {
    # Fighter styles use "fighter" profile
    "fighter":    {"mix": (0.45, 0.40, 0.15), "hit_die": 10, "atk_stats": ("str","dex")},
    "berserker":  {"mix": (0.55, 0.35, 0.10), "hit_die": 12, "atk_stats": ("str",)},
    "stalker":    {"mix": (0.45, 0.25, 0.30), "hit_die": 10, "atk_stats": ("dex","str")},
    "rogue":      {"mix": (0.50, 0.20, 0.30), "hit_die": 8,  "atk_stats": ("dex",)},
    "wizard":     {"mix": (0.55, 0.20, 0.25), "hit_die": 6,  "atk_stats": ("int",)},
    "crusader":   {"mix": (0.45, 0.45, 0.10), "hit_die": 10, "atk_stats": ("str","cha")},
    "skald":      {"mix": (0.40, 0.25, 0.35), "hit_die": 8,  "atk_stats": ("cha","dex")},
    "war_priest": {"mix": (0.40, 0.40, 0.20), "hit_die": 8,  "atk_stats": ("int","str")},
    "druid":      {"mix": (0.45, 0.30, 0.25), "hit_die": 8,  "atk_stats": ("int","dex")},
    "monk":       {"mix": (0.50, 0.20, 0.30), "hit_die": 8,  "atk_stats": ("dex","int")},
}

# ---------- class fit weights (five stats only) ----------
CLASS_FIT_WEIGHTS: Dict[str, Dict[str, int]] = {
    "fighter":    {"str":3, "dex":1, "con":2, "int":0, "cha":0},
    "berserker":  {"str":3, "dex":0, "con":3, "int":0, "cha":0},
    "stalker":    {"str":0, "dex":3, "con":1, "int":2, "cha":0},
    "rogue":      {"str":0, "dex":3, "con":1, "int":1, "cha":1},
    "wizard":     {"str":0, "dex":1, "con":1, "int":3, "cha":0},
    "crusader":   {"str":2, "dex":0, "con":2, "int":1, "cha":2},
    "skald":      {"str":0, "dex":1, "con":0, "int":1, "cha":3},
    "war_priest": {"str":1, "dex":0, "con":2, "int":3, "cha":0},
    "druid":      {"str":0, "dex":1, "con":1, "int":3, "cha":0},
    "monk":       {"str":1, "dex":3, "con":1, "int":2, "cha":0},
}

def _norm_ability(x: int) -> float:
    return clamp01((int(x) - 3) / 17.0)

def compute_class_fit(abilities: Dict[str,int], cls: str) -> float:
    ckey = _normalize_class_key(cls)
    w = CLASS_FIT_WEIGHTS[ckey]
    num = 0.0; den = 0.0
    for a, wt in w.items():
        val = abilities.get(a.upper(), abilities.get(a, 10))
        num += wt * _norm_ability(val)
        den += abs(wt)
    den = den or 1.0
    return clamp01(num / den)

# ---------- equipment readers (ratings-local; mirror of engine shapes) ----------
def _equipped_maps(f: Dict[str, Any]) -> Tuple[Dict[str,Any], List[Dict[str,Any]]]:
    inv = f.get("inventory") or {}
    eq = f.get("equipped") or {}
    weapons = inv.get("weapons", []) or []
    return eq, weapons

def _find_item_by_id(items: List[Dict[str,Any]], iid: str | None) -> Dict[str,Any] | None:
    if not iid: return None
    for it in items:
        if it.get("id") == iid: return it
    return None

def _equipped_main_weapon(f: Dict[str, Any]) -> Dict[str, Any] | None:
    eq, weapons = _equipped_maps(f)
    it = _find_item_by_id(weapons, eq.get("main_hand_id"))
    if it: return it
    w = f.get("weapon")
    return w if isinstance(w, dict) else None

def _equipped_off_weapon(f: Dict[str, Any]) -> Dict[str, Any] | None:
    eq, weapons = _equipped_maps(f)
    return _find_item_by_id(weapons, eq.get("off_hand_id"))

def _has_shield_equipped(f: Dict[str, Any]) -> bool:
    eq = (f.get("equipped") or {})
    return bool(eq.get("shield_id"))

def _versatile_two_handing_now(f: Dict[str, Any], main: Dict[str,Any] | None) -> bool:
    if not main: return False
    if main.get("two_handed", False): return True
    if main.get("versatile", False) and (not _has_shield_equipped(f)) and (_equipped_off_weapon(f) is None):
        return True
    return False

# ---------- Off/Def/Mob components ----------
def offense_score(f: Dict[str,Any]) -> float:
    """
    Hybrid DPR baseline:
      - Weapon path: main-hand die (swap to two_handed_dice if currently two-handing),
        adds ability mod + proficiency; if off-hand weapon equipped, include its die too.
      - Caster path: base damage cantrip die * cantrip tier + INT mod.
      - Use the better of the two as DPR baseline.
    Hit% still uses best attack mod vs OFFENSE_BASELINE_AC.
    """
    lvl = int(f.get("level",1))
    cls = _normalize_class_key(str(f.get("class","fighter")))
    atk_stats = CLASS_PROFILES.get(cls, CLASS_PROFILES["fighter"])["atk_stats"]
    best_mod = max(mod(int(f.get(s.upper(), f.get(s,10)))) for s in atk_stats)
    prof = proficiency(lvl)
    attack_mod = best_mod + prof

    # --- Weapon DPR ---
    main = _equipped_main_weapon(f)
    weapon_dpr = 0.0
    if main:
        use_twohand = _versatile_two_handing_now(f, main)
        die = str(main.get("two_handed_dice" if use_twohand else "dice", main.get("dice", "1d6")))
        main_avg = die_avg_from_str(die) + best_mod + prof

        # Off-hand inclusion (if equipped): include its damage baseline too
        off = _equipped_off_weapon(f)
        off_avg = 0.0
        if off:
            off_die = str(off.get("dice", "1d6"))
            off_avg = die_avg_from_str(off_die)
            # add ability + proficiency (project rule: prof to damage as well)
            # off-hand proficiency to-hit varies in engine, but for DPR baseline we include its damage adders
            off_ability = "DEX" if (off.get("finesse") or off.get("ranged")) else off.get("ability", "STR")
            off_avg += mod(int(f.get(off_ability, f.get(off_ability.lower(), 10)))) + prof

        weapon_dpr = max(0.0, main_avg + off_avg)

    # --- Caster DPR (base damage cantrip) ---
    can_die, tier = base_cantrip_die_and_tier(f)
    caster_dpr = (die_avg_from_str(can_die) * max(1, tier)) + mod(int(f.get("INT", f.get("int", 10))))

    # Use the better of the two
    dpr = max(weapon_dpr, caster_dpr)

    # --- Hit chance vs baseline AC ---
    target_ac = OFFENSE_BASELINE_AC
    hit = clamp01((21 + attack_mod - target_ac) / 20.0)

    # Blend: favor hit probability slightly more than raw DPR (kept from prior design)
    return clamp01(0.55*hit + 0.45*clamp01(dpr / 12.0))  # dividing by 12 keeps scale reasonable

def defense_score(f: Dict[str,Any]) -> float:
    ac = int(f.get("ac", 12))
    hp = int(f.get("hp", 10))
    return clamp01(0.55*clamp01((ac-10)/10.0) + 0.45*clamp01((hp-8)/24.0))

def mobility_score(f: Dict[str,Any]) -> float:
    spd = int(f.get("speed", 9))
    dexm = mod(int(f.get("DEX", f.get("dex",10))))
    return clamp01(0.7*clamp01(spd/12.0) + 0.3*clamp01((10 + dexm - 10)/8.0))

# ---------- OVR ----------
def compute_ovr(f: Dict[str,Any]) -> int:
    cls = _normalize_class_key(str(f.get("class","fighter")))
    mix = CLASS_PROFILES.get(cls, CLASS_PROFILES["fighter"])["mix"]
    OFF = offense_score(f); DEF = defense_score(f); MOB = mobility_score(f)
    class_mix = mix[0]*OFF + mix[1]*DEF + mix[2]*MOB

    fit_input = {k.lower(): int(f.get(k.upper(), f.get(k,10))) for k in ["str","dex","con","int","cha"]}
    fit = compute_class_fit(fit_input, cls)

    total01 = 0.75*class_mix + 0.25*fit
    ovr = round(40 + (100-40) * clamp01(total01))

    # Also compute hidden role fits for UI recommendations
    f["role_fit"] = rank_archetypes(f)
    return ovr

# ---------- Level-up & simulation ----------
def level_up(f: Dict[str,Any]) -> None:
    cls = _normalize_class_key(str(f.get("class","fighter")))
    die = CLASS_PROFILES.get(cls, CLASS_PROFILES["fighter"])["hit_die"]
    f["level"] = int(f.get("level",1)) + 1
    lvl = f["level"]

    con_mod = mod(int(f.get("CON", f.get("con",10))))
    gain = (die // 2) + 1 + con_mod
    f["max_hp"] = int(f.get("max_hp", f.get("hp", 10))) + max(1, gain)
    f["hp"] = min(f["max_hp"], int(f.get("hp", f["max_hp"])))

    if lvl in (4,8,12,16,19):
        weights = CLASS_FIT_WEIGHTS.get(cls, {})
        order = sorted(weights.keys(), key=lambda a: weights[a], reverse=True)
        for a in order:
            key = a.upper()
            cur = int(f.get(key, f.get(a,10)))
            if cur < 20:
                f[key] = min(20, cur + 2)
                break

    # light AC nudge consistent with earlier approach
    dex_mod = mod(int(f.get("DEX",10)))
    base_ac = int(f.get("base_ac", f.get("ac",12)))
    f["ac"] = max(base_ac, base_ac + dex_mod // 2)
    f["OVR"] = compute_ovr(f)

def simulate_to_level(f: Dict[str,Any], target_level: int) -> Dict[str,Any]:
    g = dict(f)
    while int(g.get("level",1)) < target_level:
        level_up(g)
    return g

# ======================================================================
#                   Role & Archetype Fit (hidden)
# ======================================================================

# We compute a 0..1 score per archetype from features, similar to class fit.

# Weights per *archetype* (not just top-level role)
ROLE_FIT_WEIGHTS: Dict[str, Dict[str, float]] = {
    # Support
    "Healer":   {"healing_spells": 3, "cha": 1, "con": 1, "lay_on_hands": 2, "aura_support": 1},
    "Buffer":   {"buff_spells": 3, "int": 1, "cha": 1, "con": 1},
    "Debuffer": {"debuff_spells": 3, "int": 2, "dex": 1},

    # DPS
    "Sniper":    {"ranged_capable": 3, "ranged_spells": 2, "dex": 2, "int": 1},
    "Bombarder": {"aoe_spells": 3, "int": 2, "ranged_spells": 1},
    "Rush":      {"str": 2, "dex": 1, "speed": 1, "two_handed_capable": 1},
    "Assassin":  {"dex": 3, "stealth_capable": 3, "int": 1},

    # Tank
    "True Tank": {"con": 3, "shield_user": 2, "str": 1},
    "Taunter":   {"cha": 3, "con": 1, "int": 1},
    "Hero":      {"healing_spells": 2, "buff_spells": 2, "cha": 2, "con": 1, "aura_support": 2},
}

def _feature_pool(f: Dict[str, Any]) -> Dict[str, float]:
    # Base stats (normalized)
    stats = {
        "str": _norm_ability(f.get("STR", f.get("str", 10))),
        "dex": _norm_ability(f.get("DEX", f.get("dex", 10))),
        "con": _norm_ability(f.get("CON", f.get("con", 10))),
        "int": _norm_ability(f.get("INT", f.get("int", 10))),
        "cha": _norm_ability(f.get("CHA", f.get("cha", 10))),
    }

    # Equipment/flags
    main = _equipped_main_weapon(f)
    off  = _equipped_off_weapon(f)
    shield_user = 1.0 if _has_shield_equipped(f) else 0.0
    two_handed_now = 1.0 if _versatile_two_handing_now(f, main) or (main and main.get("two_handed", False)) else 0.0
    ranged_capable = 1.0 if ((main and main.get("ranged")) or (off and off.get("ranged"))) else 0.0
    speed = clamp01(int(f.get("speed", 4)) / 12.0)

    # Stealth capability: Rogue or Stalker>=10 (bonus action hide)
    cls = _normalize_class_key(str(f.get("class","")))
    lvl = int(f.get("level", 1))
    stealth_capable = 1.0 if (cls == "rogue" or (cls == "stalker" and lvl >= 10)) else 0.0

    # Spell category counts (normalized)
    sc = count_spell_tags(f)
    def norm_count(x): return clamp01(x / float(ROLE_SPELL_COUNT_CAP))
    buff_spells = norm_count(sc.get("buff", 0))
    debuff_spells = norm_count(sc.get("debuff", 0))
    healing_spells = norm_count(sc.get("healing", 0))
    ranged_spells = norm_count(sc.get("ranged", 0))
    aoe_spells = norm_count(sc.get("aoe", 0))

    # Paladin/Crusader auras & Lay on Hands
    aura_support = 1.0 if int(f.get("cru_aura_radius", 0)) > 0 else 0.0
    # Normalize Lay on Hands by its maximum at current level (5 * level)
    lay_pool_max = 5 * max(1, lvl)
    lay_on_hands = clamp01(int(f.get("cru_lay_on_hands_max", 0)) / float(lay_pool_max)) if lay_pool_max else 0.0

    pool = {
        **stats,
        "speed": speed,
        "ranged_capable": ranged_capable,
        "two_handed_capable": two_handed_now,
        "shield_user": shield_user,
        "stealth_capable": stealth_capable,
        "buff_spells": buff_spells,
        "debuff_spells": debuff_spells,
        "healing_spells": healing_spells,
        "ranged_spells": ranged_spells,
        "aoe_spells": aoe_spells,
        "aura_support": aura_support,
        "lay_on_hands": lay_on_hands,
    }
    return pool

def compute_role_fit(f: Dict[str, Any], archetype: str) -> float:
    w = ROLE_FIT_WEIGHTS.get(str(archetype), None)
    if not w: return 0.0
    pool = _feature_pool(f)
    num = 0.0; den = 0.0
    for k, wt in w.items():
        num += float(wt) * float(pool.get(k, 0.0))
        den += abs(float(wt))
    den = den or 1.0
    return clamp01(num / den)

def rank_archetypes(f: Dict[str, Any]) -> List[Tuple[str, float]]:
    """
    Returns a sorted list of (archetype, score) highest first.
    """
    out = [(name, compute_role_fit(f, name)) for name in ROLE_FIT_WEIGHTS.keys()]
    out.sort(key=lambda t: t[1], reverse=True)
    return out
