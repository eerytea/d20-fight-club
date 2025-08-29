# core/creator.py
from __future__ import annotations
import random
from typing import Dict, Any, List
from core.constants import RACES, DEFAULT_RACE_WEIGHTS, DEV_TRAITS, RACE_TRAITS, RACE_SPEED
from core.ratings import compute_ovr, simulate_to_level, CLASS_FIT_WEIGHTS
from core.ac import calc_ac

_rng = random.Random()

STD_ARRAY = [15, 14, 13, 12, 10, 8]
ABIL_KEYS: List[str] = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]

def _weighted_choice(weights: Dict[str, float]) -> str:
    items = list(weights.items())
    total = sum(w for _, w in items) or 1.0
    pick = _rng.random() * total
    acc = 0.0
    for key, w in items:
        acc += w
        if pick <= acc:
            return key
    return items[-1][0]

def _apply_race_bonuses(abilities: Dict[str,int], race_code: str) -> Dict[str,int]:
    d = dict(abilities)
    mods = RACE_TRAITS.get(race_code, {})
    for k, v in mods.items():
        if k in d:
            d[k] = int(d[k]) + int(v)
    return d

def _choose_class_by_fit(abilities: Dict[str,int]) -> str:
    lowers = {k.lower(): int(v) for k, v in abilities.items()}
    best_cls, best_score = None, -1.0
    for cls, weights in CLASS_FIT_WEIGHTS.items():
        num = 0.0; den = 0.0
        for a, w in weights.items():
            den += abs(w)
            num += lowers.get(a, 10) * w
        score = (num / den) if den else 0.0
        if score > best_score:
            best_cls, best_score = cls, score
    return (best_cls or "fighter").capitalize()

def _roll_standard_array(rng: random.Random) -> Dict[str, int]:
    vals = STD_ARRAY[:]
    rng.shuffle(vals)
    keys = ABIL_KEYS[:]
    rng.shuffle(keys)
    return {k: v for k, v in zip(keys, vals)}

_FIRST = ["Kael","Ryn","Mira","Thorn","Lysa","Doran","Nyra","Kellan","Sera","Jorin",
          "Talia","Bren","Arin","Sel","Vara","Garrin","Orin","Kira","Fen","Zara"]
_LAST  = ["Stone","Vale","Rook","Ash","Hollow","Black","Bright","Gale","Wolfe","Mire",
          "Thorne","Ridge","Hawk","Frost","Dusk","Iron","Raven","Drake","Storm","Oath"]

def _generate_name(rng: random.Random, race: str) -> str:
    i = rng.randrange(0, len(_FIRST))
    j = (i + rng.randrange(0, len(_LAST))) % len(_LAST)
    return f"{_FIRST[i]} {_LAST[j]}"

def _choose_race(team: Dict[str,Any] | None, rng: random.Random) -> str:
    weights = (team or {}).get("race_weights") or DEFAULT_RACE_WEIGHTS
    for r in RACES:
        weights.setdefault(r, 1.0)
    return _weighted_choice(weights)

def _assign_dev_trait(rng: random.Random) -> str:
    pools = [("bad", 0.12), ("normal", 0.58), ("star", 0.22), ("superstar", 0.08)]
    total = sum(w for _, w in pools)
    x = rng.random() * total
    acc = 0.0
    for name, w in pools:
        acc += w
        if x <= acc:
            return name
    return "normal"

def generate_fighter(team: Dict[str, Any] | None = None, seed: int | None = None) -> Dict[str, Any]:
    """
    Generates a L1 fighter with race/class/abilities, now including:
      - Race-specific speed (RACE_SPEED)
      - Special AC rules (handled by calc_ac)
      - Goblin: outgoing damage bonus = level (dmg_bonus_per_level=1)
    """
    rng = _rng if seed is None else random.Random(seed)

    # 1) Identity + abilities
    race = _choose_race(team, rng)
    base = _roll_standard_array(rng)
    base = _apply_race_bonuses(base, race)

    # 2) Class fit
    cls = _choose_class_by_fit(base)
    dev_trait = _assign_dev_trait(rng)

    # 3) Vitals
    lvl = 1
    armor_bonus = 0
    hp = 10 + (base["CON"] - 10) // 2

    # 4) Build fighter
    f: Dict[str, Any] = {
        "name": _generate_name(rng, race),
        "num": rng.randint(1, 99),
        "race": race,
        "class": cls,
        "level": lvl,
        "hp": hp,
        "max_hp": hp,
        "ac": 10,  # recomputed below
        "armor_bonus": armor_bonus,
        **base,
        "str": base.get("STR",10), "dex": base.get("DEX",10), "con": base.get("CON",10),
        "int": base.get("INT",10), "wis": base.get("WIS",10), "cha": base.get("CHA",10),
        "team_id": (team or {}).get("tid"),
        "origin": (team or {}).get("country"),
        "age": rng.randint(18, 38),
        "dev_trait": dev_trait,
        "xp": 0,
        "xp_rate": DEV_TRAITS[dev_trait],
        "alive": True,
        # NEW: race speed
        "speed": int(RACE_SPEED.get(race, 4)),
    }

    # NEW: Goblin bonus damage per level (applies to any damage they deal)
    if race == "goblin":
        f["dmg_bonus_per_level"] = 1  # engine multiplies by current level

    # 5) AC via helper (handles Lizardkin & Golem rules)
    f["ac"] = calc_ac(f)

    # 6) Ratings now and at 20
    f["OVR"] = compute_ovr(f)
    f20 = simulate_to_level(f, 20)
    f["potential"] = int(f20.get("OVR", f["OVR"]))

    return f
