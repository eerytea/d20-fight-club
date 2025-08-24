# core/career.py
from __future__ import annotations
import random
from typing import List, Tuple
from .types import Career
from .creator import make_random_team
from .league import build_fixtures

def new_career(seed: int = 12345, team_count: int = 20) -> Career:
    rng = random.Random(seed)
    # toy team names/colors
    team_names = [f"Team {i+1}" for i in range(team_count)]
    team_colors = [(rng.randint(40,220), rng.randint(40,220), rng.randint(40,220)) for _ in range(team_count)]

    rosters = {tid: make_random_team(tid, team_names[tid], team_colors[tid], rng, size=6) for tid in range(team_count)}
    fixtures = build_fixtures(team_count)
    table = {}  # filled on first simulate_week_ai()

    return Career(
        seed=seed,
        week=1,
        team_names=team_names,
        team_colors=team_colors,
        rosters=rosters,
        fixtures=fixtures,
        table=table,
    )
