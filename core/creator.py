# core/creator.py
# Random standard array (no min-max), Human +1 random among top stats,
# Class selection supports: weighted / pure_random (+ misfit_prob).
# Optional negative traits scaffold to create more "bad characters".

from typing import Dict, List, Optional, Tuple
import random

from .ratings import CLASS_PROFILES, refresh_fighter_ratings

# Development traits (hidden growth archetypes)
# weight is the pick probability; mult is the XP gain multiplier applied on top of age.
DEV_TRAITS = [
    ("Bad Developer",    0.20, 0.75),
    ("Normal Developer", 0.55, 1.00),
    ("Star Developer",   0.20, 1.25),
    ("Superstar",        0.05, 1.50),
]

FIRST_NAMES = [
    "Alex","Jordan","Riley","Casey","Morgan","Taylor","Jess","Drew","Parker","Sam",
    "Avery","Quinn","Cameron","Shawn","Jamie","Charlie","Sage","Rowan","Elliot","Skyler"
]
LAST_NAMES  = [
    "Stone","Brooks","Miller","Reeves","Hayes","Cole","Ford","Wells","Blake","Hale",
    "Shaw","Sloan","Bishop","Rhodes","Vance","Kerr","Greer","Lane","Pryce","Lowe"
]

ABILITY_KEYS = ["str","dex","con","int","wis","cha"]
STANDARD_ARRAY = [15,14,13,12,10,8]

# Same weights used for class selection (multi-factor)
CLASS_WEIGHTS: Dict[str, Dict[str, int]] = {
    "Fighter":   {"str": 3, "dex": 1, "con": 2, "int": 0, "wis": 0, "cha": 0},
    "Barbarian": {"str": 3, "dex": 0, "con": 3, "int": 0, "wis": 0, "cha": 0},
    "Rogue":     {"str": 0, "dex": 3, "con": 1, "int": 1, "wis": 0, "cha": 1},
    "Wizard":    {"str": 0, "dex": 1, "con": 1, "int": 3, "wis": 0, "cha": 0},
    "Cleric":    {"str": 0, "dex": 0, "con": 2, "int": 0, "wis": 3, "cha": 0},
    "Sorcerer":  {"str": 0, "dex": 1, "con": 1, "int": 0, "wis": 0, "cha": 3},
}
ALL_CLASSES = list(CLASS_WEIGHTS.keys())

# Optional negative traits scaffold
NEG_TRAITS_POOL: List[Tuple[str, Dict[str, float]]] = [
    ("Glass Jaw", {"def_mult": 0.92}),
    ("Clumsy",    {"mob_mult": 0.94}),
    ("Timid",     {"off_mult": 0.93}),
    ("Injury-Prone", {"ovr_mult": 0.96}),
]

def assign_standard_array(r: random.Random) -> Dict[str,int]:
    scores = STANDARD_ARRAY[:]
    r.shuffle(scores)  # true random mapping (no min-max)
    return {k: v for k, v in zip(ABILITY_KEYS, scores)}

def apply_human_bonus(stats: Dict[str,int], r: random.Random) -> None:
    max_val = max(stats.values())
    tied = [k for k, v in stats.items() if v == max_val]
    stats[r.choice(tied)] += 1  # random among highest

def class_score(stats: Dict[str,int], cls: str, r: random.Random) -> float:
    w = CLASS_WEIGHTS.get(cls, {})
    base = sum(stats.get(k,10) * w.get(k,0) for k in ABILITY_KEYS)
    return base * r.uniform(0.9, 1.1)  # jitter ±10%

def pick_class(stats: Dict[str,int], r: random.Random, class_mode: str, misfit_prob: float) -> str:
    if class_mode == "pure_random":
        # equal chance for any class
        return r.choice(ALL_CLASSES)

    # weighted (default)
    best_cls, best_score = None, float("-inf")
    for cls in ALL_CLASSES:
        sc = class_score(stats, cls, r)
        if sc > best_score:
            best_cls, best_score = cls, sc

    # Occasionally force a misfit (deliberately bad assignment)
    if misfit_prob > 0 and r.random() < misfit_prob:
        others = [c for c in ALL_CLASSES if c != best_cls]
        return r.choice(others) if others else best_cls

    return best_cls or "Fighter"

