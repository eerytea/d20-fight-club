
from __future__ import annotations
import random
from typing import Dict, Any, List, Tuple

try:
    from core.spell_catalog import SPELLS
except Exception:
    SPELLS = []

def _pair_match(spell_pairs: List[Dict[str,str]], pos: str, role: str) -> bool:
    pos = (pos or "").strip().lower()
    role = (role or "").strip().lower()
    for p in (spell_pairs or []):
        sp = (p.get("position","") or "").strip().lower()
        sr = (p.get("role","") or "").strip().lower()
        if sp == pos and sr == role:
            return True
    return False

def _pos_only_match(spell_pairs: List[Dict[str,str]], pos: str) -> bool:
    pos = (pos or "").strip().lower()
    for p in (spell_pairs or []):
        sp = (p.get("position","") or "").strip().lower()
        if sp == pos:
            return True
    return False

def _ensure_known_struct(f: Dict[str,Any]) -> None:
    f.setdefault("known_cantrips", [])
    f.setdefault("known_spells", [])

def _known_count_by_slot(f: Dict[str,Any], slot_type: int) -> int:
    if slot_type == 0:
        return len(f.get("known_cantrips", []))
    # naive: count non-cantrips in known_spells of this slot (we don't store slot per name; best effort)
    # Better: use catalog to map names to slot types.
    known = set(f.get("known_spells", []))
    return sum(1 for s in SPELLS if s["slot_type"] == slot_type and s["spell"] in known and s["class"] == f.get("class"))

def _already_known(f: Dict[str,Any], spell_name: str) -> bool:
    return spell_name in f.get("known_spells", []) or spell_name in f.get("known_cantrips", [])

def _capacity_for_slot(f: Dict[str,Any], slot_type: int) -> int:
    if slot_type == 0:
        return int(f.get("cantrips_known", 0)) - len(f.get("known_cantrips", []))
    slots = (f.get("spell_slots_total") or [0]*10)
    cur = int(slots[slot_type]) if slot_type < len(slots) else 0
    # subtract how many we already know at that slot
    return max(0, cur - _known_count_by_slot(f, slot_type))

def learn_spells_for_level(f: Dict[str,Any], level: int) -> None:
    """
    At character level `level`, learn spells whose 'learn_at_level' equals `level`.
    Fill up to current slot capacity per slot_type using precedence:
      1) training pair (position+role) match
      2) position-only match
      3) class match (remaining)
      4) random from class
    """
    _ensure_known_struct(f)
    cls = f.get("class")
    training = f.get("training") or {}
    t_pos = (training.get("position") or "").strip()
    t_role = (training.get("role") or "").strip()

    # Candidate spells for this class & learnable now
    pool = [s for s in SPELLS if s["class"] == cls and int(s["learn_at_level"]) == int(level)]
    # Group by slot type
    by_slot = {}
    for s in pool:
        by_slot.setdefault(int(s["slot_type"]), []).append(s)

    # For each slot type, add up to capacity
    for slot_type, spells in by_slot.items():
        # capacity tracks remaining room at this slot
        capacity = _capacity_for_slot(f, slot_type)
        if capacity <= 0:
            continue

        def add_if_possible(spell_name: str):
            nonlocal capacity
            if capacity <= 0:
                return
            if _already_known(f, spell_name):
                return
            if slot_type == 0:
                f["known_cantrips"].append(spell_name)
            else:
                f["known_spells"].append(spell_name)
            capacity -= 1

        # 1) exact training pair
        exact = [s for s in spells if _pair_match(s.get("training_pairs", []), t_pos, t_role)]
        for s in exact:
            add_if_possible(s["spell"])

        # 2) position-only
        if capacity > 0 and t_pos:
            pos_hits = [s for s in spells if _pos_only_match(s.get("training_pairs", []), t_pos)]
            for s in pos_hits:
                add_if_possible(s["spell"])

        # 3) class match (remaining in this class/slot)
        if capacity > 0:
            cls_hits = [s for s in spells if not _already_known(f, s["spell"])]
            for s in cls_hits:
                add_if_possible(s["spell"])

        # 4) random fill if still short
        if capacity > 0:
            rest = [s for s in spells if not _already_known(f, s["spell"])]
            random.shuffle(rest)
            for s in rest:
                add_if_possible(s["spell"])
