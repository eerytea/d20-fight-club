# core/creator.py
from __future__ import annotations
import random
from typing import Dict, Any, List
from core.constants import (
    RACES, DEFAULT_RACE_WEIGHTS, DEV_TRAITS, RACE_TRAITS, RACE_SPEED, RACE_PERKS
)
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
    # ensure all race keys present
    for r in RACES:
        weights.setdefault(r, 1.0)
    return _weighted_choice(weights)

def _assign_dev_trait(rng: random.Random) -> str:
    pools = [("bad", 0.12), ("normal", 0.58), ("star", 0.22), ("superstar", 0.08)]
    roll = rng.random()
    acc = 0.0
    for name, p in pools:
        acc += p
        if roll <= acc:
            return name
    return "normal"

def generate_fighter(team: Dict[str, Any] | None = None, seed: int | None = None) -> Dict[str, Any]:
    rng = _rng if seed is None else random.Random(seed)

    # Identity + abilities
    race = _choose_race(team, rng)
    base = _roll_standard_array(rng)
    base = _apply_race_bonuses(base, race)

    # Class
    cls = _choose_class_by_fit(base)
    dev_trait = _assign_dev_trait(rng)

    # Vitals
    lvl = 1
    armor_bonus = 0
    hp_base = 10 + (base["CON"] - 10) // 2

    # Apply dwarf extra HP at level 1 (max HP bonus per level)
    extra_hp_per_level = int(RACE_PERKS.get(race, {}).get("extra_hp_per_level", 0))
    hp = hp_base + extra_hp_per_level

    f: Dict[str, Any] = {
        "name": _generate_name(rng, race),
        "num": rng.randint(1, 99),
        "race": race,
        "class": cls,
        "level": lvl,
        "hp": hp,
        "max_hp": hp,
        "ac": 10,  # recomputed
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
        "speed": int(RACE_SPEED.get(race, 4)),
        # Store perk flags directly on fighter for the engine to read
        "weekly_heal_mult": float(RACE_PERKS.get(race, {}).get("weekly_heal_mult", 1.0)),
        "adv_vs_charm": bool(RACE_PERKS.get(race, {}).get("adv_vs_charm", False)),
        "adv_vs_paralysis": bool(RACE_PERKS.get(race, {}).get("adv_vs_paralysis", False)),
        "adv_vs_poison": bool(RACE_PERKS.get(race, {}).get("adv_vs_poison", False)),
        "adv_vs_magic_mental": bool(RACE_PERKS.get(race, {}).get("adv_vs_magic_mental", False)),
        "sleep_immune": bool(RACE_PERKS.get(race, {}).get("sleep_immune", False)),
        "poison_resist": bool(RACE_PERKS.get(race, {}).get("poison_resist", False)),
        "cunning_action": bool(RACE_PERKS.get(race, {}).get("cunning_action", False)),
    }

    # Unarmed dice per race (if any). If you later equip a weapon, that overrides.
    unarmed = RACE_PERKS.get(race, {}).get("unarmed_dice")
    if unarmed:
        f["unarmed_dice"] = str(unarmed)

    # Goblin level-based damage bonus already handled separately (earlier patch)
    if race == "goblin":
        f["dmg_bonus_per_level"] = 1

    # AC (handles lizardkin 13+DEX and golem +1)
    f["ac"] = calc_ac(f)

    # Ratings
    f["OVR"] = compute_ovr(f)
    f20 = simulate_to_level(f, 20)
    f["potential"] = int(f20.get("OVR", f["OVR"]))

    return f
