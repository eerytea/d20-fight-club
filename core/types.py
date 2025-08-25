# core/types.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple
import json

# Lightweight dataclasses used by tests (not the game engine).

@dataclass
class TableRow:
    team_id: int
    name: str
    played: int
    wins: int
    goals_for: int
    goals_against: int
    points: int

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, s: str) -> "TableRow":
        return cls(**json.loads(s))

@dataclass
class Fixture:
    week: int
    home_id: int
    away_id: int
    home_goals: int = 0
    away_goals: int = 0
    played: bool = False

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, s: str) -> "Fixture":
        return cls(**json.loads(s))

@dataclass
class Career:
    seed: int
    week: int
    team_names: List[str]
    team_colors: List[Tuple[int, int, int]]
    rosters: Dict[int, List[Dict]]
    fixtures: List[Fixture]
    table: Dict[int, TableRow]

    def to_json(self) -> str:
        # Convert nested dataclasses to dicts
        d = asdict(self)
        return json.dumps(d)

    @classmethod
    def from_json(cls, s: str) -> "Career":
        d = json.loads(s)
        d["fixtures"] = [Fixture(**fx) for fx in d.get("fixtures", [])]
        d["table"] = {int(k): TableRow(**v) for k, v in d.get("table", {}).items()}
        return cls(**d)
