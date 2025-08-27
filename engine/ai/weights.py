from __future__ import annotations
from typing import Dict, Any

# Simple, global Opposition Instructions map used by TBCombat.
# Keep it tiny & safe: if nothing set, we just return base score.

_OI: Dict[str, Any] | None = None

def set_oi_map(oi: Dict[str, Any] | None) -> None:
    """
    oi example:
      {
        "focus_low_hp": True,
        "prefer_roles": {"Healer": 20, "Bruiser": 10}
      }
    """
    global _OI
    _OI = dict(oi) if isinstance(oi, dict) else None

def clear_oi() -> None:
    global _OI
    _OI = None

def apply_oi_bias(attacker, target, base_score: float) -> float:
    """
    Hook used by engine.tbcombat.TBCombat during target scoring.
    It receives attacker/target (actors) and a base_score (float).
    Return the adjusted score.
    """
    oi = _OI
    if not isinstance(oi, dict):
        return float(base_score)

    score = float(base_score)

    # Bias: prefer targets with low HP
    if oi.get("focus_low_hp"):
        # + up to ~15 pts when target is near 0 HP
        try:
            hp = int(getattr(target, "hp", 0))
            mx = max(1, int(getattr(target, "max_hp", 1)))
            frac = 1.0 - (hp / mx)
            score += 15.0 * max(0.0, min(1.0, frac))
        except Exception:
            pass

    # Bias: role preferences (e.g., "Healer": +20)
    prefs = oi.get("prefer_roles", {})
    if isinstance(prefs, dict):
        role = getattr(target, "role", None)
        if role is None and isinstance(getattr(target, "__dict__", None), dict):
            role = target.__dict__.get("role")
        if role is not None and role in prefs:
            try:
                score += float(prefs[role])
            except Exception:
                pass

    return float(score)
