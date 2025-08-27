from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, Literal, Callable, List

TargetKind = Literal["role", "player_id", "attribute_query"]

@dataclass
class OppositionInstruction:
    target_kind: TargetKind
    target_value: str                      # e.g., "Striker" or "pid:123" or "DEX>=14 AND role=Healer"
    directives: Dict[str, Any]             # e.g., {"focus_fire": True, "tight_mark": True}
    priority: int = 1                      # 1..3; higher = stronger bias
    trigger: Optional[str] = None          # optional: "losing", "round>=5", ...

def _parse_attr_query(q: str) -> Callable[[Dict[str, Any]], bool]:
    """Return predicate(player_dict)->bool for 'DEX>=14 AND role=Healer'."""
    import re
    tokens = [t.strip() for t in re.split(r"\bAND\b", q, flags=re.IGNORECASE)]
    tests: List[Callable[[Dict[str, Any]], bool]] = []

    def make_test(part: str):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(>=|<=|>|<|==|=|!=)\s*([A-Za-z0-9_]+)$", part)
        if not m:
            def bad(_): return False
            return bad
        attr, op, value = m.groups()
        v = int(value) if value.isdigit() else value

        def test(d: Dict[str, Any]) -> bool:
            x = d.get(attr)
            if isinstance(x, (int, float)) and isinstance(v, (int, float)):
                if op == ">=": return x >= v
                if op == "<=": return x <= v
                if op == ">":  return x > v
                if op == "<":  return x < v
                if op in ("==", "="): return x == v
                if op == "!=": return x != v
            else:
                if op in ("==", "="): return str(x) == str(v)
                if op == "!=": return str(x) != str(v)
            return False
        return test

    for part in tokens:
        tests.append(make_test(part))

    def predicate(d: Dict[str, Any]) -> bool:
        return all(t(d) for t in tests)

    return predicate

def instruction_applies_to(oi: OppositionInstruction, unit: Dict[str, Any]) -> bool:
    kind = oi.target_kind
    if kind == "player_id":
        return str(unit.get("pid")) == oi.target_value or f"pid:{unit.get('pid')}" == oi.target_value
    if kind == "role":
        return str(unit.get("role")) == oi.target_value
    if kind == "attribute_query":
        pred = _parse_attr_query(oi.target_value)
        return pred(unit)
    return False
