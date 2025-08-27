from __future__ import annotations
from typing import Dict, Any, List, Tuple

def _mix(seed: int, text: str) -> int:
    x = (seed ^ 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    for b in text.encode("utf-8"):
        x ^= (b + 0x9E3779B97F4A7C15 + ((x << 6) & 0xFFFFFFFFFFFFFFFF) + (x >> 2))
        x &= 0xFFFFFFFFFFFFFFFF
    return x

# ----------------- Seeding staff -----------------

def ensure_seeded_staff(career) -> None:
    """
    Ensure career.staff['by_club'][tid] exists with a coach, scout, physio.
    Deterministic from career.seed + tid.
    """
    staff = getattr(career, "staff", None)
    if staff is None or not isinstance(staff, dict):
        staff = {}
        setattr(career, "staff", staff)
    by_club = staff.setdefault("by_club", {})

    seed = int(getattr(career, "seed", 12345))
    for t in getattr(career, "teams", []):
        tid = str(t.get("tid", t.get("id")))
        if tid in by_club:
            # already seeded
            continue
        # deterministic pseudo-ratings
        r_coach  = 50 + (_mix(seed, f"coach:{tid}")  % 51)  # 50..100
        r_scout  = 50 + (_mix(seed, f"scout:{tid}")  % 51)
        r_physio = 50 + (_mix(seed, f"physio:{tid}") % 51)
        by_club[tid] = {
            "coach":  {"role": "coach",  "name": f"Coach {tid}",  "rating": int(r_coach)},
            "scout":  {"role": "scout",  "name": f"Scout {tid}",  "rating": int(r_scout)},
            "physio": {"role": "physio", "name": f"Physio {tid}", "rating": int(r_physio)},
        }

# ----------------- Training -----------------

def apply_training(
    career,
    club_id: str,
    players: List[Dict[str, Any]],
    focus_per_player: Dict[str, Dict[str, float]],
) -> None:
    """
    Simple deterministic training:
      - Coach rating drives a small weekly chance to +1 in focused stats.
      - Uses seed + week + club + pid to decide upgrades.
    """
    ensure_seeded_staff(career)
    coach_rating = int(getattr(career.staff["by_club"][club_id]["coach"], "get", lambda k, d=None: None)("rating", None)
                       if isinstance(career.staff["by_club"][club_id]["coach"], dict)
                       else career.staff["by_club"][club_id]["coach"].rating
                       ) if "by_club" in getattr(career, "staff", {}) else 60
    # Fallback if dict path above is messy
    if isinstance(career.staff["by_club"][club_id]["coach"], dict):
        coach_rating = int(career.staff["by_club"][club_id]["coach"].get("rating", 60))

    seed = int(getattr(career, "seed", 12345))
    week = int(getattr(career, "week", 1))
    base_chance = 0.05 + 0.003 * (coach_rating - 50)  # ~2%..20%

    for p in players:
        pid = str(p.get("pid", p.get("id", 0)))
        focus = focus_per_player.get(pid, {})
        # Normalize weights
        total = sum(v for v in focus.values() if isinstance(v, (int, float)) and v > 0)
        if total <= 0:
            continue
        for stat, w in focus.items():
            if not isinstance(w, (int, float)) or w <= 0:
                continue
            prob_pp = base_chance * (w / total)
            # Deterministic coin flip
            rbits = _mix(seed, f"train:{club_id}:{pid}:{stat}:W{week}") & 0xFFFF
            threshold = int(prob_pp * 65535.0)
            if rbits < threshold:
                try:
                    p[stat] = int(p.get(stat, 0)) + 1
                except Exception:
                    pass

# ----------------- Injuries -----------------

def injury_mods(career, club_id: str) -> Dict[str, float]:
    """
    Return tiny multipliers based on physio quality.
    """
    ensure_seeded_staff(career)
    phy = career.staff["by_club"][club_id]["physio"]
    rating = phy.get("rating", 60) if isinstance(phy, dict) else getattr(phy, "rating", 60)
    return {
        "recovery_speed": 1.0 + (rating - 50) / 500.0,   # 50 → 1.0, 100 → 1.1
        "injury_risk_mult": max(0.9, 1.0 - (rating - 50) / 500.0),  # 100 → ~0.9
    }

# ----------------- Scouting (optional helper) -----------------

def scout_report(career, club_id: str, target_tid: str) -> Dict[str, Any]:
    """
    Return a coarse 'OVR' estimate for each player on target team, noisy by scout rating.
    """
    ensure_seeded_staff(career)
    scout = career.staff["by_club"][club_id]["scout"]
    srat = scout.get("rating", 60) if isinstance(scout, dict) else getattr(scout, "rating", 60)
    seed = int(getattr(career, "seed", 12345))

    team = next((t for t in getattr(career, "teams", []) if str(t.get("tid")) == str(target_tid)), None)
    if not team:
        return {"team": target_tid, "players": []}

    out = []
    for p in team.get("fighters", []):
        pid = str(p.get("pid", p.get("id", 0)))
        # crude OVR: average STR/DEX/CON with a little noise scaled by scout rating
        base = (int(p.get("STR", 10)) + int(p.get("DEX", 10)) + int(p.get("CON", 10))) / 3.0
        noise_raw = (_mix(seed, f"scout:{club_id}:{target_tid}:{pid}") % 21) - 10  # -10..+10
        noise = noise_raw * max(0.1, (110 - srat) / 100.0)
        est = max(1.0, min(99.0, base + noise))
        out.append({"pid": pid, "name": p.get("name", f"P{pid}"), "est_ovr": round(est, 1)})
    return {"team": target_tid, "players": out}
