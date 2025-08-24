# core/ratings.py
# Class-aware ratings, OVR, and simple value/wage model.

from typing import Dict

# -------------------- Class Profiles --------------------

CLASS_PROFILES: Dict[str, Dict] = {
    "Fighter": {
        "weights": (0.45, 0.40, 0.15),      # offense, defense, mobility
        "primaries": ["str", "con"],
        "secondaries": ["dex"],
        "attack_stat_priority": ["str", "dex"],  # to-hit stat order
        "melee_damage_stat": "str",
        "weapon": {"name": "Longsword", "damage": "1d8"},
        "armor_ac": 16,
    },
    "Cleric": {
        "weights": (0.40, 0.40, 0.20),
        "primaries": ["wis", "con"],
        "secondaries": ["str"],
        "attack_stat_priority": ["wis", "str"],  # spell/melee hybrid
        "spell_damage_stat": "wis",
        "melee_damage_stat": "str",
        "weapon": {"name": "Mace", "damage": "1d6"},
        "armor_ac": 16,
    },
    "Wizard": {
        "weights": (0.55, 0.25, 0.20),
        "primaries": ["int"],
        "secondaries": ["dex"],
        "attack_stat_priority": ["int"],     # spell attack proxy
        "spell_damage_stat": "int",
        "weapon": {"name": "Quarterstaff", "damage": "1d6"},
        "armor_ac": 10,
    },
    "Rogue": {
        "weights": (0.50, 0.25, 0.25),
        "primaries": ["dex"],
        "secondaries": ["int"],
        "attack_stat_priority": ["dex"],
        "melee_damage_stat": "dex",          # finesse proxy
        "weapon": {"name": "Dagger", "damage": "1d4"},
        "armor_ac": 14,
    },
    "Barbarian": {
        "weights": (0.55, 0.35, 0.10),
        "primaries": ["str", "con"],
        "secondaries": ["dex"],
        "attack_stat_priority": ["str"],
        "melee_damage_stat": "str",
        "weapon": {"name": "Greataxe", "damage": "1d12"},
        "armor_ac": 14,
    },
    "Sorcerer": {
        "weights": (0.55, 0.25, 0.20),
        "primaries": ["cha"],
        "secondaries": ["con"],
        "attack_stat_priority": ["cha"],     # spell attack proxy
        "spell_damage_stat": "cha",
        "weapon": {"name": "Wand", "damage": "1d6"},
        "armor_ac": 12,
    },
}

# -------------------- Core helpers --------------------

def ability_mod(score: int) -> int:
    return (score - 10) // 2

def proficiency_by_level(level: int) -> int:
    if level <= 4:  return 2
    if level <= 8:  return 3
    if level <= 12: return 4
    if level <= 16: return 5
    return 6

def expected_weapon_dmg(damage_die: str) -> float:
    try:
        num, die = damage_die.lower().split('d')
        num = int(num); die = int(die)
        return num * (die + 1) / 2.0
    except Exception:
        return 3.5

# -------------------- Components for OVR --------------------

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
    hit_chance = min(0.95, max(0.05, (21 + atk_mod - target_ac) / 20.0))

    wpn = f.get("weapon", {"damage": "1d6"})
    base_dmg = expected_weapon_dmg(wpn.get("damage", "1d6"))
    dmg_bonus = _damage_bonus_for(f)
    dpr = hit_chance * (base_dmg + dmg_bonus)

    return 100.0 * (0.55 * hit_chance + 0.45 * min(1.0, dpr / 8.0))

def compute_component_defense(f: Dict) -> float:
    ac = int(f.get("ac", 12))
    hp = int(f.get("hp", 10))
    ac_score  = min(1.0, max(0.0, (ac - 10) / 10.0))
    ehp_score = min(1.0, max(0.0, (hp - 8) / 24.0))
    return 100.0 * (0.55 * ac_score + 0.45 * ehp_score)

def compute_component_mobility(f: Dict) -> float:
    spd = int(f.get("speed", 6))
    dex_mod = ability_mod(f.get("dex", 10))
    spd_score = min(1.0, spd / 12.0)
    dodge_score = min(1.0, max(0.0, (10 + dex_mod - 10) / 8.0))
    return 100.0 * (0.7 * spd_score + 0.3 * dodge_score)

# -------------------- Age/Potential curves --------------------

def age_factor(age: int) -> float:
    if age < 20: return 0.92
    if age < 23: return 0.97
    if age < 26: return 1.00
    if age < 29: return 1.03
    if age < 31: return 1.02
    if age < 33: return 1.00
    if age < 35: return 0.97
    if age < 37: return 0.94
    return 0.90

def potential_factor(potential: int, age: int) -> float:
    base = (potential - 50) / 50.0
    youth = max(0.0, (25 - age) / 25.0)
    return 1.0 + 0.15 * base * youth

# -------------------- Overall (OVR) --------------------

def compute_ovr(f: Dict) -> int:
    cls = f.get("class", "Fighter")
    prof = CLASS_PROFILES.get(cls, CLASS_PROFILES["Fighter"])
    off_w, def_w, mob_w = prof["weights"]

    off = compute_component_offense(f)
    de  = compute_component_defense(f)
    mob = compute_component_mobility(f)

    raw = off_w*off + def_w*de + mob_w*mob
    raw *= age_factor(int(f.get("age", 24)))
    raw *= potential_factor(int(f.get("potential", 70)), int(f.get("age", 24)))
    return int(round(max(25, min(99, raw))))

# -------------------- Value / Wage model --------------------

def value_wage_from_profile(ovr: int, age: int, potential: int, league_economy: float = 1.0) -> Dict[str, int]:
    base_val = (ovr ** 2.1) * 15
    pot_mult = 1.0 + (potential - 70) * 0.03
    if 21 <= age <= 26: age_mult = 1.15
    elif age <= 30:     age_mult = 1.00
    elif age < 21:      age_mult = 0.90
    else:               age_mult = 0.85
    value = int(base_val * pot_mult * age_mult * league_economy)
    wage  = int((value ** 0.5) * (0.85 + (potential - 70) * 0.01) * (1.0 if 22 <= age <= 30 else 0.9))
    return {"value": max(10_000, value), "wage": max(200, wage)}

# -------------------- Public API --------------------

def refresh_fighter_ratings(f: Dict, league_economy: float = 1.0) -> None:
    lvl = int(f.get("level", 1))
    f["prof"] = proficiency_by_level(lvl)
    f["atk_mod"] = _attack_ability_for(f) + f["prof"]
    f["eva_mod"] = ability_mod(int(f.get("dex", 10)))
    f["ovr"] = compute_ovr(f)
    money = value_wage_from_profile(f["ovr"], int(f.get("age", 24)), int(f.get("potential", 70)), league_economy)
    f["value"] = money["value"]
    f["wage"]  = money["wage"]
