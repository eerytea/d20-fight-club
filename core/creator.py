# core/creator.py
# Fighter generation: standard array, Human +1 to highest, class fit, gear, ratings.

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

def assign_standard_array(r: random.Random) -> Dict[str,int]:
    scores = STANDARD_ARRAY[:]
    r.shuffle(scores)
    return {k: v for k, v in zip(ABILITY_KEYS, scores)}

def apply_human_bonus(stats: Dict[str,int]) -> None:
    # +1 to the single highest ability (ties break by STR, DEX, CON, INT, WIS, CHA order)
    order = ["str","dex","con","int","wis","cha"]
    best = max(stats.values())
    for k in order:
        if stats[k] == best:
            stats[k] += 1
            break

def score_class_fit(stats: Dict[str,int], cls: str) -> int:
    prof = CLASS_PROFILES[cls]
    score = 0
    for k in prof.get("primaries", []):
        score += stats.get(k, 10) * 2
    for k in prof.get("secondaries", []):
        score += stats.get(k, 10)
    return score

def pick_class(stats: Dict[str,int]) -> str:
    best_cls, best_score = None, -10**9
    for cls in CLASS_PROFILES.keys():
        sc = score_class_fit(stats, cls)
        if sc > best_score:
            best_cls, best_score = cls, sc
    return best_cls or "Fighter"

def generate_fighter(level: int = 1, rng: Optional[random.Random] = None) -> Dict:
    r = rng or random.Random()
    stats = assign_standard_array(r)
    apply_human_bonus(stats)

    cls = pick_class(stats)
    prof = CLASS_PROFILES[cls]

    # Basic combat (simple abstractions)
    # You can later swap in class-specific hit dice; for now keep it simple and balanced for the sim.
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
    fighters: List[Dict] = []
    for _ in range(size):
        f = generate_fighter(level=level, rng=r)
        fighters.append(f)

    team = {
        "tid": tid,
        "name": name,
        "color": list(color),
        "fighters": fighters,
        "budget": r.randint(250_000, 2_000_000),
        "wage_bill": sum(f["wage"] for f in fighters)
    }
    return team
