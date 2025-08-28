# core/creator.py
# Pipeline:
# 1) Pick race by town (pluggable distributions; placeholders now)
# 2) Assign standard array
# 3) Apply racial bonuses (+2/+1 etc.; Human = +1 to ALL stats)
# 4) Evaluate every class via ratings.compute_ovr and pick the best
# 5) Produce fighter dict (with BOTH lowercase and UPPERCASE stats for engine safety)

from typing import Dict, List, Optional, Tuple
import random

from .ratings import CLASS_PROFILES, compute_ovr, refresh_fighter_ratings

FIRST_NAMES = [
    "Alex","Jordan","Riley","Casey","Morgan","Taylor","Jess","Drew","Parker","Sam",
    "Avery","Quinn","Cameron","Shawn","Jamie","Charlie","Sage","Rowan","Elliot","Skyler",
    "Arin","Bren","Cael","Dara","Eryn","Finn","Garr","Hale","Iona","Joss","Kade","Lira",
]
LAST_NAMES  = [
    "Stone","Brooks","Miller","Reeves","Hayes","Cole","Ford","Wells","Blake","Hale",
    "Shaw","Sloan","Bishop","Rhodes","Vance","Kerr","Greer","Lane","Pryce","Lowe",
    "Blackwood","Stormborn","Ironhart","Quickstep","Nightbloom","Brightshield","Holloway",
]

ABILITY_KEYS = ["str","dex","con","int","wis","cha"]
STANDARD_ARRAY = [15,14,13,12,10,8]

# --- Races and bonuses ---
# Human: +1 to ALL ability scores (capped at 20)
RACES: Dict[str, Dict[str, int]] = {
    "Human":    {"str": 1, "dex": 1, "con": 1, "int": 1, "wis": 1, "cha": 1},
    "Elf":      {"dex": 2, "int": 1},
    "Dwarf":    {"con": 2, "str": 1},
    "Orc":      {"str": 2, "con": 1},
    "Halfling": {"dex": 2, "cha": 1},
    "Gnome":    {"int": 2, "dex": 1},
    "Tiefling": {"cha": 2, "int": 1},
    "Half-Elf": {"cha": 2, "dex": 1},
}

DEFAULT_RACE_BUCKETS = [
    ("Human", 0.40),
    ("Elf", 0.12), ("Dwarf", 0.12), ("Orc", 0.12),
    ("Halfling", 0.08), ("Gnome", 0.06), ("Tiefling", 0.06), ("Half-Elf", 0.04),
]

NEG_TRAITS_POOL: List[Tuple[str, Dict[str, float]]] = [
    ("Glass Jaw", {"def_mult": 0.92}),
    ("Clumsy",    {"mob_mult": 0.94}),
    ("Timid",     {"off_mult": 0.93}),
    ("Injury-Prone", {"ovr_mult": 0.96}),
]

# Example per-town distributions (placeholder; tweak per your lore)
TOWN_RACE_DISTS: Dict[str, List[Tuple[str, float]]] = {
    "Albion":  [("Human",0.50),("Elf",0.15),("Dwarf",0.12),("Orc",0.08),("Halfling",0.07),("Gnome",0.04),("Tiefling",0.03),("Half-Elf",0.01)],
    "Valoria": [("Human",0.35),("Tiefling",0.18),("Elf",0.14),("Gnome",0.10),("Dwarf",0.10),("Halfling",0.08),("Orc",0.03),("Half-Elf",0.02)],
    "Karthos": [("Human",0.38),("Orc",0.22),("Dwarf",0.16),("Elf",0.10),("Halfling",0.06),("Gnome",0.04),("Tiefling",0.03),("Half-Elf",0.01)],
    "Eldoria": [("Human",0.40),("Elf",0.22),("Gnome",0.12),("Halfling",0.10),("Tiefling",0.08),("Dwarf",0.05),("Orc",0.03)],
    "Norska":  [("Human",0.44),("Dwarf",0.22),("Orc",0.14),("Elf",0.10),("Halfling",0.05),("Gnome",0.03),("Tiefling",0.02)],
    "Zafira":  [("Human",0.36),("Tiefling",0.18),("Elf",0.14),("Gnome",0.10),("Halfling",0.08),("Dwarf",0.08),("Orc",0.06)],
    "Solheim": [("Human",0.42),("Elf",0.18),("Dwarf",0.14),("Halfling",0.10),("Gnome",0.08),("Tiefling",0.05),("Orc",0.03)],
    "Drakken": [("Human",0.30),("Orc",0.28),("Dwarf",0.16),("Elf",0.10),("Tiefling",0.08),("Gnome",0.04),("Halfling",0.04)],
}

def _weighted_choice(buckets: List[Tuple[str,float]], r: random.Random) -> str:
    s = sum(w for _, w in buckets)
    x = r.random() * (s if s > 0 else 1.0)
    acc = 0.0
    for name, w in buckets:
        acc += w
        if x <= acc:
            return name
    return buckets[-1][0]

