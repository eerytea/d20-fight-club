# core/career.py
from __future__ import annotations

import random
from typing import List, Tuple, Optional

from .types import Career, TableRow
from .league import round_robin_fixtures
from . import config


def _default_team_names(n: int) -> List[str]:
    base = [
        "Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Gamma", "Helix",
        "Iota", "Juno", "Kilo", "Lambda", "Mantis", "Nova", "Orion", "Pegasus",
        "Quantum", "Raptor", "Spartan", "Titan", "Umbra", "Vortex", "Wyvern", "Zephyr",
    ]
    if n <= len(base):
        return base[:n]
    # extend with numbers if needed
    out = base[:]
    i = 1
    while len(out) < n:
        out.append(f"Club {i}")
        i += 1
    return out[:n]


def _rand_color(rng: random.Random) -> Tuple[int, int, int]:
    return (rng.randint(40, 230), rng.randint(40, 230), rng.randint(40, 230))


def _make_roster_for_team(rng: random.Random, size: int) -> List[dict]:
    roster: List[dict] = []
    for i in range(size):
        # Very light fighter dict; engine/model.fighter_from_dict will hydrate
        name = f"F{i+1}"
        cls = rng.choice(["Fighter", "Cleric", "Wizard", "Rogue", "Barbarian", "Sorcerer"])
        ovr = rng.randint(48, 72)
        hp = rng.randint(8, 14)
        ac = rng.randint(10, 14)
        stats = {
            "str": rng.randint(8, 14),
            "dex": rng.randint(8, 14),
            "con": rng.randint(8, 14),
            "int": rng.randint(8, 14),
            "wis": rng.randint(8, 14),
            "cha": rng.randint(8, 14),
        }
        weapon = rng.choice([
            {"name": "Dagger", "damage": "1d4", "reach": 1},
            {"name": "Shortsword", "damage": "1d6", "reach": 1},
            {"name": "Spear", "damage": "1d6", "reach": 2},
            {"name": "Mace", "damage": "1d6", "reach": 1},
            {"name": "Greatsword", "damage": "2d6", "reach": 1},
        ])
        roster.append({
            "fighter_id": i, "name": name, "cls": cls, "level": 1, "ovr": ovr,
            "hp": hp, "max_hp": hp, "ac": ac, **stats, "weapon": weapon,
            "xp": 0, "age": rng.randint(18, 34), "years_left": rng.randint(1, 3),
        })
    return roster


def new_career(seed: Optional[int] = None, user_team_id: Optional[int] = None) -> Career:
    """
    Build a new career with deterministic RNG based on seed.
    Returns a Career object (from core/types.py) with teams, rosters, fixtures, table, etc.
    """
    seed = int(seed) if seed is not None else random.randint(1, 2_147_483_647)
    rng = random.Random(seed)

    num_teams = config.LEAGUE_TEAMS
    team_names = _default_team_names(num_teams)
    team_colors = [ _rand_color(rng) for _ in range(num_teams) ]
    rosters = [ _make_roster_for_team(rng, config.TEAM_SIZE) for _ in range(num_teams) ]

    fixtures = round_robin_fixtures(num_teams)

    # Table starts empty; rows created lazily by sim
    table: dict[int, TableRow] = {}

    career = Career(
        week=0,
        seed=seed,
        team_names=team_names,
        team_colors=team_colors,
        rosters=rosters,
        fixtures=fixtures,
        table=table,
        user_team_id=user_team_id,
    )
    return career
