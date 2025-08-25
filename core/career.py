# core/career.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

from .config import (
    TEAM_SIZE,
    LEAGUE_TEAMS,
    ROUNDS_DOUBLE_ROUND_ROBIN,
    DEFAULT_SEED,
)
from .schedule import build_double_round_robin
from .standings import new_table, Table, H2HMap, sort_table


# --- Creation helpers ---------------------------------------------------------

_TEAM_NAMES = [
    "Alderfall Dragons", "Blackridge Wolves", "Stormbreak Griffins", "Titan's Gate",
    "Nightveil Phantoms", "Ironcrest Knights", "Ashmar Rangers", "Silvercoil Serpents",
    "Ravenmere", "Stoneheart Golems", "Starhaven Magi", "Shadowfen Stalkers",
    "Frostpeak Yetis", "Sunspire Paladins", "Redwater Raiders", "Moonveil Oracles",
    "Thornbarb Vipers", "Eaglecrest Sentinels", "Direbrook Bears", "Mirewatch Leeches",
    "Cinderforge Hammers", "Whisperwind Sylphs", "Grimhold Reapers", "Highspire Wardens",
]

def _default_team_name(i: int) -> str:
    return _TEAM_NAMES[i % len(_TEAM_NAMES)]

def _generate_teams(
    n: int,
    team_size: int,
    seed: int,
    provided_names: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    teams: List[Dict[str, Any]] = []

    try:
        from . import creator
        have_creator = hasattr(creator, "generate_team")
    except Exception:
        creator = None
        have_creator = False

    for tid in range(n):
        name = (provided_names[tid] if provided_names and tid < len(provided_names)
                else _default_team_name(tid))
        if have_creator:
            team = creator.generate_team(
                tid=tid,
                name=name,
                size=team_size,
                seed=seed + 31 * tid,
            )
        else:
            roster = []
            for slot in range(team_size):
                roster.append({
                    "fid": tid * 1000 + slot,
                    "name": f"{name} #{slot+1}",
                    "level": 1,
                    "class": "Fighter",
                    "hp": 10,
                    "ac": 12,
                    "speed": 6,
                    "ovr": 40 + (slot % 5),
                    "xp": 0,
                })
            team = {
                "tid": tid,
                "name": name,
                "color": (180, 180, 220),
                "budget": 1_000_000,
                "wage_bill": 0,
                "roster": roster,
            }

        team.setdefault("tid", tid)
        team.setdefault("name", name)
        team.setdefault("roster", [])
        teams.append(team)

    return teams


# --- Models -------------------------------------------------------------------

@dataclass
class Fixture:
    id: str
    week: int
    home_id: int
    away_id: int
    played: bool = False
    kills_home: int = 0
    kills_away: int = 0
    winner_tid: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "week": self.week,
            "home_id": self.home_id, "away_id": self.away_id,
            "played": self.played,
            "kills_home": self.kills_home, "kills_away": self.kills_away,
            "winner_tid": self.winner_tid,
        }

