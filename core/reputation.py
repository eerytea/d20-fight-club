from __future__ import annotations
from typing import Dict, Any, List, Tuple

START_RATING = 1500.0
K_FACTOR = 24.0
HOME_BONUS = 50.0  # Elo points treated as home-advantage

def _mix(seed: int, text: str) -> int:
    x = (seed ^ 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    for b in text.encode("utf-8"):
        x ^= (b + 0x9E3779B97F4A7C15 + ((x << 6) & 0xFFFFFFFFFFFFFFFF) + (x >> 2))
        x &= 0xFFFFFFFFFFFFFFFF
    return x

def ensure_tables(career, teams: List[Dict[str, Any]] | None = None) -> None:
    """
    Create/normalize career.reputation with buckets:
      - 'clubs': {club_id: rating}
      - 'nations': {nation_id: rating}
      - 'races': {race_id: rating}
    """
    rep = getattr(career, "reputation", None)
    if rep is None or not isinstance(rep, dict):
        rep = {}
        setattr(career, "reputation", rep)
    rep.setdefault("clubs", {})
    rep.setdefault("nations", {})
    rep.setdefault("races", {})

    # Initialize clubs from teams list if provided
    if teams:
        for t in teams:
            tid = str(t.get("tid", t.get("id")))
            if tid not in rep["clubs"]:
                rep["clubs"][tid] = START_RATING


# ----------------- Elo helpers -----------------

def _expected(ra: float, rb: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))

def _update(ra: float, rb: float, score_a: float, k: float = K_FACTOR) -> Tuple[float, float]:
    ea = _expected(ra, rb)
    eb = 1.0 - ea
    ra2 = ra + k * (score_a - ea)
    rb2 = rb + k * ((1.0 - score_a) - eb)
    return ra2, rb2


# ----------------- Public: Club matches -----------------

def record_club_match(
    career,
    home_tid: str,
    away_tid: str,
    k_home: int,
    k_away: int,
    home_boost: bool = True,
) -> None:
    """
    Update Elo for a club match result using kills as outcome proxy:
      win  -> score = 1.0
      draw -> score = 0.5
      loss -> score = 0.0
    Home-side gains a small Elo bonus if home_boost=True.
    """
    ensure_tables(career)
    clubs = career.reputation["clubs"]

    ra = float(clubs.get(home_tid, START_RATING))
    rb = float(clubs.get(away_tid, START_RATING))

    if home_boost:
        ra_eff = ra + HOME_BONUS
        rb_eff = rb
    else:
        ra_eff = ra; rb_eff = rb

    if k_home > k_away:
        score_a = 1.0
    elif k_home < k_away:
        score_a = 0.0
    else:
        score_a = 0.5

    ra2, rb2 = _update(ra_eff, rb_eff, score_a, k=K_FACTOR)
    # Remove the synthetic bonus from stored rating (bonus only affected expectation)
    if home_boost:
        ra2 -= HOME_BONUS

    clubs[home_tid] = ra2
    clubs[away_tid] = rb2


# ----------------- Tables for UI -----------------

def table(kind: str, career) -> List[Tuple[str, float]]:
    """
    Return a sorted list [(id, rating), ...] high → low.
    kind in {'clubs','nations','races'}
    """
    ensure_tables(career)
    bucket = career.reputation.get(kind, {})
    items = list(bucket.items())
    items.sort(key=lambda kv: kv[1], reverse=True)
    return items
