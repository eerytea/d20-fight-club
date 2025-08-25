# core/ratings.py
from __future__ import annotations
from typing import Dict
from .ratings_consts import CLASS_PROFILES  # single source of truth

def ability_mod(score: int) -> int:
    return (int(score) - 10) // 2

def proficiency_by_level(level: int) -> int:
    return 2 + ((max(1, int(level)) - 1) // 4)

def expected_weapon_dmg(dmg: str) -> float:
    try:
        n, s = dmg.lower().split("d")
        return int(n) * (1 + int(s)) / 2.0
    except Exception:
        return 4.0

def age_factor(age: int) -> float:
    if 21 <= age <= 26: return 1.05
    if age <= 30:       return 1.00
    if age < 21:        return 0.95
    return 0.92

def potential_factor(potential: int, age: int) -> float:
    base = 1.0 + (max(0, min(99, potential)) - 70) * 0.01
    if age < 23: base *= 0.98
    return base

def clamp01(x: float) -> float: return max(0.0, min(1.0, x))

def _attack_ability_for(f: Dict) -> int:
    cls = f.get("class", "Fighter")
    prof = CLASS_PROFILES.get(cls, CLASS_PROFILES["Fighter"])
    for key in prof.get("attack_stat_priority", ["str", "dex"]):
        if key in f:
            return ability_mod(f[key])
    return max(ability_mod(f.get("str", 10)), ability_mod(f.get("dex", 10)))

def _damage_bonus_for(f: Dict) -> int:
    cls = f.get("class", "Fighter")
    prof = CLASS_PROFILES.get(cls, CLASS_PROFILES["Fighter"])
    stat_key = prof.get("spell_damage_stat") or prof.get("melee_damage_stat") or "str"
    return max(0, ability_mod(f.get(stat_key, 10)))

def compute_component_offense(f: Dict) -> float:
    level = int(f.get("level", 1))
    atk_mod = _attack_ability_for(f) + proficiency_by_level(level)
    target_ac = 12
    hit_chance = clamp01((21 + atk_mod - target_ac) / 20.0)
    wpn = f.get("weapon", {"damage": "1d6"})
    base_dmg = expected_weapon_dmg(wpn.get("damage", "1d6"))
    dmg_bonus = _damage_bonus_for(f)
    dpr = hit_chance * (base_dmg + dmg_bonus)
    return 0.55 * hit_chance + 0.45 * clamp01(dpr / 8.0)

def compute_component_defense(f: Dict) -> float:
    level = int(f.get("level", 1))
    ac   = int(f.get("ac", 12))
    conm = ability_mod(int(f.get("con", 10)))
    hp = int(f.get("hp", 8 + int(f.get("con", 10))))
    tank = clamp01((ac - 10) / 10.0) * 0.6 + clamp01(hp / 20.0) * 0.4
    save = clamp01((proficiency_by_level(level) + conm + 2) / 8.0)
    return 0.65 * tank + 0.35 * save

def compute_component_mobility(f: Dict) -> float:
    spd  = int(f.get("speed", 6))
    dexm = ability_mod(int(f.get("dex", 10)))
    return clamp01(spd / 8.0) * 0.65 + clamp01((dexm + 3) / 6.0) * 0.35

OVR_MIN, OVR_MAX = 25, 90

def compute_ovr(f: Dict) -> int:
    cls = f.get("class", "Fighter")
    prof = CLASS_PROFILES.get(cls, CLASS_PROFILES["Fighter"])
    w_off, w_def, w_mob = prof.get("weights", (0.4, 0.4, 0.2))
    off = compute_component_offense(f)
    de  = compute_component_defense(f)
    mob = compute_component_mobility(f)
    tm = f.get("_trait_mods", {"off_mult": 1.0, "def_mult": 1.0, "mob_mult": 1.0, "ovr_mult": 1.0})
    total_01 = (w_off * off * tm.get("off_mult", 1.0)) + (w_def * de * tm.get("def_mult", 1.0)) + (w_mob * mob * tm.get("mob_mult", 1.0))
    total_01 *= age_factor(int(f.get("age", 24)))
    total_01 *= potential_factor(int(f.get("potential", 70)), int(f.get("age", 24)))
    total_01 *= tm.get("ovr_mult", 1.0)
    raw = OVR_MIN + (OVR_MAX - OVR_MIN) * clamp01(total_01)
    return int(round(max(OVR_MIN, min(OVR_MAX, raw))))

def value_wage_from_profile(ovr: int, age: int, potential: int, league_economy: float = 1.0) -> Dict[str, int]:
    norm = (ovr - OVR_MIN) / (OVR_MAX - OVR_MIN + 1e-6)
    base_val = (50_000 + 2_000_000 * (norm ** 2.2))
    pot_mult = 1.0 + (potential - 70) * 0.02
    if 21 <= age <= 26: age_mult = 1.15
    elif age <= 30:     age_mult = 1.00
    elif age < 21:      age_mult = 0.92
    else:               age_mult = 0.85
    value = int(base_val * pot_mult * age_mult * league_economy)
    wage  = int((value ** 0.5) * (0.6 + 0.01 * max(0, potential - 65)))
    return {"value": max(10_000, value), "wage": max(150, wage)}

def refresh_fighter_ratings(f: Dict, league_economy: float = 1.0) -> None:
    lvl = int(f.get("level", 1))
    f["prof"] = proficiency_by_level(lvl)
    f["atk_mod"] = _attack_ability_for(f) + f["prof"]
    f["eva_mod"] = ability_mod(int(f.get("dex", 10)))
    f["ovr"] = compute_ovr(f)
    f.update(value_wage_from_profile(f["ovr"], int(f.get("age", 24)), int(f.get("potential", 70))))

def level_up(f: Dict) -> None:
    f["level"] = int(f.get("level", 1)) + 1
    f["hp"] = int(f.get("hp", 8)) + 2
    lvl = int(f["level"])
    if lvl % 4 == 0:
        cls = f.get("class", "Fighter")
        prof = CLASS_PROFILES.get(cls, CLASS_PROFILES["Fighter"])
        for stat in prof.get("primaries", ["str"]):
            if f.get(stat,10) < 20:
                f[stat] = min(20, f[stat] + 2)
                break
        else:
            for stat in prof.get("secondaries", []):
                if f.get(stat,10) < 20:
                    f[stat] = min(20, f[stat] + 2)
                    break
    refresh_fighter_ratings(f)
