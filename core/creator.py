# core/creator.py
from __future__ import annotations
import random
from typing import Dict, Any
from core.constants import RACES, DEFAULT_RACE_WEIGHTS, DEV_TRAITS
from core.ratings import compute_ovr, simulate_to_level, CLASS_FIT_WEIGHTS, calc_ac

_rng = random.Random()

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
    # 25% each as requested
    return _rng.choice(["bad","normal","star","superstar"])

def _choose_race(team: Dict[str,Any] | None) -> str:
    weights = (team or {}).get("race_weights") or DEFAULT_RACE_WEIGHTS
    # ensure all races are present
    w = {r: float(weights.get(r, 1.0)) for r in RACES}
    return _weighted_choice(w)

def _choose_class_by_fit(abilities: Dict[str,int]) -> str:
    best_cls, best_score = None, -1.0
    for cls, w in CLASS_FIT_WEIGHTS.items():
        num = 0.0; den = 0.0
        for a, wt in w.items():
            val = abilities.get(a.upper(), abilities.get(a,10))
            num += wt * max(0.0, (int(val) - 3) / 17.0)
            den += abs(wt)
        score = (num / den) if den else 0.0
        if score > best_score:
            best_cls, best_score = cls, score
    return best_cls or "fighter"

def generate_fighter(team: Dict[str,Any] | None = None, seed: int | None = None) -> Dict[str,Any]:
    """
    Create a level-1 fighter dict with:
      - class chosen by fit over STR/DEX/CON/INT/WIS/CHA
      - race chosen from equal weights (or team["race_weights"] if provided)
      - dev_trait (bad/normal/star/superstar) controlling XP rate only
      - potential set to OVR at level 20 (simulated immediately)
    """
    rng = random.Random(seed) if seed is not None else _rng

    # base abilities
    base = {
        "STR": rng.randint(8, 16),
        "DEX": rng.randint(8, 16),
        "CON": rng.randint(8, 16),
        "INT": rng.randint(8, 16),
        "WIS": rng.randint(8, 16),
        "CHA": rng.randint(8, 16),
    }

    cls = _choose_class_by_fit(base)
    race = _choose_race(team)
    dev_trait = _assign_dev_trait()

    lvl = 1
    # armor bonus placeholder until gear system
    armor_bonus = 0

    f: Dict[str,Any] = {
        "name": "Rookie",
        "num": rng.randint(1, 99),
        "race": race,
        "class": cls,
        "level": lvl,
        "hp": 10 + (base["CON"] - 10)//2,  # simple base until class HD scaling on level_up
        "max_hp": 0,   # set after hp below
        "armor_bonus": armor_bonus,
        **base,
        "team_id": (team or {}).get("tid"),
        "dev_trait": dev_trait,                 # invisible tag
        "xp": 0,
        "xp_rate": DEV_TRAITS[dev_trait],       # multiplier for future XP grants
    }

    # AC (and normalize hp/max_hp)
    f["ac"] = calc_ac(f)
    f["max_hp"] = f["hp"]

    # Initial OVR at level 1
    f["OVR"] = compute_ovr(f)

    # Potential: simulate to level 20, record OVR
    f20 = simulate_to_level(f, 20)
    f["potential"] = int(f20.get("OVR", f["OVR"]))

    return f
