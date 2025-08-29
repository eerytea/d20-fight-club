# core/creator.py
from __future__ import annotations
import random
from typing import Dict, Any, List
from core.constants import RACES, DEFAULT_RACE_WEIGHTS, DEV_TRAITS
from core.ratings import compute_ovr, simulate_to_level, CLASS_FIT_WEIGHTS, calc_ac

_rng = random.Random()

# -------------------- helpers --------------------
STD_ARRAY = [15, 14, 13, 12, 10, 8]
ABIL_KEYS: List[str] = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]

def _weighted_choice(weights: Dict[str, float]) -> str:
    items = list(weights.items())
    total = sum(w for _, w in items) or 1.0
    r = _rng.random() * total
    acc = 0.0
    for k, w in items:
        acc += w
        if r <= acc:
            return k
    return items[-1][0]

def _assign_dev_trait() -> str:
    # 25% each
    return _rng.choice(["bad", "normal", "star", "superstar"])

def _choose_race(team: Dict[str, Any] | None) -> str:
    weights = (team or {}).get("race_weights") or DEFAULT_RACE_WEIGHTS
    # ensure all races exist with a number
    w = {r: float(weights.get(r, 1.0)) for r in RACES}
    return _weighted_choice(w)

def _choose_class_by_fit(abilities: Dict[str, int]) -> str:
    best_cls, best_score = None, -1.0
    for cls, w in CLASS_FIT_WEIGHTS.items():
        num = 0.0; den = 0.0
        for a, wt in w.items():
            val = abilities.get(a.upper(), abilities.get(a, 10))
            num += wt * max(0.0, (int(val) - 3) / 17.0)
            den += abs(wt)
        score = (num / den) if den else 0.0
        if score > best_score:
            best_cls, best_score = cls, score
    return best_cls or "fighter"

def _roll_standard_array(rng: random.Random) -> Dict[str, int]:
    """Assign the standard array randomly to the six ability keys."""
    vals = STD_ARRAY[:]   # copy
    rng.shuffle(vals)
    # random assignment to keys (also shuffled to be fully random)
    keys = ABIL_KEYS[:]
    rng.shuffle(keys)
    return {k: v for k, v in zip(keys, vals)}

# ultra-light fantasy name generator (guarantees a 'name' string)
_FIRST = ["Kael", "Ryn", "Mira", "Thorn", "Lysa", "Doran", "Nyra", "Kellan", "Sera", "Jorin",
          "Talia", "Bren", "Arin", "Sel", "Vara", "Garrin", "Orin", "Kira", "Fen", "Zara"]
_LAST  = ["Stone", "Vale", "Rook", "Ash", "Hollow", "Black", "Bright", "Gale", "Wolfe", "Mire",
          "Thorne", "Ridge", "Hawk", "Frost", "Dusk", "Iron", "Raven", "Drake", "Storm", "Oath"]

def _generate_name(rng: random.Random, race: str) -> str:
    # Slight variation by race (purely cosmetic): pick another pool index offset
    i = rng.randrange(0, len(_FIRST))
    j = (i + rng.randrange(0, len(_LAST))) % len(_LAST)
    return f"{_FIRST[i]} {_LAST[j]}"

# -------------------- main factory --------------------
def generate_fighter(team: Dict[str, Any] | None = None, seed: int | None = None) -> Dict[str, Any]:
    """
    Create a level-1 fighter dict with:
      - abilities from a RANDOM STANDARD ARRAY (15,14,13,12,10,8) randomly assigned to STR/DEX/CON/INT/WIS/CHA
      - class chosen by fit over abilities
      - race chosen from equal weights (or team['race_weights'] if provided)
      - dev_trait (bad/normal/star/superstar) controlling XP rate only
      - potential set to OVR at level 20 (simulated immediately)
    """
    rng = random.Random(seed) if seed is not None else _rng

    # 1) Abilities from random standard array
    base = _roll_standard_array(rng)

    # 2) Choose class by fit and race by weights
    cls = _choose_class_by_fit(base)
    race = _choose_race(team)
    dev_trait = _assign_dev_trait()

    # 3) Core vitals at level 1
    lvl = 1
    armor_bonus = 0  # placeholder for future gear system
    # Simple HP seed (class HD applied on future level_ups)
    hp = 10 + (base["CON"] - 10) // 2

    # 4) Build fighter object
    f: Dict[str, Any] = {
        "name": _generate_name(rng, race),   # ensure a displayable name
        "num": rng.randint(1, 99),
        "race": race,
        "class": cls,
        "level": lvl,
        "hp": hp,
        "max_hp": hp,
        "armor_bonus": armor_bonus,
        **base,
        "team_id": (team or {}).get("tid"),
        "dev_trait": dev_trait,         # invisible tag
        "xp": 0,
        "xp_rate": DEV_TRAITS[dev_trait],
    }

    # 5) AC using unified formula (includes armor_bonus placeholder)
    f["ac"] = calc_ac(f)

    # 6) Initial OVR at level 1
    f["OVR"] = compute_ovr(f)

    # 7) Potential: simulate to level 20 and record that OVR
    f20 = simulate_to_level(f, 20)
    f["potential"] = int(f20.get("OVR", f["OVR"]))

    return f
