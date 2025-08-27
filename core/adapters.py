from __future__ import annotations

from typing import Dict, Any, Optional, List, Tuple
from core.contracts import FighterDict, FixtureDict, MatchResult

# ---------- Fighter ----------

def as_fighter_dict(src: Any, default_team_id: int = 0, default_pid: Optional[int] = None) -> FighterDict:
    """
    Accepts dict, object, or dataclass and returns a canonical Fighter dict.
    Tolerant to keys: pid/id, team_id/tid/team, x/tx, y/ty, hp/HP, max_hp/HP_max, ac/AC, alive/is_alive, role/position.
    """
    d = dict(src) if isinstance(src, dict) else src.__dict__.copy()
    out: FighterDict = {}

    out["pid"] = int(d.get("pid", d.get("id", d.get("index", default_pid if default_pid is not None else 0))))
    out["name"] = str(d.get("name", d.get("n", f"U{out['pid']}")))
    out["team_id"] = int(d.get("team_id", d.get("tid", d.get("team", default_team_id))))
    out["x"] = int(d.get("x", d.get("tx", 0)))
    out["y"] = int(d.get("y", d.get("ty", 0)))
    out["hp"] = int(d.get("hp", d.get("HP", 10)))
    out["max_hp"] = int(d.get("max_hp", d.get("HP_max", out["hp"])))
    out["ac"] = int(d.get("ac", d.get("AC", 10)))
    out["alive"] = bool(d.get("alive", d.get("is_alive", True)))
    out["role"] = d.get("role", d.get("position"))
    # Keep any extra numeric stats (STR/DEX/etc.)
    for k, v in d.items():
        if k in out: 
            continue
        if isinstance(v, (int, float)) and k.isupper():
            out[k] = v
    return out

# ---------- Fixture / Result ----------

def as_fixture_dict(src: Any) -> FixtureDict:
    """
    Accepts dict or object and returns a canonical Fixture dict.
    Tolerant to keys: home_id/home_tid/home/A, away_id/away_tid/away/B, week/week_index(1-based fix).
    """
    if isinstance(src, dict):
        d = dict(src)
    else:
        d = src.__dict__.copy()

    week = d.get("week", d.get("week_index", 1))
    # If week_index looked 0-based, bump to 1-based
    try:
        week = int(week)
        if "week_index" in d and week == 0:
            week = 1
    except Exception:
        week = 1

    home = d.get("home_id", d.get("home_tid", d.get("home", d.get("A"))))
    away = d.get("away_id", d.get("away_tid", d.get("away", d.get("B")))

    )
    fx: FixtureDict = {
        "week": int(week),
        "home_id": int(home),
        "away_id": int(away),
        "played": bool(d.get("played", False)),
        "k_home": int(d.get("k_home", d.get("K_home", 0))),
        "k_away": int(d.get("k_away", d.get("K_away", 0))),
        "winner": d.get("winner", None),
        "comp_kind": d.get("comp_kind", d.get("competition", "league")),
    }
    # helper aliases many screens expect:
    fx["home_tid"] = fx["home_id"]
    fx["away_tid"] = fx["away_id"]
    fx["A"] = fx["home_id"]
    fx["B"] = fx["away_id"]
    return fx

def as_result_dict(src: Any) -> MatchResult:
    """
    Accepts dict or object and returns a canonical MatchResult dict.
    Same keys as Fixture, minimum of home/away IDs and k_home/k_away and winner.
    """
    d = as_fixture_dict(src)
    # Ensure required keys present
    for k in ("home_id", "away_id", "k_home", "k_away"):
        d[k] = int(d.get(k, 0))
    # winner can be 0/1/None; leave as-is
    return d

# ---------- Teams / Rosters ----------

def team_name_from(career: Any, tid: Any) -> str:
    """Safe name lookup used by UI; prefers career.team_name then teams list/dict."""
    if hasattr(career, "team_name"):
        try:
            return str(career.team_name(tid))
        except Exception:
            pass
    teams = getattr(career, "teams", None)
    if isinstance(teams, list):
        for t in teams:
            if str(t.get("tid", t.get("id"))) == str(tid):
                return t.get("name", f"Team {tid}")
    if isinstance(teams, dict):
        t = teams.get(str(tid)) or (teams.get(int(tid)) if str(tid).isdigit() else None)
        if t:
            return t.get("name", f"Team {tid}")
    return f"Team {tid}"

def roster_for_team(career: Any, tid: Any, team_slot: int) -> List[FighterDict]:
    """
    Get a team's fighter list normalized to FighterDicts.
    team_slot: 0 for home, 1 for away (sets team_id for the engine).
    """
    teams = getattr(career, "teams", [])
    for t in teams:
        if str(t.get("tid", t.get("id"))) == str(tid):
            roster = t.get("fighters") or t.get("players") or []
            out: List[FighterDict] = []
            for i, p in enumerate(roster):
                out.append(as_fighter_dict(p, default_team_id=team_slot, default_pid=i))
            return out
    return []