@dataclass
class Career:
    seed: int
    week: int
    teams: List[Dict[str, Any]]
    fixtures: List[Fixture]
    table: Table
    h2h: H2HMap
    user_team_id: Optional[int] = None

    # --- Construction ---------------------------------------------------------
    @classmethod
    def new(
        cls,
        seed: int = DEFAULT_SEED,
        n_teams: int = LEAGUE_TEAMS,
        team_size: int = TEAM_SIZE,
        user_team_id: Optional[int] = 0,
        team_names: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> "Career":
        # Accept alias used by tests
        if "team_count" in kwargs and kwargs["team_count"] is not None:
            n_teams = int(kwargs["team_count"])

        teams = _generate_teams(n_teams, team_size, seed, team_names)
        team_ids = [t["tid"] for t in teams]

        fixtures_dicts = build_double_round_robin(
            team_ids, rounds=ROUNDS_DOUBLE_ROUND_ROBIN, shuffle_seed=seed
        )
        fixtures = [Fixture(**f) for f in fixtures_dicts]

        table, h2h = new_table(team_ids)
        return cls(
            seed=seed,
            week=1,  # <-- start at Week 1 (tests expect this)
            teams=teams,
            fixtures=fixtures,
            table=table,
            h2h=h2h,
            user_team_id=user_team_id,
        )

    # --- Query helpers ---------------------------------------------------------
    def team_by_id(self, tid: int) -> Dict[str, Any]:
        return next(t for t in self.teams if t["tid"] == tid)

    def fixtures_in_week(self, week: Optional[int] = None) -> List[Fixture]:
        w = self.week if week is None else week
        return [fx for fx in self.fixtures if fx.week == w]

    def find_fixture(self, fixture_id: str) -> Fixture:
        return next(fx for fx in self.fixtures if fx.id == fixture_id)

    def user_fixture_this_week(self) -> Optional[Fixture]:
        if self.user_team_id is None:
            return None
        for fx in self.fixtures_in_week():
            if not fx.played and (fx.home_id == self.user_team_id or fx.away_id == self.user_team_id):
                return fx
        return None

    def remaining_unplayed_in_week(self, week: Optional[int] = None) -> List[Fixture]:
        return [fx for fx in self.fixtures_in_week(week) if not fx.played]

    def is_week_done(self, week: Optional[int] = None) -> bool:
        return all(fx.played for fx in self.fixtures_in_week(week))

    # --- Mutation --------------------------------------------------------------
    def record_result(self, fixture_id: str, kills_home: int, kills_away: int) -> None:
        fx = self.find_fixture(fixture_id)
        fx.kills_home = int(kills_home)
        fx.kills_away = int(kills_away)
        fx.played = True

        if kills_home > kills_away:
            fx.winner_tid = fx.home_id
        elif kills_away > kills_home:
            fx.winner_tid = fx.away_id
        else:
            fx.winner_tid = None

        from .standings import apply_result
        apply_result(self.table, self.h2h, fx.home_id, fx.away_id, fx.kills_home, fx.kills_away)

    def advance_week_if_done(self) -> None:
        if self.is_week_done(self.week):
            self.week += 1

    # --- Views for UI ----------------------------------------------------------
    def standings_sorted(self) -> List[Tuple[int, Dict[str, int]]]:
        return sort_table(self.table, self.h2h)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seed": self.seed,
            "week": self.week,
            "teams": self.teams,
            "fixtures": [fx.to_dict() for fx in self.fixtures],
            "table": self.table,
            "h2h": {f"{k[0]}_{k[1]}": v for k, v in self.h2h.items()},
            "user_team_id": self.user_team_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Career":
        fixtures = [Fixture(**fx) for fx in data.get("fixtures", [])]
        raw_h2h = data.get("h2h", {})
        h2h: H2HMap = {}
        for k, v in raw_h2h.items():
            a, b = k.split("_")
            h2h[(int(a), int(b))] = dict(v)
        return cls(
            seed=data.get("seed", DEFAULT_SEED),
            week=data.get("week", 1),
            teams=list(data.get("teams", [])),
            fixtures=fixtures,
            table=dict(data.get("table", {})),
            h2h=h2h,
            user_team_id=data.get("user_team_id"),
        )

# --- Back-compat convenience expected by tests --------------------------------

def new_career(
    seed: int = DEFAULT_SEED,
    n_teams: int = LEAGUE_TEAMS,
    team_size: int = TEAM_SIZE,
    user_team_id: Optional[int] = 0,
    team_names: Optional[List[str]] = None,
    **kwargs: Any,
) -> Career:
    if "team_count" in kwargs and kwargs["team_count"] is not None:
        n_teams = int(kwargs["team_count"])
    return Career.new(
        seed=seed,
        n_teams=n_teams,
        team_size=team_size,
        user_team_id=user_team_id,
        team_names=team_names,
    )
