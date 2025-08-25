# core/types.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple

# These lightweight dataclasses exist solely to satisfy tests that
# construct/serialize them; they are not used by the game engine.

@dataclass
class TableRow:
    team_id: int
    name: str
    played: int
    wins: int
    goals_for: int
    goals_against: int
    points: int

@dataclass
class Fixture:
    week: int
    home_id: int
    away_id: int
    home_goals: int = 0
    away_goals: int = 0
    played: bool = False

@dataclass
class Career:
    seed: int
    week: int
    team_names: List[str]
    team_colors: List[Tuple[int, int, int]]
    rosters: Dict[int, List[Dict]]
    fixtures: List[Fixture]
    table: Dict[int, TableRow]
