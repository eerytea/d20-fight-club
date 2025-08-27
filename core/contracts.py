from __future__ import annotations
from typing import TypedDict, Literal, Tuple, List, Dict, Any, Optional

# ---- Canonical shapes (our "shared language") ----

class FighterDict(TypedDict, total=False):
    pid: int
    name: str
    team_id: int            # 0 (home) or 1 (away)
    x: int
    y: int
    hp: int
    max_hp: int
    ac: int
    alive: bool
    role: str               # optional, e.g., "Bruiser", "Healer"
    xp: int
    STR: int; DEX: int; CON: int; INT: int; WIS: int; CHA: int

class FixtureDict(TypedDict, total=False):
    week: int               # 1-based
    home_id: int
    away_id: int
    played: bool
    k_home: int
    k_away: int
    winner: Optional[Literal[0,1]]  # None for draw/unplayed
    comp_kind: str          # e.g., "league", "cup"
    # friendly aliases (kept for older screens/data)
    home_tid: int
    away_tid: int
    A: int
    B: int

class MatchResultDict(TypedDict, total=False):
    home_id: int
    away_id: int
    k_home: int
    k_away: int
    winner: Optional[Literal[0,1]]

class StandingRow(TypedDict, total=False):
    tid: int
    name: str
    P: int; W: int; D: int; L: int
    K: int     # kills for
    KD: int    # kill diff
    PTS: int

class TypedEvent(TypedDict, total=False):
    type: Literal["round","move","hit","miss","down","blocked","end"]
    round: int
    name: str
    target: str
    dmg: int
    to: Tuple[int,int]
    at: Tuple[int,int]
    winner: Optional[Literal[0,1]]

# ---- Expected key sets (used by tests/adapters) ----

FIGHTER_KEYS_REQ = {"pid","name","team_id","hp","max_hp","ac","alive","STR","DEX","CON","INT","WIS","CHA"}
FIXTURE_KEYS_REQ = {"week","home_id","away_id","played","k_home","k_away","winner","comp_kind"}
RESULT_KEYS_REQ  = {"home_id","away_id","k_home","k_away","winner"}
STAND_ROW_KEYS   = {"tid","name","P","W","D","L","K","KD","PTS"}
EVENT_TYPES      = {"round","move","hit","miss","down","blocked","end"}

# Some aliases older code might still pass (adapters accept these)
FIGHTER_ALIASES = {"id":"pid","tid":"team_id","HP":"hp","HP_max":"max_hp","AC":"ac","tx":"x","ty":"y"}
FIXTURE_ALIASES = {"home_tid":"home_id","away_tid":"away_id","A":"home_id","B":"away_id"}
