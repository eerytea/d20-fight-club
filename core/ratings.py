# core/ratings.py
# Class-aware ratings with OVR mapped to 40..100.
# Combines: class-fit (abilities vs class weights), offense/defense/mobility, age/potential.
# Honors optional negative trait multipliers from creator.

from typing import Dict

# -------------------- Class Profiles (combat defaults) --------------------
CLASS_PROFILES: Dict[str, Dict] = {
    "Fighter": {
        "weights": (0.45, 0.40, 0.15),      # offense, defense, mobility
        "primaries": ["str", "con"],
        "secondaries": ["dex"],
        "attack_stat_priority": ["str", "dex"],
        "melee_damage_stat": "str",
        "weapon": {"name": "Longsword", "damage": "1d8"},
        "armor_ac": 16,
    },
    "Cleric": {
        "weights": (0.40, 0.40, 0.20),
        "primaries": ["wis", "con"],
        "secondaries": ["str"],
        "attack_stat_priority": ["wis", "str"],
        "spell_damage_stat": "wis",
        "melee_damage_stat": "str",
        "weapon": {"name": "Mace", "damage": "1d6"},
        "armor_ac": 16,
    },
    "Wizard": {
        "weights": (0.55, 0.25, 0.20),
        "primaries": ["int"],
        "secondaries": ["dex"],
        "attack_stat_priority": ["int"],
        "spell_damage_stat": "int",
        "weapon": {"name": "Quarterstaff", "damage": "1d6"},
        "armor_ac": 10,
    },
    "Rogue": {
        "weights": (0.50, 0.25, 0.25),
        "primaries": ["dex"],
        "secondaries": ["int"],
        "attack_stat_priority": ["dex"],
        "melee_damage_stat": "dex",
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
        "attack_stat_priority": ["cha"],
        "spell_damage_stat": "cha",
        "weapon": {"name": "Wand", "damage": "1d6"},
        "armor_ac": 12,
    },
}

# Class selection weights (kept here for standalone use when needed)
CLASS_WEIGHTS: Dict[str, Dict[str, int]] = {
    "Fighter":   {"str": 3, "dex": 1, "con": 2, "int": 0, "wis": 0, "cha": 0},
    "Barbarian": {"str": 3, "dex": 0, "con": 3, "int": 0, "wis": 0, "cha": 0},
    "Rogue":     {"str": 0, "dex": 3, "con": 1, "int": 1, "wis": 0, "cha": 1},
    "Wizard":    {"str": 0, "dex": 1, "con": 1, "int": 3, "wis": 0, "cha": 0},
    "Cleric":    {"str": 0, "dex": 0, "con": 2, "int": 0, "wis": 3, "cha": 0},
    "Sorcerer":  {"str": 0, "dex": 1, "con": 1, "int": 0, "wis": 0, "cha": 3},
}

# --- OVR range ---
OVR_MAX = 100
OVR_MIN = 40

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

def clamp01(x: float) -> float: return max(0.0, min(1.0, x))

# -------------------- Components --------------------
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
    ac = int(f.get("ac", 12))
    hp = int(f.get("hp", 10))
    ac_score  = clamp01((ac - 10) / 10.0)
    ehp_score = clamp01((hp - 8)  / 24.0)
    return 0.55 * ac_score + 0.45 * ehp_score

def compute_component_mobility(f: Dict) -> float:
    spd = int(f.get("speed", 6))
    dex_mod = ability_mod(f.get("dex", 10))
    spd_score = clamp01(spd / 12.0)
    dodge_score = clamp01((10 + dex_mod - 10) / 8.0)
    return 0.7 * spd_score + 0.3 * dodge_score

def compute_class_fit(f: Dict) -> float:
    """Ability-to-class alignment (0–1). Abilities max at 20."""
    cls = f.get("class", "Fighter")
    weights = CLASS_WEIGHTS.get(cls, {})
    if not weights: return 0.5
    top = sum(max(0, w) for w in weights.values()) * 20.0
    if top <= 0: return 0.5
    acc = 0.0
    for k, w in weights.items():
        acc += max(0, w) * float(f.get(k, 10))
    return clamp01(acc / top)

