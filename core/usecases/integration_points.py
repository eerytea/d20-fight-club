from __future__ import annotations

from typing import Dict, Any, Iterable, List, Optional
from core.reputation import RepTable
from core.usecases.reputation_hooks import ensure_reputation, record_club_match
from core.usecases.staff_ops import (
    club_staff, training_gain_with_coaches, injury_modifiers, estimate_player_with_scout
)
from core.staff import StaffRole
from engine.tactics.opposition import OppositionInstruction
from engine.ai.weights import apply_oi_target_scores

# 1) Bootstrap: ensure reputation exists (call once at new career or when loading older saves)
def bootstrap_career(career) -> None:
    ensure_reputation(career)
    if not hasattr(career, "all_staff"):
        career.all_staff = {}  # basic container if you don't have staff persistence yet

# 2) Record club match into reputation tables (call at match finalize)
def on_match_finalized(
    career,
    home_club_id: str,
    away_club_id: str,
    goals_home: int,
    goals_away: int,
    comp_kind: str = "league",
    home_advantage: Optional[str] = None
) -> None:
    record_club_match(career, home_club_id, away_club_id, goals_home, goals_away, comp_kind, home_advantage=home_advantage)

# 3) Apply Opposition Instructions to AI target scores (call inside AI target selection)
def apply_oi_to_scores(
    base_scores: Dict[int, float],
    enemy_units: Iterable[Dict[str, Any]],
    oi_list: Iterable[OppositionInstruction]
) -> Dict[int, float]:
    return apply_oi_target_scores(base_scores, enemy_units, oi_list)

# 4) Weekly training tick (call once per club per week in your sim-week code)
def weekly_training_tick(
    career,
    club_id: str,
    players: List[Dict[str, Any]],
    focus_per_player: Dict[str, Dict[str, float]]  # pid -> {attr: weight}
) -> None:
    coaches = [s for s in club_staff(career, club_id) if s.role == StaffRole.COACH]
    for p in players:
        pid = str(p.get("pid"))
        focus = focus_per_player.get(pid, {"DEX": 0.5, "STR": 0.5})
        deltas = training_gain_with_coaches(p, focus, coaches)
        for k, dv in deltas.items():
            p[k] = p.get(k, 0.0) + dv

# 5) Injury model modifiers (use in your injury roll / recovery code)
def injury_mods_for_club(career, club_id: str) -> Dict[str, float]:
    physios = [s for s in club_staff(career, club_id) if s.role == StaffRole.PHYSIO]
    return injury_modifiers(physios)
