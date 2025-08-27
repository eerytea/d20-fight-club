from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional

from core.contracts import (
    FighterDict, FixtureDict, MatchResultDict, StandingRow, TypedEvent,
    FIGHTER_KEYS_REQ, FIXTURE_KEYS_REQ, RESULT_KEYS_REQ,
    FIGHTER_ALIASES, FIXTURE_ALIASES,
)

# ---------- Fighter ----------

def as_fighter_dict(p: Any, default_team_id: int = 0, default_pid: int = 0) -> FighterDict:
    """
    Accepts dict or object; returns a FighterDict with canonical keys and safe defaults.
    """
    d: Dict[str, Any] = dict(p) if isinstance(p, dict) else p.__dict__.copy()
    # apply common aliases
    for src, dst in FIGHTER_ALIASES.items():
        if src in d and dst not in d:
            d[dst] = d[src]

    out: FighterDict = {
        "pid": int(d.get("pid", d.get("id", default_pid))),
        "name": str(d.get("name", d.get("n", f"P{default_pid}"))),
        "team_id": int(d.get("team_id", d.get("tid", default_team_id))),
        "x": int(d.get("x", d.get("tx", 0))),
        "y": int(d.get("y", d.get("ty", 0))),
        "hp": int(d.get("hp", d.get("HP", 10))),
        "max_hp": int(d.get("max_hp", d.get("HP_max", d.get("hp", 10)))),
        "ac": int(d.get("ac", d.get("AC", 10))),
        "alive": bool(d.get("alive", d.get("is_alive", True))),
        "role": str(d.get("role", d.get("position", ""))),
        "xp": int(d.get("xp", d.get("XP", 0))),
        "STR": int(d.get("STR", 10)),
        "DEX": int(d.get("DEX", 10)),
        "CON": int(d.get("CON", 10)),
        "INT": int(d.get("INT", 8)),
        "WIS": int(d.get("WIS", 8)),
        "CHA": int(d.get("CHA", 8)),
    }
    return out

def roster_for_team(career, tid: int, team_slot: int) -> List[FighterDict]:
    """
    Build a normalized roster for a team id.
    team_slot: 0 for home, 1 for away (sets team_id for engine).
    """
    team = next((t for t in getattr(career, "teams", []) if str(t.get("tid", t.get("id"))) == str(tid)), None)
    roster = team.get("fighters", []) if team else []
    return [as_fighter_dict(p, default_team_id=team_slot, default_pid=i) for i, p in enumerate(roster)]

# ---------- Fixture / Result ----------

def as_fixture_dict(fx: Any) -> FixtureDict:
    d: Dict[str, Any] = dict(fx) if isinstance(fx, dict) else fx.__dict__.copy()
    # apply fixture aliases
    for src, dst in FIXTURE_ALIASES.items():
        if src in d and dst not in d:
            d[dst] = d[src]
    out: FixtureDict = {
        "week": int(d.get("week", 1)),
        "home_id": int(d.get("home_id", d.get("home_tid", d.get("A", 0)))),
        "away_id": int(d.get("away_id", d.get("away_tid", d.get("B", 1)))),
        "played": bool(d.get("played", False)),
        "k_home": int(d.get("k_home", 0)),
        "k_away": int(d.get("k_away", 0)),
        "winner": d.get("winner", None),
        "comp_kind": str(d.get("comp_kind", "league")),
    }
    # keep friendly aliases for UI that still read them
    out["home_tid"] = out["home_id"]
    out["away_tid"] = out["away_id"]
    out["A"] = out["home_id"]
    out["B"] = out["away_id"]
    return out

def as_result_dict(r: Any) -> MatchResultDict:
    d: Dict[str, Any] = dict(r) if isinstance(r, dict) else r.__dict__.copy()
    out: MatchResultDict = {
        "home_id": int(d.get("home_id", d.get("home_tid", d.get("A", 0)))),
        "away_id": int(d.get("away_id", d.get("away_tid", d.get("B", 1)))),
        "k_home": int(d.get("k_home", 0)),
        "k_away": int(d.get("k_away", 0)),
        "winner": d.get("winner", None),
    }
    return out

def flatten_fixtures(fixtures_by_week: List[List[Any]]) -> List[FixtureDict]:
    out: List[FixtureDict] = []
    for wk in fixtures_by_week:
        for fx in wk:
            out.append(as_fixture_dict(fx))
    return out

# ---------- Standings helpers ----------

def team_name_from(career, tid: Any) -> str:
    tid_i = int(tid)
    for t in getattr(career, "teams", []):
        if int(t.get("tid", t.get("id", -999))) == tid_i:
            return t.get("name", f"Team {tid_i}")
    tn = getattr(career, "team_names", None)
    if isinstance(tn, dict) and tid_i in tn:
        return str(tn[tid_i])
    return f"Team {tid_i}"

# ---------- Events (optional normalization) ----------

def as_event_dict(e: Any) -> Dict[str, Any]:
    """
    Tolerant event normalizer; returns dict with at least a 'type' key and known fields if present.
    """
    d: Dict[str, Any] = dict(e) if isinstance(e, dict) else e.__dict__.copy()
    t = str(d.get("type", ""))
    out: Dict[str, Any] = {"type": t}
    for k in ("round","name","target","dmg","to","at","winner"):
        if k in d:
            out[k] = d[k]
    return out