from __future__ import annotations

from typing import Dict, Any, Optional, List, Tuple
from core.contracts import FighterDict, FixtureDict, MatchResult

# ---------- Fighter ----------

def as_fighter_dict(src: Any, default_team_id: int = 0, default_pid: Optional[int] = None) -> FighterDict:
    """
    Accepts dict, object, or dataclass and returns a canonical Fighter dict.
    Tolerant to keys: pid/id, team_id/tid/team, x/tx, y/ty, hp/HP, max_hp/HP_max, ac/AC, alive/is_alive, role/position.
    """
    d = dict(src) if isinstance(src, dict) else src.__dict__.copy()
    out: FighterDict = {}

    out["pid"] = int(d.get("pid", d.get("id", d.get("index", default_pid if default_pid is not None else 0))))
    out["name"] = str(d.get("name", d.get("n", f"U{out['pid']}")))
    out["team_id"] = int(d.get("team_id", d.get("tid", d.get("team", default_team_id))))
    out["x"] = int(d.get("x", d.get("tx", 0)))
    out["y"] = int(d.get("y", d.get("ty", 0)))
    out["hp"] = int(d.get("hp", d.get("HP", 10)))
    out["max_hp"] = int(d.get("max_hp", d.get("HP_max", out["hp"])))
    out["ac"] = int(d.get("ac", d.get("AC", 10)))
    out["alive"] = bool(d.get("alive", d.get("is_alive", True)))
    out["role"] = d.get("role", d.get("position"))
    # Keep any extra numeric stats (STR/DEX/etc.)
    for k, v in d.items():
        if k in out: 
            continue
        if isinstance(v, (int, float)) and k.isupper():
            out[k] = v
    return out

# ---------- Fixture / Result ----------

def as_fixture_dict(src: Any) -> FixtureDict:
    """
    Accepts dict or object and returns a canonical Fixture dict.
    Tolerant to keys: home_id/home_tid/home/A, away_id/away_tid/away/B, week/week_index(1-based fix).
    """
    if isinstance(src, dict):
        d = dict(src)
    else:
        d = src.__dict__.copy()

    week = d.get("week", d.get("week_index", 1))
    # If week_index looked 0-based, bump to 1-based
    try:
        week = int(week)
        if "week_index" in d and week == 0:
            week = 1
    except Exception:
        week = 1

    home = d.get("home_id", d.get("home_tid", d.get("home", d.get("A"))))
    away = d.get("away_id", d.get("away_tid", d.get("away", d.get("B")))

    )
    fx: FixtureDict = {
        "week": int(week),
        "home_id": int(home),
        "away_id": int(away),
        "played": bool(d.get("played", False)),
        "k_home": int(d.get("k_home", d.get("K_home", 0))),
        "k_away": int(d.get("k_away", d.get("K_away", 0))),
        "winner": d.get("winner", None),
        "comp_kind": d.get("comp_kind", d.get("competition", "league")),
    }
    # helper aliases many screens expect:
    fx["home_tid"] = fx["home_id"]
    fx["away_tid"] = fx["away_id"]
    fx["A"] = fx["home_id"]
    fx["B"] = fx["away_id"]
    return fx

def as_result_dict(src: Any) -> MatchResult:
    """
    Accepts dict or object and returns a canonical MatchResult dict.
    Same keys as Fixture, minimum of home/away IDs and k_home/k_away and winner.
    """
    d = as_fixture_dict(src)
    # Ensure required keys present
    for k in ("home_id", "away_id", "k_home", "k_away"):
        d[k] = int(d.get(k, 0))
    # winner can be 0/1/None; leave as-is
    return d

# ---------- Teams / Rosters ----------

def team_name_from(career: Any, tid: Any) -> str:
    """Safe name lookup used by UI; prefers career.team_name then teams list/dict."""
    if hasattr(career, "team_name"):
        try:
            return str(career.team_name(tid))
        except Exception:
            pass
    teams = getattr(career, "teams", None)
    if isinstance(teams, list):
        for t in teams:
            if str(t.get("tid", t.get("id"))) == str(tid):
                return t.get("name", f"Team {tid}")
    if isinstance(teams, dict):
        t = teams.get(str(tid)) or (teams.get(int(tid)) if str(tid).isdigit() else None)
        if t:
            return t.get("name", f"Team {tid}")
    return f"Team {tid}"

def roster_for_team(career: Any, tid: Any, team_slot: int) -> List[FighterDict]:
    """
    Get a team's fighter list normalized to FighterDicts.
    team_slot: 0 for home, 1 for away (sets team_id for the engine).
    """
    teams = getattr(career, "teams", [])
    for t in teams:
        if str(t.get("tid", t.get("id"))) == str(tid):
            roster = t.get("fighters") or t.get("players") or []
            out: List[FighterDict] = []
            for i, p in enumerate(roster):
                out.append(as_fighter_dict(p, default_team_id=team_slot, default_pid=i))
            return out
    return []
