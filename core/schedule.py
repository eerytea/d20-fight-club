# core/schedule.py
from __future__ import annotations
from typing import List, Dict, Optional
import hashlib
import random

def _stable_id(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]

def build_double_round_robin(team_ids: List[int], rounds: int = 2, shuffle_seed: Optional[int] = None) -> List[Dict]:
    """
    Build a round-robin schedule using the circle method.
    Returns a flat list of fixtures with 0-based weeks and home/away balanced across rounds.

    Each fixture dict has:
      - id: str
      - week: int (0-based)
      - home_id: int
      - away_id: int
    """
    ids = list(map(int, team_ids))
    assert len(ids) >= 2, "Need at least two teams"

    n = len(ids)
    # If odd, add a bye (-1) which we drop later
    bye = None
    if n % 2 == 1:
        bye = -1
        ids.append(bye)
        n += 1

    fixed = ids[0]
    rot = ids[1:]

    if shuffle_seed is not None:
        rng = random.Random(int(shuffle_seed))
        rng.shuffle(rot)

    weeks = []
    # One full round (n-1 weeks)
    for w in range(n - 1):
        week_pairs = []
        left = [fixed] + rot[: (n // 2) - 1]
        right = list(reversed(rot[(n // 2) - 1 :]))
        pairs = list(zip(left, right))
        week_pairs.extend(pairs)

        # rotate
        rot = [rot[-1]] + rot[:-1]
        weeks.append(week_pairs)

    fixtures: List[Dict] = []
    # two rounds: swap home/away on alternate rounds for balance
    for r in range(int(rounds)):
        for w, pairs in enumerate(weeks):
            for a, b in pairs:
                if a == bye or b == bye:
                    continue
                # Alternate home/away across rounds
                if r % 2 == 0:
                    home, away = a, b
                else:
                    home, away = b, a
                fixtures.append(
                    {
                        "id": _stable_id(f"R{r+1}-W{w}-H{home}-A{away}"),
                        "week": w + r * (len(weeks)),
                        "home_id": int(home),
                        "away_id": int(away),
                    }
                )

    # Sort deterministically
    fixtures.sort(key=lambda f: (f["week"], f["home_id"], f["away_id"]))
    return fixtures

def fixtures_double_round_robin(
    n_teams: int,
    start_week: int = 1,
    comp_kind: str = "league",
    shuffle_seed: Optional[int] = None,
) -> List[List[Dict]]:
    """
    Public helper expected by tests and other modules.

    Returns a list of weeks, where each week is a list of fixture dicts with keys:
      - week (1-based, starting at start_week)
      - home_id, away_id
      - played (False)
      - k_home, k_away (0)
      - winner (None)
      - comp_kind (str)
    """
    team_ids = list(range(int(n_teams)))
    flat = build_double_round_robin(team_ids, rounds=2, shuffle_seed=shuffle_seed)

    # Bucket by week (0-based -> 1-based with start offset)
    max_w = max((fx["week"] for fx in flat), default=-1)
    weeks: List[List[Dict]] = [[] for _ in range(max_w + 1)]
    for fx in flat:
        w0 = int(fx["week"])
        weeks[w0].append(
            {
                "id": fx["id"],
                "week": start_week + w0,
                "home_id": int(fx["home_id"]),
                "away_id": int(fx["away_id"]),
                "played": False,
                "k_home": 0,
                "k_away": 0,
                "winner": None,
                "comp_kind": comp_kind,
            }
        )
    return weeks
