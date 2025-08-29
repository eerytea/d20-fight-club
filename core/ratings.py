# core/ratings.py
from __future__ import annotations
from typing import Dict, Any, Tuple

# ---------- helpers ----------
def clamp01(x: float) -> float: return max(0.0, min(1.0, x))
def mod(stat: int) -> int: return (stat - 10) // 2
def die_avg(d: int) -> float: return (1 + d) / 2.0

def proficiency(level: int) -> int:
    if level <= 4:  return 2
    if level <= 8:  return 3
    if level <= 12: return 4
    if level <= 16: return 5
    return 6

# ---------- class profiles ----------
# mix = (off, def, mob) weights sum to 1; hit_die for level-up; atk_stats=best stat mods to use
CLASS_PROFILES: Dict[str, Dict[str, Any]] = {
    "fighter":   {"mix": (0.45, 0.40, 0.15), "hit_die": 10, "atk_stats": ("str","dex")},
    "barbarian": {"mix": (0.55, 0.35, 0.10), "hit_die": 12, "atk_stats": ("str",)},
    "ranger":    {"mix": (0.45, 0.25, 0.30), "hit_die": 10, "atk_stats": ("dex","str")},
    "rogue":     {"mix": (0.50, 0.20, 0.30), "hit_die": 8,  "atk_stats": ("dex",)},
    "wizard":    {"mix": (0.55, 0.20, 0.25), "hit_die": 6,  "atk_stats": ("int",)},
    "sorcerer":  {"mix": (0.55, 0.20, 0.25), "hit_die": 6,  "atk_stats": ("cha",)},
    "paladin":   {"mix": (0.45, 0.45, 0.10), "hit_die": 10, "atk_stats": ("str","cha")},
    "bard":      {"mix": (0.40, 0.25, 0.35), "hit_die": 8,  "atk_stats": ("cha","dex")},
    "cleric":    {"mix": (0.40, 0.40, 0.20), "hit_die": 8,  "atk_stats": ("wis","str")},
    "druid":     {"mix": (0.45, 0.30, 0.25), "hit_die": 8,  "atk_stats": ("wis","dex")},
    "monk":      {"mix": (0.50, 0.20, 0.30), "hit_die": 8,  "atk_stats": ("dex","wis")},
    "warlock":   {"mix": (0.55, 0.20, 0.25), "hit_die": 8,  "atk_stats": ("cha","int")},
}

# ---------- class fit weights (for class assignment) ----------
CLASS_FIT_WEIGHTS: Dict[str, Dict[str, int]] = {
    "fighter":   {"str":3, "dex":1, "con":2, "int":0, "wis":0, "cha":0},
    "barbarian": {"str":3, "dex":0, "con":3, "int":0, "wis":0, "cha":0},
    "ranger":    {"str":0, "dex":3, "con":1, "int":0, "wis":2, "cha":0},
    "rogue":     {"str":0, "dex":3, "con":1, "int":1, "wis":0, "cha":1},
    "wizard":    {"str":0, "dex":1, "con":1, "int":3, "wis":0, "cha":0},
    "sorcerer":  {"str":0, "dex":1, "con":1, "int":0, "wis":0, "cha":3},
    "paladin":   {"str":2, "dex":0, "con":2, "int":0, "wis":1, "cha":2},
    "bard":      {"str":0, "dex":1, "con":0, "int":1, "wis":0, "cha":3},
    "cleric":    {"str":1, "dex":0, "con":2, "int":0, "wis":3, "cha":0},
    "druid":     {"str":0, "dex":1, "con":1, "int":1, "wis":3, "cha":0},
    "monk":      {"str":1, "dex":3, "con":1, "int":0, "wis":2, "cha":0},
    "warlock":   {"str":0, "dex":0, "con":1, "int":1, "wis":0, "cha":3},
}

def _norm_ability(x: int) -> float:
    return clamp01((x - 3) / 17.0)

def compute_class_fit(abilities: Dict[str,int], cls: str) -> float:
    w = CLASS_FIT_WEIGHTS[cls]
    num = sum(w[a]*_norm_ability(abilities.get(a.upper(), abilities.get(a,10))) for a in w)
    den = sum(abs(v) for v in w.values()) or 1
    return clamp01(num / den)

# ---------- Off/Def/Mob components ----------
def offense_score(f: Dict[str,Any]) -> float:
    lvl = int(f.get("level",1))
    cls = str(f.get("class","fighter")).lower()
    atk_stats = CLASS_PROFILES.get(cls, CLASS_PROFILES["fighter"])["atk_stats"]
    best_mod = max(mod(int(f.get(s.upper(), f.get(s,10)))) for s in atk_stats)
    prof = proficiency(lvl)
    attack_mod = best_mod + prof
    target_ac = 12
    hit = clamp01((21 + attack_mod - target_ac) / 20.0)
    dpr = die_avg(8) + best_mod  # simple baseline
    return clamp01(0.55*hit + 0.45*clamp01(dpr/8.0))

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
    cls = str(f.get("class","fighter")).lower()
    mix = CLASS_PROFILES.get(cls, CLASS_PROFILES["fighter"])["mix"]
    OFF = offense_score(f); DEF = defense_score(f); MOB = mobility_score(f)
    class_mix = mix[0]*OFF + mix[1]*DEF + mix[2]*MOB

    fit = compute_class_fit(
        {k.lower(): int(f.get(k.upper(), f.get(k,10))) for k in ["str","dex","con","int","wis","cha"]},
        cls
    )
    total01 = 0.75*class_mix + 0.25*fit
    return round(40 + (100-40) * clamp01(total01))

# ---------- Level-up & simulation (1..20) ----------
def level_up(f: Dict[str,Any]) -> None:
    cls = str(f.get("class","fighter")).lower()
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
        changed = False
        for a in order:
            key = a.upper()
            cur = int(f.get(key, f.get(a,10)))
            if cur < 20:
                f[key] = min(20, cur + 2)
                changed = True
                break
        if not changed:
            for a in ("DEX","CON"):
                cur = int(f.get(a,10))
                if cur < 20:
                    f[a] = min(20, cur + 2)
                    break

    dex_mod = mod(int(f.get("DEX",10)))
    base_ac = int(f.get("base_ac", f.get("ac",12)))
    f["ac"] = max(base_ac, base_ac + dex_mod // 2)
    f["OVR"] = compute_ovr(f)

def simulate_to_level(f: Dict[str,Any], target_level: int) -> Dict[str,Any]:
    g = dict(f)
    while int(g.get("level",1)) < target_level:
        level_up(g)
    return g