# -------------------- Age/Potential & Traits --------------------
def age_factor(age: int) -> float:
    if age < 20: return 0.93
    if age < 23: return 0.98
    if age < 26: return 1.00
    if age < 29: return 1.03
    if age < 31: return 1.02
    if age < 33: return 1.00
    if age < 35: return 0.97
    if age < 37: return 0.94
    return 0.90

def potential_factor(potential: int, age: int) -> float:
    base = (potential - 70) / 40.0
    youth = max(0.0, (25 - age) / 25.0)
    return 1.0 + 0.12 * base * youth

def trait_multipliers(f: Dict) -> Dict[str, float]:
    mods = f.get("_trait_mods", {})
    return {
        "off_mult": float(mods.get("off_mult", 1.0)),
        "def_mult": float(mods.get("def_mult", 1.0)),
        "mob_mult": float(mods.get("mob_mult", 1.0)),
        "ovr_mult": float(mods.get("ovr_mult", 1.0)),
    }

# -------------------- Overall (OVR) --------------------
def compute_ovr(f: Dict) -> int:
    cls = f.get("class", "Fighter")
    prof = CLASS_PROFILES.get(cls, CLASS_PROFILES["Fighter"])
    off_w, def_w, mob_w = prof["weights"]
    tm = trait_multipliers(f)

    off = compute_component_offense(f) * tm["off_mult"]   # 0–1
    de  = compute_component_defense(f) * tm["def_mult"]   # 0–1
    mob = compute_component_mobility(f) * tm["mob_mult"]  # 0–1
    fit = compute_class_fit(f)                            # 0–1

    comp = (off_w*off + def_w*de + mob_w*mob)
    total_01 = 0.75 * comp + 0.25 * fit

    total_01 *= age_factor(int(f.get("age", 24)))
    total_01 *= potential_factor(int(f.get("potential", 70)), int(f.get("age", 24)))
    total_01 *= tm["ovr_mult"]

    raw = OVR_MIN + (OVR_MAX - OVR_MIN) * clamp01(total_01)
    return int(round(max(OVR_MIN, min(OVR_MAX, raw))))

# -------------------- Value / Wage --------------------
def value_wage_from_profile(ovr: int, age: int, potential: int, league_economy: float = 1.0) -> Dict[str, int]:
    norm = (ovr - OVR_MIN) / (OVR_MAX - OVR_MIN + 1e-6)  # 0..1
    base_val = (75_000 + 2_500_000 * (norm ** 2.1))
    pot_mult = 1.0 + (potential - 70) * 0.02
    if 21 <= age <= 26: age_mult = 1.15
    elif age <= 30:     age_mult = 1.00
    elif age < 21:      age_mult = 0.92
    else:               age_mult = 0.85
    value = int(base_val * pot_mult * age_mult * league_economy)
    wage  = int((value ** 0.5) * (0.65 + 0.01 * max(0, potential - 65)))
    return {"value": max(15_000, value), "wage": max(200, wage)}

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

ASI_LEVELS = [4, 8, 12, 16, 19]

def level_up(f: Dict) -> None:
    f["level"] += 1
    cls = f.get("class", "Fighter")
    prof = CLASS_PROFILES.get(cls, CLASS_PROFILES["Fighter"])

    hit_die = {"Fighter":10,"Barbarian":12,"Rogue":8,"Cleric":8,"Wizard":6,"Sorcerer":6}.get(cls,8)
    avg = hit_die // 2 + 1
    f["hp"] += avg + max(0, (f.get("con",10) - 10) // 2)

    if f["level"] in ASI_LEVELS:
        primaries = prof.get("primaries", ["str"])
        for stat in primaries:
            if f.get(stat,10) < 20:
                f[stat] = min(20, f[stat] + 2)
                break
        else:
            for stat in prof.get("secondaries", []):
                if f.get(stat,10) < 20:
                    f[stat] = min(20, f[stat] + 2)
                    break

    refresh_fighter_ratings(f)
