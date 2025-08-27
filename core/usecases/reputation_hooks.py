from __future__ import annotations

from typing import Optional
from datetime import date
from core.reputation import Reputation, RepTable

def ensure_reputation(store) -> Reputation:
    rep: Optional[Reputation] = getattr(store, "reputation", None)
    if rep is None:
        rep = Reputation()
        setattr(store, "reputation", rep)
    return rep

def record_club_match(store, club_a_id: str, club_b_id: str, goals_a: int, goals_b: int,
                      comp_kind: str = "league", when: Optional[date] = None,
                      home_advantage: Optional[str] = None) -> None:
    rep = ensure_reputation(store)
    rep.record_match(RepTable.CLUB, club_a_id, club_b_id, goals_a, goals_b, comp_kind, when, home_advantage)

def record_national_match(store, country_a_id: str, country_b_id: str, goals_a: int, goals_b: int,
                          comp_kind: str = "world_cup", when: Optional[date] = None,
                          neutral: bool = True) -> None:
    rep = ensure_reputation(store)
    rep.record_match(RepTable.NATIONAL, country_a_id, country_b_id, goals_a, goals_b, comp_kind, when, None if neutral else 'a')

def record_race_match(store, race_a_id: str, race_b_id: str, goals_a: int, goals_b: int,
                      comp_kind: str = "world_cup", when: Optional[date] = None,
                      neutral: bool = True) -> None:
    rep = ensure_reputation(store)
    rep.record_match(RepTable.RACE, race_a_id, race_b_id, goals_a, goals_b, comp_kind, when, None if neutral else 'a')
