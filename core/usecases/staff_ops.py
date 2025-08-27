# core/usecases/staff_ops.py
"""
Lightweight stubs so the integration hooks import cleanly.
You can expand these later (ratings mattering, injuries, etc.).

Plain English:
- club_staff(...)      -> returns a tiny staff record for a club
- training_gain_with_coaches(players, focus) -> (currently) +1 HP per week
- injury_modifiers(...) -> neutral modifiers for now
- estimate_player_with_scout(player) -> simple overall rating number
"""

from __future__ import annotations
from typing import Dict, Any, Iterable


def club_staff(store: Dict[str, Any] | None, club_id: str) -> Dict[str, Any]:
    """
    Return the staff dict for a club. If nothing stored yet, return safe defaults.
    """
    if not isinstance(store, dict):
        store = {}
    by_club = store.get("by_club", {})
    rec = by_club.get(str(club_id))
    if isinstance(rec, dict):
        return rec
    # default empty staff "slots"
    return {
        "coach": {"name": "Coach", "rating": 50},
        "scout": {"name": "Scout", "rating": 50},
        "physio": {"name": "Physio", "rating": 50},
    }


def training_gain_with_coaches(players: Iterable[Dict[str, Any]], focus: Dict[str, Dict[str, float]]) -> None:
    """
    Weekly training effect.
    For now we keep it VERY small & deterministic: each player +1 current HP (up to max_hp).
    (We read focus to prove through-paths, but do not change stats based on it yet.)
    """
    for p in players:
        try:
            hp = int(p.get("hp", 10))
            mx = int(p.get("max_hp", max(10, hp)))
            if hp < mx:
                p["hp"] = hp + 1
        except Exception:
            # never crash training
            pass


def injury_modifiers(store: Dict[str, Any] | None, club_id: str) -> Dict[str, float]:
    """
    Neutral injury modifiers for now.
    """
    return {
        "injury_chance_mult": 1.0,
        "recovery_rate_mult": 1.0,
    }


def estimate_player_with_scout(player: Dict[str, Any]) -> float:
    """
    Very simple 'OVR' estimate for scouting screens: average of STR/DEX/CON if present,
    else fall back to AC and max_hp scale.
    """
    try:
        nums = []
        for key in ("STR", "DEX", "CON"):
            if key in player:
                nums.append(float(player[key]))
        if nums:
            return sum(nums) / len(nums)
        # fallback
        ac = float(player.get("ac", 10))
        mx = float(player.get("max_hp", 10))
        return 0.6 * ac + 0.4 * mx
    except Exception:
        return 10.0
