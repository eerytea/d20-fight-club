# core/save_system.py
# Career save/load, schedule, table, and week simulation.
# Use full TBCombat for AI week sims
try:
    from engine import TBCombat, Team, fighter_from_dict, layout_teams_tiles
except Exception:
    TBCombat = Team = fighter_from_dict = layout_teams_tiles = None

from __future__ import annotations
import json, os, random
from typing import Dict, List, Tuple, Optional

from .creator import generate_team
from .ratings import refresh_fighter_ratings

# ------------ Helpers ------------

def _ensure_dir(p: str) -> None:
    os.makedirs(os.path.dirname(p), exist_ok=True)

def _round_robin_pairings(team_ids: List[str]) -> List[List[Tuple[str, str]]]:
    """
    Circle method, single round robin (no home/away swap).
    Returns a list of rounds; each round is a list of (home, away) tuples.
    """
    teams = team_ids[:]
    if len(teams) % 2 == 1:
        teams.append("__BYE__")
    n = len(teams)
    rounds = []
    # split
    l = teams[: n // 2]
    r = teams[n // 2 :]
    r.reverse()
    for _round in range(n - 1):
        pairings = []
        for i in range(n // 2):
            a, b = l[i], r[i]
            if "__BYE__" not in (a, b):
                pairings.append((a, b))  # a = home, b = away
        rounds.append(pairings)
        # rotate
        l1 = [l[0]] + [r[0]] + l[1:-0 or None]
        r1 = r[1:] + [l[-1]]
        l, r = l1, r1
    return rounds

def _team_avg_ovr(team: Dict) -> float:
    if not team["fighters"]:
        return 50.0
    return sum(f.get("ovr", 50) for f in team["fighters"]) / len(team["fighters"])

# ------------ Career object ------------

class Career:
    def __init__(self):
        self.team_ids: List[str] = []
        self.teams: Dict[str, Dict] = {}           # tid -> team dict
        self.table: Dict[str, Dict] = {}           # tid -> standings row
        self.fixtures: Dict[str, List[Dict]] = {}  # "S{season}W{week}" -> list of fixtures
        self.date = {"season": 1, "week": 1}
        self.season_meta = {"total_weeks": 0}
        self.random_seed = random.randint(1, 10_000_000)
        self.league_economy = 1.0

    # ---------- Creation / Schedule ----------

    @classmethod
    def create_random_league(cls, num_teams: int, fighters_per_team: int, seed: Optional[int] = None) -> "Career":
        rng = random.Random(seed)
        c = cls()
        c.random_seed = seed if seed is not None else c.random_seed

        # Make teams
        for i in range(num_teams):
            tid = f"T{i+1:02d}"
            name = f"Club {i+1}"
            color = (120 + (i*37) % 120, 80 + (i*53) % 120, 140 + (i*23) % 100)
            team = generate_team(name, tid, color=color, size=fighters_per_team, level=1, rng=rng)
            # assign player IDs
            for j, f in enumerate(team["fighters"], start=1):
                f["pid"] = f"P{tid}{j:02d}"
                refresh_fighter_ratings(f, league_economy=c.league_economy)
            c.teams[tid] = team
            c.team_ids.append(tid)
            c.table[tid] = {"P": 0, "W": 0, "D": 0, "L": 0, "PF": 0, "PA": 0, "PTS": 0}

        c.generate_season_schedule(c.date["season"])
        return c

    def generate_season_schedule(self, season: int) -> None:
        """Single round-robin season; total weeks = len(team_ids)-1."""
        rounds = _round_robin_pairings(self.team_ids)
        total_weeks = max(1, len(rounds))
        self.season_meta["total_weeks"] = total_weeks
        for week, matches in enumerate(rounds, start=1):
            key = f"S{season}W{week}"
            self.fixtures[key] = [{"home": h, "away": a, "result": None} for (h, a) in matches]

    def ensure_schedule(self) -> None:
        season = self.date["season"]
        if not any(k.startswith(f"S{season}W") for k in self.fixtures.keys()):
            self.generate_season_schedule(season)

    # ---------- Query / Seeds ----------

    def next_fixture_for_team(self, tid: str) -> Optional[Dict]:
        season, week = self.date["season"], self.date["week"]
        key = f"S{season}W{week}"
        for fx in self.fixtures.get(key, []):
            if tid in (fx["home"], fx["away"]):
                return fx
        return None

    def get_team(self, tid: str) -> Dict:
        return self.teams[tid]

    def match_seed(self, season: int, week: int, tidA: str, tidB: str) -> int:
        # deterministic seed per match
        base = self.random_seed or 1
        s = f"{base}-{season}-{week}-{tidA}-{tidB}"
        return abs(hash(s)) % 2_147_483_647

    # ---------- Recording / Table ----------

    def record_result(self, season: int, week: int, home_tid: str, away_tid: str, result: Dict) -> None:
        """
        result: {"winner": "home"|"away"|"draw", "home_hp": int, "away_hp": int}
        Updates fixture and table.
        """
        key = f"S{season}W{week}"
        for fx in self.fixtures.get(key, []):
            if fx["home"] == home_tid and fx["away"] == away_tid:
                if fx["result"] is not None:
                    return
                fx["result"] = dict(result)
                # Update table
                self._apply_to_table(home_tid, away_tid, result)
                return

    def _apply_to_table(self, home_tid: str, away_tid: str, res: Dict) -> None:
        th, ta = self.table[home_tid], self.table[away_tid]
        th["P"] += 1; ta["P"] += 1
        hh, aa = int(res.get("home_hp", 0)), int(res.get("away_hp", 0))
        th["PF"] += hh; th["PA"] += aa
        ta["PF"] += aa; ta["PA"] += hh

        if res.get("winner") == "home":
            th["W"] += 1; th["PTS"] += 3
            ta["L"] += 1
        elif res.get("winner") == "away":
            ta["W"] += 1; ta["PTS"] += 3
            th["L"] += 1
        else:
            th["D"] += 1; ta["D"] += 1
            th["PTS"] += 1; ta["PTS"] += 1

    # ---------- Week tick ----------

    def tick_week(self) -> None:
        """Advance to next week; if past end, start a fresh season with new schedule and reset table."""
        self.date["week"] += 1
        if self.date["week"] > self.season_meta.get("total_weeks", 38):
            # new season
            self.date["season"] += 1
            self.date["week"] = 1
            # reset table
            for tid in self.team_ids:
                self.table[tid] = {"P": 0, "W": 0, "D": 0, "L": 0, "PF": 0, "PA": 0, "PTS": 0}
            # new schedule
            self.generate_season_schedule(self.date["season"])

    # ---------- Serialization ----------

    def to_dict(self) -> Dict:
        return {
            "team_ids": self.team_ids,
            "teams": self.teams,
            "table": self.table,
            "fixtures": self.fixtures,
            "date": self.date,
            "season_meta": self.season_meta,
            "random_seed": self.random_seed,
            "league_economy": self.league_economy,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "Career":
        c = cls()
        c.team_ids = d["team_ids"]
        c.teams = d["teams"]
        c.table = d["table"]
        c.fixtures = d["fixtures"]
        c.date = d["date"]
        c.season_meta = d.get("season_meta", {"total_weeks": 38})
        c.random_seed = d.get("random_seed", random.randint(1, 10_000_000))
        c.league_economy = float(d.get("league_economy", 1.0))

        # Back-compat: ensure fighters have derived ratings
        for tid in c.team_ids:
            for f in c.teams[tid]["fighters"]:
                refresh_fighter_ratings(f, league_economy=c.league_economy)
        return c

# ------------ Save/Load ------------

def save_career(path: str, career: Career) -> None:
    _ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(career.to_dict(), f, indent=2)

def load_career(path: str) -> Career:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    return Career.from_dict(d)

# ------------ Quick Sim (AI weeks) ------------

def _quick_sim_match(team_home: Dict, team_away: Dict, seed: int) -> Dict:
    """
    Very fast sim using team OVRs; returns result dict for record_result.
    """
    rng = random.Random(seed)
    ovr_h = _team_avg_ovr(team_home)
    ovr_a = _team_avg_ovr(team_away)
    # Home edge + variance
    edge = (ovr_h - ovr_a) * 0.015 + 0.5  # map diff into ~0.35..0.65 range
    edge = max(0.25, min(0.75, edge))
    roll = rng.random()
    # Produce pseudo "HP remaining" so PF/PA feel like scores
    base_hp = 40
    var = rng.randint(-8, 8)
    if roll < edge - 0.05:
        # home win
        home_hp = base_hp + max(0, int((ovr_h - 60) * 0.6)) + var
        away_hp = rng.randint(0, max(8, int(home_hp * 0.6)))
        return {"winner": "home", "home_hp": max(1, home_hp), "away_hp": max(0, away_hp)}
    elif roll > edge + 0.05:
        # away win
        away_hp = base_hp + max(0, int((ovr_a - 60) * 0.6)) + var
        home_hp = rng.randint(0, max(8, int(away_hp * 0.6)))
        return {"winner": "away", "home_hp": max(0, home_hp), "away_hp": max(1, away_hp)}
    else:
        # draw-ish
        hp = base_hp // 2 + var // 2
        return {"winner": "draw", "home_hp": max(0, hp), "away_hp": max(0, hp)}

def _run_full_engine_match(team_home: dict, team_away: dict, seed: int) -> dict:
    """
    Headless match using full TBCombat. Returns result dict for record_result.
    """
    if TBCombat is None:
        # fallback if engine isn't available
        return {"winner": "draw", "home_hp": 10, "away_hp": 10}

    tH = Team(0, team_home["name"], tuple(team_home.get("color", (120,180,255))))
    tA = Team(1, team_away["name"], tuple(team_away.get("color", (255,140,140))))

    fighters = []
    for fd in team_home["fighters"]:
        fighters.append(fighter_from_dict({**fd, "team_id": 0}))
    for fd in team_away["fighters"]:
        fighters.append(fighter_from_dict({**fd, "team_id": 1}))

    GRID_W, GRID_H = 18, 12
    layout_teams_tiles(fighters, GRID_W, GRID_H)

    combat = TBCombat(tH, tA, fighters, GRID_W, GRID_H, seed=seed)

    turns = 0
    while combat.winner is None and turns < 2000:
        combat.take_turn()
        turns += 1

    home_hp = sum(max(0, f.hp) for f in combat.fighters if f.team_id == 0 and f.alive)
    away_hp = sum(max(0, f.hp) for f in combat.fighters if f.team_id == 1 and f.alive)

    if combat.winner == 0: winner = "home"
    elif combat.winner == 1: winner = "away"
    else: winner = "draw"

    return {"winner": winner, "home_hp": home_hp, "away_hp": away_hp}

def simulate_week_ai(career: Career) -> None:
    """
    Simulate all UNPLAYED fixtures for the current week using full TBCombat.
    """
    season, week = career.date["season"], career.date["week"]
    key = f"S{season}W{week}"
    fixtures = career.fixtures.get(key, [])
    for fx in fixtures:
        if fx["result"] is not None:
            continue
        h, a = fx["home"], fx["away"]
        team_h, team_a = career.get_team(h), career.get_team(a)
        seed = career.match_seed(season, week, h, a)
        res = _run_full_engine_match(team_h, team_a, seed)
        career.record_result(season, week, h, a, res)
