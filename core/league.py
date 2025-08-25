# core/league.py
from __future__ import annotations
from typing import List, Tuple
from .types import Fixture


def round_robin_fixtures(num_teams: int) -> List[Fixture]:
    """
    Simple single round-robin using the circle method.
    Returns a flat list of Fixture objects with .week, .home_id, .away_id, played=False.
    Team ids are 0..num_teams-1
    """
    if num_teams < 2:
        return []

    teams = list(range(num_teams))
    if num_teams % 2 == 1:
        teams.append(-1)  # bye marker

    n = len(teams)
    half = n // 2
    weeks: List[List[Tuple[int, int]]] = []

    arr = teams[:]
    for _ in range(n - 1):
        pairings: List[Tuple[int, int]] = []
        for i in range(half):
            t1 = arr[i]
            t2 = arr[n - 1 - i]
            if t1 != -1 and t2 != -1:
                # alternate home/away per week for variety
                if len(weeks) % 2 == 0:
                    pairings.append((t1, t2))
                else:
                    pairings.append((t2, t1))
        weeks.append(pairings)
        # rotate (keep first fixed)
        arr = [arr[0]] + [arr[-1]] + arr[1:-1]

    # Flatten to Fixture list
    fixtures: List[Fixture] = []
    for w, pairs in enumerate(weeks):
        for (h, a) in pairs:
            fixtures.append(Fixture(week=w, home_id=h, away_id=a, played=False, home_goals=None, away_goals=None))
    return fixtures
