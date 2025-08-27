from __future__ import annotations

from typing import Dict, Iterable, Any
from engine.tactics.opposition import OppositionInstruction, instruction_applies_to

def apply_oi_target_scores(
    base_scores: Dict[int, float],
    enemy_units: Iterable[Dict[str, Any]],
    instructions: Iterable[OppositionInstruction],
) -> Dict[int, float]:
    """Bias base target scores using Opposition Instructions.
    - focus_fire: multiply by (1 + 0.4*priority)
    - avoid:      multiply by (1 - 0.2*priority)
    """
    unit_by_pid = {int(u.get("pid", -1)): u for u in enemy_units}
    scores = dict(base_scores)
    for oi in instructions:
        pr = max(1, min(3, int(oi.priority)))
        for pid, u in unit_by_pid.items():
            if not instruction_applies_to(oi, u):
                continue
            if oi.directives.get("focus_fire"):
                scores[pid] = scores.get(pid, 0.0) * (1.0 + 0.4 * pr)
            if oi.directives.get("avoid"):
                scores[pid] = scores.get(pid, 0.0) * (1.0 - 0.2 * pr)
            # Extend here (deny_heal, tackle_hard) as needed.
    return scores
