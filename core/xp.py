# core/xp.py
from __future__ import annotations
from typing import Dict, Any

# --- Canonical XP table (per your chart) ---
XP_TABLE: Dict[int, Dict[str, int]] = {
    1:  {"kill":   50, "threshold":      0},
    2:  {"kill":  100, "threshold":    300},
    3:  {"kill":  150, "threshold":    900},
    4:  {"kill":  200, "threshold":   2700},
    5:  {"kill":  250, "threshold":   6500},
    6:  {"kill":  300, "threshold":  14000},
    7:  {"kill":  350, "threshold":  23000},
    8:  {"kill":  450, "threshold":  34000},
    9:  {"kill":  500, "threshold":  48000},
    10: {"kill":  550, "threshold":  64000},
    11: {"kill":  600, "threshold":  85000},
    12: {"kill":  700, "threshold": 100000},
    13: {"kill":  800, "threshold": 120000},
    14: {"kill":  900, "threshold": 140000},
    15: {"kill": 1000, "threshold": 165000},
    16: {"kill": 1100, "threshold": 195000},
    17: {"kill": 1300, "threshold": 225000},
    18: {"kill": 1500, "threshold": 265000},
    19: {"kill": 1700, "threshold": 305000},
    20: {"kill": 1800, "threshold": 355000},
}

_MAX_LEVEL = 20
_MAX_XP = XP_TABLE[_MAX_LEVEL]["threshold"]  # clamp here

def xp_for_kill(victim_level: int) -> int:
    L = max(1, min(_MAX_LEVEL, int(victim_level)))
    return int(XP_TABLE[L]["kill"])

def level_from_total_xp(xp_total: int) -> int:
    x = max(0, int(xp_total))
    level = 1
    for L in range(1, _MAX_LEVEL + 1):
        if x >= XP_TABLE[L]["threshold"]:
            level = L
        else:
            break
    return level

def grant_xp(player: Any, amount: int, *, reason: str = "kill", queue_levelups: bool = True) -> None:
    """
    Silent XP grant (no event logging). Clamps at level-20 threshold.
    Sets:
      - player['xp_total'] (clamped)
      - player['xp_gain_last'] (last grant amount; for debug/telemetry)
      - player['level_pending'] (how many levels above current, if queue_levelups=True)
    """
    amt = max(0, int(amount))
    cur = int(getattr(player, "xp_total", getattr(player, "XP", 0)) or 0)
    new_total = min(cur + amt, _MAX_XP)
    # write both attribute and dict forms to be friendly to Obj/dict hybrids
    try: player.xp_total = new_total  # type: ignore[attr-defined]
    except Exception: pass
    player["xp_total"] = new_total
    player["xp_gain_last"] = amt

    if queue_levelups:
        current_level = int(getattr(player, "level", player.get("level", 1)))
        future_level = level_from_total_xp(new_total)
        pend = max(0, future_level - current_level)
        player["level_pending"] = pend

def settle_post_match_levels(player: Any) -> None:
    """
    Apply any queued level increases after a match ends.
    Uses core.classes.apply_class_level_up for each level gained.
    """
    from core.classes import apply_class_level_up  # late import to avoid cycles
    current = int(player.get("level", 1))
    xp_total = int(player.get("xp_total", 0))
    target = level_from_total_xp(xp_total)
    for L in range(current + 1, min(target, _MAX_LEVEL) + 1):
        apply_class_level_up(player, L)
    player["level"] = min(target, _MAX_LEVEL)
    # clear pending marker
    if "level_pending" in player:
        del player["level_pending"]
