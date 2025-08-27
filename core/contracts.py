from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Literal, List, Tuple

# --------- Canonical keys (use these names everywhere) ---------

# Fighter keys (dicts or dataclass-as-dict)
# pid:int, name:str, team_id:int(0/1), x:int, y:int, hp:int, max_hp:int, ac:int, alive:bool, role?:str
FighterDict = Dict[str, Any]

# Fixture / Result keys (week is 1-based)
# {"week": int, "home_id": int, "away_id": int, "played": bool,
#  "k_home": int, "k_away": int, "winner": 0|1|None, "comp_kind": str}
FixtureDict = Dict[str, Any]
MatchResult = Dict[str, Any]

# Standings row
# {"tid","name","P","W","D","L","K","KD","PTS"}
StandingRow = Dict[str, Any]

# Typed events allowed in combat log
EventType = Literal["round", "move", "hit", "miss", "down", "blocked", "end"]
TypedEvent = Dict[str, Any]


# --------- Optional dataclasses (you can use plain dicts too) ---------

@dataclass
class Fighter:
    pid: int
    name: str
    team_id: int
    x: int = 0
    y: int = 0
    hp: int = 10
    max_hp: int = 10
    ac: int = 10
    alive: bool = True
    role: Optional[str] = None
    # extra stats are OK; keep them on a side dict if you like

    def as_dict(self) -> FighterDict:
        return asdict(self)


@dataclass
class Fixture:
    week: int
    home_id: int
    away_id: int
    played: bool = False
    k_home: int = 0
    k_away: int = 0
    winner: Optional[int] = None  # 0=home, 1=away, None=draw
    comp_kind: str = "league"

    def as_dict(self) -> FixtureDict:
        d = asdict(self)
        # Keep alias names some screens expect:
        d["home_tid"] = d["home_id"]
        d["away_tid"] = d["away_id"]
        d["A"] = d["home_id"]
        d["B"] = d["away_id"]
        return d
