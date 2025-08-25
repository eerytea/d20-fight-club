# core/schedule.py
from __future__ import annotations
from typing import List, Dict, Tuple, Iterable, Optional
import random
import hashlib

def _stable_id(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]

def build_double_round_robin(team_ids: List[int], rounds: int = 2, shuffle_seed: Optional[int] = None) -> List[Dict]:
    """
    Circle method, home/away balanced across two rounds.
    Returns a list of fixtures: { 'id', 'week', 'home_id', 'away_id' }.
    """
    assert len(team_ids) >= 2, "Need at least two teams"
    n = len(team_ids)

    # If odd, add a BYE (-1); we won't emit fixtures for byes.
    ids = team_ids[:]
    bye_id = None
    if n % 2 == 1:
        bye_id = -1
        ids.append(bye_id)
        n += 1

    # Optionally stabilize starting order for cosmetic variety
    if shuffle_seed is not None:
        rnd = random.Random(shuffle_seed)
        rnd.shuffle(ids)

    half = n // 2
    weeks_one_round: List[List[Tuple[int, int]]] = []

    # Circle algorithm: fix first, rotate the rest
    arr = ids[:]
    for _ in range(n - 1):
        left = arr[:half]
        right = list(reversed(arr[half:]))
        pairings = list(zip(left, right))
        weeks_one_round.append(pairings)

        # rotate (keep arr[0] fixed)
        arr = [arr[0]] + [arr[-1]] + arr[1:-1]

    fixtures: List[Dict] = []
    week = 0

    # Round 1: pairings as drawn (assign home/away alternating for balance)
    for pairings in weeks_one_round:
        for i, (a, b) in enumerate(pairings):
            if bye_id in (a, b):
                continue
            # lightly balance home/away across the round
            home, away = (a, b) if (i % 2 == 0) else (b, a)
            fid = _stable_id(f"R1-W{week}-H{home}-A{away}")
            fixtures.append({"id": fid, "week": week, "home_id": home, "away_id": away})
        week += 1

    # Round 2: swap home/away for the mirror
    for pairings in weeks_one_round:
        for i, (a, b) in enumerate(pairings):
            if bye_id in (a, b):
                continue
            home, away = (b, a) if (i % 2 == 0) else (a, b)
            fid = _stable_id(f"R2-W{week}-H{home}-A{away}")
            fixtures.append({"id": fid, "week": week, "home_id": home, "away_id": away})
        week += 1

    # If rounds != 2, replicate pattern appropriately (always alternate home/away per mirror)
    if rounds not in (1, 2):
        base = fixtures[:]
        fixtures = []
        for r in range(rounds):
            for fx in base:
                if r % 2 == 0:
                    home, away = fx["home_id"], fx["away_id"]
                else:
                    home, away = fx["away_id"], fx["home_id"]
                fixtures.append({
                    "id": _stable_id(f"R{r+1}-W{fx['week']}-H{home}-A{away}"),
                    "week": fx["week"] + (r * (n - 1)),
                    "home_id": home,
                    "away_id": away,
                })

    # Sort by week then home id for determinism
    fixtures.sort(key=lambda f: (f["week"], f["home_id"], f["away_id"]))
    return fixtures
