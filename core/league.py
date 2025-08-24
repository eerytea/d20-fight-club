# core/league.py
from __future__ import annotations
from typing import List, Tuple
from .types import Fixture

def generate_round_robin(team_count: int) -> List[List[Tuple[int,int]]]:
    """
    Returns weeks of (home, away) pairs; double round-robin (home/away switches).
    Uses circle method. Assumes even team_count.
    """
    teams = list(range(team_count))
    if team_count % 2 != 0:
        teams.append(-1)  # bye (won't happen if you use 20)
    n = len(teams)
    weeks_one = []
    for r in range(n-1):
        pairs = []
        for i in range(n//2):
            a = teams[i]; b = teams[n-1-i]
            if a != -1 and b != -1:
                # alternate home/away by round index for variety
                if r % 2 == 0:
                    pairs.append((a, b))
                else:
                    pairs.append((b, a))
        weeks_one.append(pairs)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]  # rotate
    # double round robin: flip home/away for the second half
    weeks_two = [[(b,a) for (a,b) in w] for w in weeks_one]
    return weeks_one + weeks_two

def build_fixtures(team_count: int) -> List[Fixture]:
    weeks = generate_round_robin(team_count)
    fixtures: List[Fixture] = []
    for w, pairs in enumerate(weeks, start=1):
        for (h,a) in pairs:
            fixtures.append(Fixture(week=w, home_id=h, away_id=a))
    return fixtures
