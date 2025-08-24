# core/types.py
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple
import json

@dataclass
class Fixture:
    week: int
    home_id: int
    away_id: int
    home_goals: int | None = None
    away_goals: int | None = None
    played: bool = False

@dataclass
class TableRow:
    team_id: int
    name: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0

@dataclass
class Career:
    seed: int
    week: int
    team_names: List[str]
    team_colors: List[Tuple[int,int,int]]
    rosters: Dict[int, List[Dict]] = field(default_factory=dict)
    fixtures: List[Fixture] = field(default_factory=list)
    table: Dict[int, TableRow] = field(default_factory=dict)

    def to_json(self) -> str:
        payload = {
            "seed": self.seed,
            "week": self.week,
            "team_names": self.team_names,
            "team_colors": self.team_colors,
            "rosters": self.rosters,
            "fixtures": [asdict(f) for f in self.fixtures],
            "table": {k: asdict(v) for k, v in self.table.items()},
        }
        return json.dumps(payload, indent=2)

    @staticmethod
    def from_json(s: str) -> "Career":
        obj = json.loads(s)
        fixtures = [Fixture(**f) for f in obj["fixtures"]]
        table = {int(k): TableRow(**v) for k, v in obj["table"].items()}
        return Career(
            seed=obj["seed"],
            week=obj["week"],
            team_names=obj["team_names"],
            team_colors=[tuple(c) for c in obj["team_colors"]],
            rosters=obj["rosters"],
            fixtures=fixtures,
            table=table,
        )
