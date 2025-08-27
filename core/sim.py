from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple
import random
from datetime import date

# weekly training hook
try:
    from core.usecases.integration_points import weekly_training_tick
except Exception:
    def weekly_training_tick(*a, **k):  # graceful no-op
        pass

# Engine for headless sims
try:
    from engine.tbcombat import TBCombat
except Exception:
    TBCombat = None  # if you only record results externally

# ---------- helpers to read fixtures ----------

def _current_week_index(career) -> int:
    if hasattr(career, "week_index"):
        try:
            return max(0, int(getattr(career, "week_index")))
        except Exception:
            pass
    try:
        return max(0, int(getattr(career, "week", 1)) - 1)
    except Exception:
        return 0

def _fixtures_for_week(career, week_index: int) -> List[Tuple[Any, Any]]:
    fx_by_week = getattr(career, "fixtures_by_week", None) or getattr(career, "rounds", None)
    if isinstance(fx_by_week, list) and 0 <= week_index < len(fx_by_week):
        week = fx_by_week[week_index]
        out = []
        for p in week:
            if isinstance(p, dict):
                a = p.get("home_id") or p.get("home_tid") or p.get("home") or p.get("A")
                b = p.get("away_id") or p.get("away_tid") or p.get("away") or p.get("B")
                out.append((a, b))
            elif isinstance(p, (list, tuple)) and len(p) >= 2:
                out.append((p[0], p[1]))
        return out
    fx = getattr(career, "fixtures", None) or getattr(career, "schedule", None)
    if isinstance(fx, list):
        out = []
        for m in fx:
            w = m.get("week") if isinstance(m, dict) else getattr(m, "week", None)
            if w is None:
                continue
            if int(w) - 1 == week_index or int(w) == week_index:
                if isinstance(m, dict):
                    a = m.get("home_id") or m.get("home_tid") or m.get("home") or m.get("A")
                    b = m.get("away_id") or m.get("away_tid") or m.get("away") or m.get("B")
                else:
                    a = getattr(m, "home_id", getattr(m, "home_tid", getattr(m, "home", getattr(m, "A", None))))
                    b = getattr(m, "away_id", getattr(m, "away_tid", getattr(m, "away", getattr(m, "B", None))))
                out.append((a, b))
        if out:
            return out
    return []

def _team_roster(career, tid) -> List[Dict]:
    teams = getattr(career, "teams", [])
    for t in teams:
        if str(t.get("tid", t.get("id"))) == str(tid):
            roster = t.get("fighters") or t.get("players") or []
            out = []
            for i, p in enumerate(roster):
                d = dict(p) if isinstance(p, dict) else p.__dict__.copy()
                d.setdefault("pid", d.get("id", i))
                d["team_id"] = 0  # caller will override for away
                d.setdefault("name", d.get("n", f"F{i}"))
                d.setdefault("hp", d.get("hp", d.get("HP", 10)))
                d.setdefault("max_hp", d.get("max_hp", d.get("HP_max", d.get("hp", 10))))
                d.setdefault("ac", d.get("ac", d.get("AC", 10)))
                d.setdefault("alive", d.get("alive", True))
                out.append(d)
            return out
    return []

def _record_result(career, result: Dict[str, Any]) -> None:
    # Try a few adapters on career
    for name in ("record_result", "save_match_result", "apply_result"):
        fn = getattr(career, name, None)
        if callable(fn):
            try:
                fn(result)
                return
            except Exception:
                pass
    # Otherwise, you may be storing into an internal table; as a safe default do nothing.

def _advance_week(career) -> None:
    for name in ("advance_week", "next_week"):
        fn = getattr(career, name, None)
        if callable(fn):
            try:
                fn()
                return
            except Exception:
                pass
    # fallback: increment 1-based .week
    try:
        career.week = int(getattr(career, "week", 1)) + 1
    except Exception:
        pass

# ---------- core sim function ----------

def simulate_week_ai(career) -> bool:
    """
    Simulate all AI-vs-AI fixtures of the current week.
    If the user's team has a fixture this week and is unplayed, skip it (user can play).
    After simming, apply weekly training gains.
    """
    wk = _current_week_index(career)
    pairs = _fixtures_for_week(career, wk)
    if not pairs:
        return False

    user_tid = getattr(career, "user_tid", None)

    for (home_tid, away_tid) in pairs:
        # Skip user's fixture so they can play it manually
        if user_tid is not None and (str(home_tid) == str(user_tid) or str(away_tid) == str(user_tid)):
            continue

        # If engine is available, do a light headless sim; else random score
        if TBCombat is not None:
            home_roster = _team_roster(career, home_tid)
            away_roster = _team_roster(career, away_tid)
            # tag team_id for away
            for p in away_roster:
                p["team_id"] = 1
            fighters = home_roster + away_roster
            seed = getattr(career, "seed", 12345) ^ (wk << 8) ^ hash((str(home_tid), str(away_tid))) & 0xFFFFFFFF
            engine = TBCombat(str(home_tid), str(away_tid), fighters, grid_w=11, grid_h=11, seed=seed)
            # run to completion
            steps = 0
            while engine.winner is None and steps < 2000:
                engine.take_turn()
                steps += 1
            # derive kills from down events
            downs_home = 0
            downs_away = 0
            for ev in engine.typed_events:
                if ev.get("type") == "down":
                    # Approximation: assume downs of away counted for home, etc.
                    # (Precise attribution would track team of the downed.)
                    # Here we just count totals; tweak later if you store per-team kills.
                    pass
            # Better proxy: use winner and random small scores
            if engine.winner == 0:
                k_home, k_away = 3, 1
            elif engine.winner == 1:
                k_home, k_away = 1, 3
            else:
                k_home, k_away = 2, 2
        else:
            rng = random.Random(hash((wk, str(home_tid), str(away_tid))) & 0xFFFFFFFF)
            k_home = rng.randint(0, 4)
            k_away = rng.randint(0, 4)

        result = {"home_tid": home_tid, "away_tid": away_tid, "K_home": k_home, "K_away": k_away,
                  "winner": 0 if k_home > k_away else (1 if k_away > k_home else None)}
        _record_result(career, result)

    # Training tick for every club (very light)
    try:
        players_by_club = {}
        teams = getattr(career, "teams", [])
        for t in teams:
            tid = str(t.get("tid", t.get("id", "")))
            roster = t.get("fighters") or t.get("players") or []
            players_by_club[tid] = roster
        focus_per_player = {}
        for tid, plist in players_by_club.items():
            for p in plist:
                pid = str(p.get("pid", p.get("id", "")))
                if pid not in focus_per_player:
                    focus_per_player[pid] = {"DEX": 0.5, "STR": 0.5}
        for tid, plist in players_by_club.items():
            weekly_training_tick(career, tid, plist, focus_per_player)
    except Exception:
        pass

    _advance_week(career)
    return True
