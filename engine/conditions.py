# engine/conditions.py
from __future__ import annotations
from typing import Dict

CONDITION_PRONE = "prone"
CONDITION_RESTRAINED = "restrained"
CONDITION_STUNNED = "stunned"

ALL_CONDITIONS = {CONDITION_PRONE, CONDITION_RESTRAINED, CONDITION_STUNNED}

def ensure_bag(f) -> Dict[str, int]:
    """Ensure a dict bag for conditions exists on fighter."""
    if not hasattr(f, "_conditions") or not isinstance(getattr(f, "_conditions"), dict):
        try:
            setattr(f, "_conditions", {})
        except Exception:
            pass
    return getattr(f, "_conditions", {})

def has_condition(f, name: str) -> bool:
    bag = ensure_bag(f)
    return int(bag.get(name, 0)) > 0

def add_condition(f, name: str, rounds: int):
    if name not in ALL_CONDITIONS:
        return
    bag = ensure_bag(f)
    bag[name] = max(int(bag.get(name, 0)), 0) + max(0, int(rounds))

def clear_condition(f, name: str):
    bag = ensure_bag(f)
    if name in bag:
        del bag[name]

def decrement_all_for_turn(f) -> Dict[str, int]:
    """Decrement all durations at the start of f's turn. Returns ended {name: old_value}."""
    bag = ensure_bag(f)
    ended = {}
    keys = list(bag.keys())
    for k in keys:
        v = int(bag.get(k, 0))
        v -= 1
        if v <= 0:
            ended[k] = int(bag.get(k, 0))
            del bag[k]
        else:
            bag[k] = v
    return ended
