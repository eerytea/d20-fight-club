# core/creator.py
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import random

from .ratings_consts import CLASS_PROFILES, CLASS_WEIGHTS, ALL_CLASSES
from .ratings import refresh_fighter_ratings

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

NEG_TRAITS_POOL: List[Tuple[str, Dict[str, float]]] = [
    ("Glass Jaw", {"def_mult": 0.92}),
    ("Clumsy",    {"mob_mult": 0.94}),
    ("Timid",     {"off_mult": 0.93}),
    ("Injury-Prone", {"ovr_mult": 0.96}),
]

def assign_standard_array(r: random.Random) -> Dict[str,int]:
    scores = STANDARD_ARRAY[:]
    r.shuffle(scores)
    return {k: v for k, v in zip(ABILITY_KEYS, scores)}

def apply_human_bonus(stats: Dict[str,int], r: random.Random) -> None:
    max_val = max(stats.values())
    tied = [k for k, v in stats.items() if v == max_val]
    stats[r.choice(tied)] += 1

def class_score(stats: Dict[str,int], cls: str, r: random.Random) -> float:
    w = CLASS_WEIGHTS.get(cls, {})
    base = sum(stats.get(k,10) * w.get(k,0) for k in ABILITY_KEYS)
    return base * r.uniform(0.9, 1.1)

def pick_class(stats: Dict[str,int], r: random.Random, class_mode: str, misfit_prob: float) -> str:
    if class_mode == "pure_random":
        return r.choice(ALL_CLASSES)
    best_cls, best_score = None, float("-inf")
    for cls in ALL_CLASSES:
        sc = class_score(stats, cls, r)
        if sc > best_score:
            best_cls, best_score = cls, sc
    if r.random() < misfit_prob:
        others = [c for c in ALL_CLASSES if c != best_cls]
        return r.choice(others) if others else best_cls
    return best_cls

def maybe_negative_trait(r: random.Random, prob: float = 0.25) -> Optional[Tuple[str, Dict[str, float]]]:
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
        "potential": r.randint(55, 96),
        "str": stats["str"], "dex": stats["dex"], "con": stats["con"],
        "int": stats["int"], "wis": stats["wis"], "cha": stats["cha"],
        "hp": hp, "ac": ac, "speed": speed, "weapon": weapon,
        "xp": 0,
    }

    trait = maybe_negative_trait(r, prob=neg_trait_prob)
    if trait:
        f.setdefault("traits", []).append(trait[0])
        f["_trait_mods"] = trait[1]

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
        "fighters": fighters,   # legacy alias (kept for backward-compat)
        "roster": fighters,     # canonical key
        "budget": r.randint(250_000, 2_000_000),
        "wage_bill": sum(f.get("wage", 0) for f in fighters)
    }
    return team
