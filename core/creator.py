# core/creator.py
from __future__ import annotations
import random
from typing import List, Dict, Tuple
from .ratings import ovr_from_stats, project_potential_l20

STD_ARRAY = [15,14,13,12,10,8]
CLASSES = ["Fighter","Cleric","Wizard","Rogue","Barbarian","Sorcerer"]

def _assign_standard_array(rng: random.Random) -> Dict[str,int]:
    stats = ["str","dex","con","int","wis","cha"]
    arr = STD_ARRAY[:]
    rng.shuffle(arr)
    return {k:v for k,v in zip(stats,arr)}

def _human_bonus(stats: Dict[str,int], rng: random.Random) -> None:
    best = max(stats, key=lambda k: stats[k])
    # tie-break random: find all max keys then pick one
    mx = stats[best]
    cands = [k for k,v in stats.items() if v==mx]
    stats[rng.choice(cands)] += 1

def make_random_fighter(team_id: int, fid: int, rng: random.Random) -> Dict:
    stats = _assign_standard_array(rng)
    _human_bonus(stats, rng)
    cls = rng.choice(CLASSES)
    level = 1
    ac = 10 + (stats["dex"]-10)//2
    max_hp = 8 + (stats["con"]-10)//2  # crude baseline
    hp = max_hp
    age = rng.randint(18,32)
    # very simple weapon palette
    weapons = [
        {"name":"Shortsword","damage":"1d6","to_hit_bonus":1,"reach":1},
        {"name":"Spear","damage":"1d6","to_hit_bonus":0,"reach":2},
        {"name":"Mace","damage":"1d6","to_hit_bonus":1,"reach":1},
        {"name":"Dagger","damage":"1d4","to_hit_bonus":2,"reach":1},
    ]
    weapon = rng.choice(weapons)

    fighter = {
        "fighter_id": fid,
        "team_id": team_id,
        "name": f"{cls} #{fid}",
        "class": cls,
        "level": level,
        "ac": ac,
        "hp": hp,
        "max_hp": max_hp,
        "age": age,
        **stats,
        "weapon": weapon,
        "ovr": ovr_from_stats(stats),
        "potential": project_potential_l20(stats),
        "dev_trait": rng.choice(["Bad","Normal","Normal","Star","Superstar"]),
    }
    return fighter

def make_random_team(team_id: int, name: str, color: Tuple[int,int,int], rng: random.Random, size: int = 6) -> List[Dict]:
    return [make_random_fighter(team_id, team_id*100 + i, rng) for i in range(size)]
