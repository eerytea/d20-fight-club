# core/creator.py
# Truly random standard array assignment (no min-max),
# Human +1 applied to a random ability among the current highest,
# class chosen via multi-factor weighted scoring + small randomness.
#
# Works with core/ratings.CLASS_PROFILES to finalize combat + OVR.

from typing import Dict, List, Optional
import random

from .ratings import CLASS_PROFILES, refresh_fighter_ratings

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

# ---- Class ability weights (multi-factor) ----
# Higher weight == more important for that class.
CLASS_WEIGHTS: Dict[str, Dict[str, int]] = {
    "Fighter":   {"str": 3, "dex": 1, "con": 2, "int": 0, "wis": 0, "cha": 0},
    "Barbarian": {"str": 3, "dex": 0, "con": 3, "int": 0, "wis": 0, "cha": 0},
    "Rogue":     {"str": 0, "dex": 3, "con": 1, "int": 1, "wis": 0, "cha": 1},
    "Wizard":    {"str": 0, "dex": 1, "con": 1, "int": 3, "wis": 0, "cha": 0},
    "Cleric":    {"str": 0, "dex": 0, "con": 2, "int": 0, "wis": 3, "cha": 0},
    "Sorcerer":  {"str": 0, "dex": 1, "con": 1, "int": 0, "wis": 0, "cha": 3},
}

def assign_standard_array(r: random.Random) -> Dict[str,int]:
    """Randomly assign the standard array to abilities with no optimization."""
    scores = STANDARD_ARRAY[:]
    r.shuffle(scores)
    return {k: v for k, v in zip(ABILITY_KEYS, scores)}

def apply_human_bonus(stats: Dict[str,int], r: random.Random) -> None:
    """+1 to a randomly chosen ability among those tied for highest."""
    max_val = max(stats.values())
    tied = [k for k, v in stats.items() if v == max_val]
    stats[r.choice(tied)] += 1

def class_score(stats: Dict[str,int], cls: str, r: random.Random) -> float:
    """Weighted sum with small randomness to avoid hard funnels."""
    weights = CLASS_WEIGHTS.get(cls, {})
    base = sum(stats.get(k, 10) * weights.get(k, 0) for k in ABILITY_KEYS)
    # ±10% jitter
    jitter = r.uniform(0.9, 1.1)
    return base * jitter

def pick_class(stats: Dict[str,int], r: random.Random) -> str:
    best_cls, best_score = None, float("-inf")
    for cls in CLASS_PROFILES.keys():
        sc = class_score(stats, cls, r)
        if sc > best_score:
            best_cls, best_score = cls, sc
    return best_cls or "Fighter"

def generate_fighter(level: int = 1, rng: Optional[random.Random] = None) -> Dict:
    r = rng or random.Random()

    # 1) Truly random standard array (no min-maxing)
    stats = assign_standard_array(r)

    # 2) Human +1 applied to random highest ability
    apply_human_bonus(stats, r)

    # 3) Pick class based on multi-factor weighted score (+jitter)
    cls = pick_class(stats, r)
    prof = CLASS_PROFILES[cls]

    # 4) Simple base combat; ratings will refine OVR/value
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
        "potential": r.randint(60, 96),
        # Abilities
        "str": stats["str"], "dex": stats["dex"], "con": stats["con"],
        "int": stats["int"], "wis": stats["wis"], "cha": stats["cha"],
        # Combat
        "hp": hp, "ac": ac, "speed": speed, "weapon": weapon,
    }

    refresh_fighter_ratings(f, league_economy=1.0)
    return f

def generate_team(name: str, tid: str, color=(120,180,255), size: int = 4, level: int = 1,
                  rng: Optional[random.Random] = None) -> Dict:
    r = rng or random.Random()
    fighters: List[Dict] = [generate_fighter(level=level, rng=r) for _ in range(size)]
    team = {
        "tid": tid,
        "name": name,
        "color": list(color),
        "fighters": fighters,
        "budget": r.randint(250_000, 2_000_000),
        "wage_bill": sum(f["wage"] for f in fighters)
    }
    return team
