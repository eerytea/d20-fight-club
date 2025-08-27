from __future__ import annotations
from typing import Dict, Any, List, Optional

from core import reputation as _rep
from core.usecases import staff_ops as _staff_ops

# ---------- Bootstrapping ----------

def bootstrap_career(career) -> None:
    """
    Ensure the career has reputation tables and seeded staff.
    Safe to call on new games and on loaded saves.
    """
    try:
        _rep.ensure_tables(career, teams=getattr(career, "teams", []))
    except Exception:
        pass
    try:
        _staff_ops.ensure_seeded_staff(career)
    except Exception:
        pass


# ---------- Match finalization → Reputation ----------

def on_match_finalized(
    career,
    home_tid: str | int,
    away_tid: str | int,
    k_home: int,
    k_away: int,
    comp_kind: str = "league",
    home_advantage: str = "a",   # 'a' -> apply small home boost, anything else -> off
) -> None:
    """
    Record a finished club match into Elo reputation.
    This is called by Career.record_result(...).
    """
    home_tid = str(home_tid); away_tid = str(away_tid)
    try:
        _rep.record_club_match(
            career,
            home_tid=home_tid,
            away_tid=away_tid,
            k_home=int(k_home),
            k_away=int(k_away),
            home_boost=(home_advantage == "a"),
        )
    except Exception:
        # Never break the game loop because reputation failed.
        pass


# ---------- Weekly training & injuries ----------

def weekly_training_tick(
    career,
    club_id: str | int,
    players: List[Dict[str, Any]],
    focus_per_player: Dict[str, Dict[str, float]],
) -> None:
    """
    Let the club's coach improve players a tiny amount based on focus.
    - club_id: team tid
    - players: list of player dicts (mutated in place)
    - focus_per_player: {'pid': {'STR':0.6, 'DEX':0.4, ...}, ...}
    """
    try:
        _staff_ops.apply_training(career, str(club_id), players, focus_per_player)
    except Exception:
        pass


def injury_mods_for_club(career, club_id: str | int) -> Dict[str, float]:
    """
    Returns a small set of injury-related multipliers based on physio quality.
    Example: {'recovery_speed': 1.08, 'injury_risk_mult': 0.95}
    """
    try:
        return _staff_ops.injury_mods(career, str(club_id))
    except Exception:
        return {"recovery_speed": 1.0, "injury_risk_mult": 1.0}