def maybe_negative_trait(r: random.Random, prob: float = 0.20) -> Optional[Tuple[str, Dict[str, float]]]:
    return r.choice(NEG_TRAITS_POOL) if r.random() < prob else None

# Helper: consistent placeholder names
def make_placeholder_name(r):
    FIRST_NAMES = [
        "Alex","Jordan","Riley","Casey","Morgan","Taylor","Jess","Drew","Parker","Sam",
        "Avery","Quinn","Cameron","Shawn","Jamie","Charlie","Sage","Rowan","Elliot","Skyler"
    ]
    LAST_NAMES  = [
        "Stone","Brooks","Miller","Reeves","Hayes","Cole","Ford","Wells","Blake","Hale",
        "Shaw","Sloan","Bishop","Rhodes","Vance","Kerr","Greer","Lane","Pryce","Lowe"
    ]
    return f"{r.choice(FIRST_NAMES)} {r.choice(LAST_NAMES)}"

def generate_fighter(level: int = 1, rng: Optional[random.Random] = None,
                     class_mode: str = "weighted", misfit_prob: float = 0.15,
                     neg_trait_prob: float = 0.20) -> Dict:
    r = rng or random.Random()

    stats = assign_standard_array(r)
    apply_human_bonus(stats, r)
    cls = pick_class(stats, r, class_mode=class_mode, misfit_prob=misfit_prob)
    prof = CLASS_PROFILES[cls]

    # Simple base combat (class armor baseline, etc.)
    hp = 6 + stats["con"]
    ac = int(prof.get("armor_ac", 12))
    speed = r.randint(5, 8)
    weapon = dict(prof.get("weapon", {"name":"Club","damage":"1d4"}))

    f: Dict = {
        "pid": "",
        "name": f"{r.choice(FIRST_NAMES)} {r.choice(LAST_NAMES)}",
        "race": "Human",
        "class": cls,
        "level": int(level),
        "age": r.randint(18, 34),
        
        # Abilities
        "str": stats["str"], "dex": stats["dex"], "con": stats["con"],
        "int": stats["int"], "wis": stats["wis"], "cha": stats["cha"],
        # Combat
        "hp": hp, "ac": ac, "speed": speed, "weapon": weapon,
    }

    # Optional negative trait
    trait = maybe_negative_trait(r, prob=neg_trait_prob)
    if trait:
        f.setdefault("traits", []).append(trait[0])
        f["_trait_mods"] = trait[1]  # used by ratings
 # Assign a development trait
    roll = r.random()
    acc = 0.0
    for name, weight, mult in DEV_TRAITS:
        acc += weight
        if roll <= acc:
            f["dev_trait"] = name
            f["dev_mult"] = mult
            break
    if "dev_trait" not in f:
        f["dev_trait"] = "Normal Developer"
        f["dev_mult"] = 1.0
    refresh_fighter_ratings(f, league_economy=1.0)
    return f

def generate_team(name: str, tid: str, color=(120,180,255), size: int = 4, level: int = 1,
                  rng: Optional[random.Random] = None,
                  class_mode: str = "weighted", misfit_prob: float = 0.15, neg_trait_prob: float = 0.20) -> Dict:
    r = rng or random.Random()
    fighters: List[Dict] = [
        generate_fighter(level=level, rng=r, class_mode=class_mode, misfit_prob=misfit_prob, neg_trait_prob=neg_trait_prob)
        for _ in range(size)
    ]
    team = {
        "tid": tid,
        "name": name,
        "color": list(color),
        "fighters": fighters,
        "budget": r.randint(250_000, 2_000_000),
        "wage_bill": sum(f.get("wage", 0) for f in fighters)
    }
    return team
