from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Tuple, List, Iterable, Optional
from datetime import date
import math

# --- Reputation / Rankings (Elo-like) ---------------------------------------

class RepTable(Enum):
    NATIONAL = auto()      # countries' national teams
    CLUB = auto()          # clubs
    RACE = auto()          # race national teams
    # LEAGUE and ASSOCIATION are computed on demand from CLUB table


@dataclass
class EloConfig:
    base_k: float = 20.0
    # Competition importance weights (similar spirit to FIFA Elo)
    weights: Dict[str, float] = field(default_factory=lambda: {
        "friendly": 0.5,
        "league": 1.0,
        "playoff": 1.2,
        "cup": 1.5,
        "continental": 1.7,
        "world_cup": 2.5,  # Nations / Race Cup finals
    })
    start_rating: float = 1500.0
    half_life_days: Optional[int] = 1460  # ~4 years; set None to disable decay
    home_advantage_elo: float = 60.0      # optional; if you model home/away


@dataclass
class Reputation:
    """Holds Elo tables and provides helpers for aggregate coefficients."""
    config: EloConfig = field(default_factory=EloConfig)
    # Each table maps key -> (rating, last_update_date)
    tables: Dict[RepTable, Dict[str, Tuple[float, date]]] = field(default_factory=lambda: {
        RepTable.NATIONAL: {},
        RepTable.CLUB: {},
        RepTable.RACE: {},
    })

    def _get_raw(self, table: RepTable, key: str) -> Tuple[float, date]:
        t = self.tables.setdefault(table, {})
        if key not in t:
            today = date.today()
            t[key] = (self.config.start_rating, today)
        return t[key]

    def _with_decay(self, rating: float, last: date, today: date) -> float:
        if self.config.half_life_days is None:
            return rating
        dt = max(0, (today - last).days)
        if dt == 0:
            return rating
        lam = math.log(2) / float(self.config.half_life_days)
        return 1500.0 + (rating - 1500.0) * math.exp(-lam * dt)

    def get(self, table: RepTable, key: str, today: Optional[date] = None) -> float:
        if today is None:
            today = date.today()
        r, last = self._get_raw(table, key)
        return self._with_decay(r, last, today)

    def expected_score(self, ra: float, rb: float) -> float:
        return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))

    def record_match(
        self,
        table: RepTable,
        a: str,
        b: str,
        goals_a: int,
        goals_b: int,
        comp_kind: str,
        when: Optional[date] = None,
        home_advantage: Optional[str] = None,  # 'a', 'b', or None
    ) -> Tuple[float, float]:
        if when is None:
            when = date.today()
        w = self.config.weights.get(comp_kind, 1.0)
        k = self.config.base_k * w

        ra = self.get(table, a, when)
        rb = self.get(table, b, when)

        # optional home advantage tweak
        if home_advantage == 'a':
            ra_eff, rb_eff = ra + self.config.home_advantage_elo, rb
        elif home_advantage == 'b':
            ra_eff, rb_eff = ra, rb + self.config.home_advantage_elo
        else:
            ra_eff, rb_eff = ra, rb

        ea = self.expected_score(ra_eff, rb_eff)
        eb = 1.0 - ea

        if goals_a > goals_b:
            sa, sb = 1.0, 0.0
        elif goals_a < goals_b:
            sa, sb = 0.0, 1.0
        else:
            sa, sb = 0.5, 0.5

        margin = abs(goals_a - goals_b)
        mboost = 1.0 + 0.1 * min(3, margin)  # cap at +30%

        na = ra + k * mboost * (sa - ea)
        nb = rb + k * mboost * (sb - eb)

        self.tables.setdefault(table, {})[a] = (na, when)
        self.tables.setdefault(table, {})[b] = (nb, when)
        return na, nb

    # --- Aggregates ----------------------------------------------------------

    def league_coefficient(self, league_id: str, club_ids: Iterable[str], today: Optional[date] = None) -> float:
        if today is None:
            today = date.today()
        ratings = sorted([self.get(RepTable.CLUB, cid, today) for cid in club_ids], reverse=True)
        if not ratings:
            return 1500.0
        weights: List[float] = []
        for i in range(len(ratings)):
            if i < 5:
                weights.append(1.0 - 0.1 * i)  # 1.0, 0.9, 0.8, 0.7, 0.6
            else:
                weights.append(0.5)
        num = sum(r * weights[i] for i, r in enumerate(ratings))
        den = sum(weights[:len(ratings)]) or 1.0
        return num / den

    def association_coefficient(self, country_id: str, club_ids: Iterable[str], today: Optional[date] = None) -> float:
        if today is None:
            today = date.today()
        ratings = [self.get(RepTable.CLUB, cid, today) for cid in club_ids]
        if not ratings:
            return 1500.0
        top = sorted(ratings, reverse=True)[:10]
        return sum(top) / len(top)

    def table_sorted(self, table: RepTable, today: Optional[date] = None) -> List[Tuple[str, float]]:
        if today is None:
            today = date.today()
        t = self.tables.get(table, {})
        pairs = [(k, self.get(table, k, today)) for k in t.keys()]
        return sorted(pairs, key=lambda x: x[1], reverse=True)

    def to_dict(self) -> Dict:
        out: Dict[str, Dict[str, Tuple[float, str]]] = {}
        for table, mapping in self.tables.items():
            out[table.name] = {k: (float(r), d.isoformat()) for k, (r, d) in mapping.items()}
        return out

    @classmethod
    def from_dict(cls, data: Dict) -> "Reputation":
        rep = cls()
        rep.tables = {}
        for table_name, mapping in data.items():
            tkey = RepTable[table_name]
            rep.tables[tkey] = {k: (float(r), date.fromisoformat(ds)) for k, (r, ds) in mapping.items()}
        return rep
