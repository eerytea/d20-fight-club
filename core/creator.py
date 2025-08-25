# core/creator.py
# Random standard array (no min-max), Human +1 random among top stats,
# Class selection supports: weighted / pure_random (+ misfit_prob).
# Optional negative traits scaffold to create more "bad characters".

from typing import Dict, List, Optional, Tuple
import random

from .ratings import CLASS_PROFILES, refresh_fighter_ratings

FIRST_NAMES = [
    "Alex","Jordan","Riley","Casey","Morgan","Taylor","Jess","Drew","Parker","Sam",
    "Avery","Quinn","Cameron","Shawn","Jamie","Charlie","Sage","Rowan","Elliot","Skyler"
]
LAST_NAMES  = [
    "Stone","Brooks","Miller","Reeves","Hayes","Cole","Ford","Wells","Blake","Hale",
    "Rhodes","Kane","Page","Cross","York","Hart","Lake","Wade","Gates","Quill"
]

STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]
ABILITY_KEYS = ["str","dex","con","int","wis","cha"]

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

    # allow "misfit" spice
    if r.random() < misfit_prob:
        others = [c for c in ALL_CLASSES if c != best_cls]
        return r.choice(others)
    return best_cls

def maybe_negative_trait(r: random.Random, prob: float = 0.2) -> Optional[Tuple[str, Dict[str, float]]]:
    if r.random() < prob:
        return r.choice(NEG_TRAITS_POOL)
    return None

def generate_fighter(level: int = 1, rng: Optional[random.Random] = None,
                     class_mode: str = "weighted", misfit_prob: float = 0.15,
                     neg_trait_prob: float = 0.25) -> Dict:
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
        "potential": r.randint(55, 96),  # allow some lemons
        # Abilities
        "str": stats["str"], "dex": stats["dex"], "con": stats["con"],
        "int": stats["int"], "wis": stats["wis"], "cha": stats["cha"],
        # Combat
        "hp": hp, "ac": ac, "speed": speed, "weapon": weapon,
        # Progress
        "xp": 0,
    }

    # Optional negative trait
    trait = maybe_negative_trait(r, prob=neg_trait_prob)
    if trait:
        f.setdefault("traits", []).append(trait[0])
        f["_trait_mods"] = trait[1]  # used by ratings

    # Initial ratings
    refresh_fighter_ratings(f)
    return f

def generate_team(tid: int, name: str, size: int, seed: int,
                  class_mode: str = "weighted", misfit_prob: float = 0.15,
                  neg_trait_prob: float = 0.25, rng: Optional[random.Random] = None,
                  color: Tuple[int,int,int] = (180, 180, 220)) -> Dict:
    r = rng or random.Random(seed)
    fighters: List[Dict] = [
        generate_fighter(level=r.randint(1, 3), rng=r, class_mode=class_mode, misfit_prob=misfit_prob, neg_trait_prob=neg_trait_prob)
        for _ in range(size)
    ]
    team = {
        "tid": tid,
        "name": name,
        "color": list(color),
        "fighters": fighters,   # v1 naming (kept for backwards compat)
        "roster": fighters,     # v2 naming (used by new core)
        "budget": r.randint(250_000, 2_000_000),
        "wage_bill": sum(f.get("wage", 0) for f in fighters)
    }
    return team