# -------------------- Core steps --------------------
def assign_standard_array(r: random.Random) -> Dict[str,int]:
    scores = STANDARD_ARRAY[:]
    r.shuffle(scores)
    return {k: v for k, v in zip(ABILITY_KEYS, scores)}

def apply_racial_bonuses(stats: Dict[str,int], race: str, r: random.Random) -> None:
    """Apply racial bonuses. Human = +1 to ALL abilities (cap 20)."""
    bonus = RACES.get(race, {})
    for k, inc in bonus.items():
        if k in stats:
            stats[k] = min(20, stats[k] + int(inc))

def choose_race_for_town(town: Optional[str], r: random.Random) -> str:
    buckets = TOWN_RACE_DISTS.get(town or "", DEFAULT_RACE_BUCKETS)
    if not buckets:
        buckets = DEFAULT_RACE_BUCKETS
    return _weighted_choice(buckets, r)

def _baseline_combat_for_class(cls: str, stats: Dict[str,int], r: random.Random) -> Dict:
    prof = CLASS_PROFILES.get(cls, CLASS_PROFILES["Fighter"])
    hp = 6 + stats.get("con", 10)
    ac = int(prof.get("armor_ac", 12))
    speed = r.randint(6, 8)
    weapon = dict(prof.get("weapon", {"name":"Club","damage":"1d4"}))
    return {"hp": hp, "ac": ac, "speed": speed, "weapon": weapon}

def best_class_by_ovr(stats: Dict[str,int], r: random.Random,
                      age: int, potential: int, level: int) -> Tuple[str, int]:
    best_cls, best_ovr = "Fighter", -1
    for cls in CLASS_PROFILES.keys():
        f = {
            "class": cls,
            "level": level,
            "age": age,
            "potential": potential,
            **stats,
            **_baseline_combat_for_class(cls, stats, r),
        }
        ovr = compute_ovr(f)
        if ovr > best_ovr:
            best_cls, best_ovr = cls, ovr
    return best_cls, best_ovr

def maybe_negative_trait(r: random.Random, prob: float = 0.20) -> Optional[Tuple[str, Dict[str, float]]]:
    return r.choice(NEG_TRAITS_POOL) if r.random() < prob else None

# -------------------- Public API --------------------
def generate_fighter(level: int = 1, rng: Optional[random.Random] = None,
                     town: Optional[str] = None,
                     neg_trait_prob: float = 0.20) -> Dict:
    """
    Create one fighter using: town->race -> standard array -> racial bonuses -> best class by OVR.
    Returns a dict containing both lowercase and UPPERCASE ability keys for engine/UI compatibility.
    """
    r = rng or random.Random()
    age = r.randint(18, 34)
    potential = r.randint(60, 96)

    race = choose_race_for_town(town, r)
    stats = assign_standard_array(r)
    apply_racial_bonuses(stats, race, r)

    cls, best_ovr = best_class_by_ovr(stats, r, age=age, potential=potential, level=level)
    base_combat = _baseline_combat_for_class(cls, stats, r)

    first = r.choice(FIRST_NAMES); last = r.choice(LAST_NAMES)
    fighter: Dict = {
        "pid": "",
        "name": f"{first} {last}",
        "race": race,
        "class": cls,
        "level": int(level),
        "age": age,
        "potential": potential,
        # Abilities (lowercase, used by ratings)
        "str": stats["str"], "dex": stats["dex"], "con": stats["con"],
        "int": stats["int"], "wis": stats["wis"], "cha": stats["cha"],
        # Combat
        **base_combat,
    }

    trait = maybe_negative_trait(r, prob=neg_trait_prob)
    if trait:
        fighter.setdefault("traits", []).append(trait[0])
        fighter["_trait_mods"] = trait[1]

    refresh_fighter_ratings(fighter, league_economy=1.0)

    # Provide UPPERCASE mirrors for systems that expect them
    fighter.update({
        "STR": fighter["str"], "DEX": fighter["dex"], "CON": fighter["con"],
        "INT": fighter["int"], "WIS": fighter["wis"], "CHA": fighter["cha"],
        "hp": fighter["hp"], "max_hp": fighter["hp"],
        "ac": fighter["ac"],
        "alive": True,
    })

    return fighter

def generate_team(name: str, tid: str, color=(120,180,255), size: int = 6, level: int = 1,
                  rng: Optional[random.Random] = None,
                  town: Optional[str] = None,
                  neg_trait_prob: float = 0.20) -> Dict:
    r = rng or random.Random()
    fighters: List[Dict] = [
        generate_fighter(level=level, rng=r, town=town, neg_trait_prob=neg_trait_prob)
        for _ in range(size)
    ]
    team = {
        "tid": tid,
        "name": name,
        "color": list(color),
        "fighters": fighters,
        "budget": r.randint(300_000, 2_400_000),
        "wage_bill": sum(f.get("wage", 0) for f in fighters)
    }
    return team
