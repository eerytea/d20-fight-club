# engine/tbcombat.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import random

# Try typed event formatter; fall back to simple strings.
try:
    from .events import format_event  # type: ignore
except Exception:
    def format_event(e) -> str:
        t = e.get("type", "?")
        if t == "move":
            return f"{e['name']} moves to {e['to']}"
        if t == "hit":
            return f"{e['name']} hits {e['target']} for {e['dmg']}!"
        if t == "miss":
            return f"{e['name']} misses {e['target']}"
        if t == "down":
            return f"{e['target']} is down!"
        if t == "level_up":
            return f"{e['name']} reached level {e['level']}!"
        if t == "round":
            return f"— Round {e['round']} —"
        if t == "end":
            return f"Match ended: {e.get('winner','draw')}"
        return str(e)

# Ratings hook
try:
    from core.ratings import level_up
except Exception:
    def level_up(f):  # pragma: no cover
        f["level"] = f.get("level", 1) + 1

def ability_mod(score: int) -> int:
    return (int(score) - 10) // 2

def d20(rng: random.Random) -> int:
    return rng.randint(1, 20)

def expected_hp(f: Dict) -> int:
    return int(f.get("hp", 10))

def attack_bonus(f: Dict) -> int:
    prof = int(f.get("prof", 2))
    atk_mod = int(f.get("atk_mod", ability_mod(f.get("str", 10)) + prof))
    return atk_mod

def target_ac(f: Dict) -> int:
    return int(f.get("ac", 12))

def damage_roll(f: Dict, crit: bool, rng: random.Random) -> int:
    dmg = 0
    w = f.get("weapon", {"damage": "1d6"})
    try:
        s = w.get("damage", "1d6").lower()
        n, s = s.split("d")
        n = int(n) * (2 if crit else 1)
        s = int(s)
        dmg = sum(rng.randint(1, s) for _ in range(max(1, n)))
    except Exception:
        dmg = rng.randint(1, 6) * (2 if crit else 1)
    dmg += max(0, ability_mod(int(f.get("str", 10))))
    return max(0, dmg)

@dataclass
class _F:
    name: str
    tid: int
    tx: int
    ty: int
    hp: int
    ac: int
    spd: int
    alive: bool
    ref: Dict
    xp: int
    level: int

def _mk_fighters(team: Dict, tid: int, grid_w: int, grid_h: int) -> List[_F]:
    roster = team.get("roster") or team.get("fighters") or []
    roster = roster[:]
    fs: List[_F] = []
    gap = grid_h // (len(roster) + 1) if roster else max(1, grid_h // 2)
    base_x = 1 if tid == 0 else max(0, grid_w - 2)
    for i, rd in enumerate(roster, start=1):
        fs.append(_F(
            name=rd.get("name", f"P{tid}-{i}"),
            tid=tid,
            tx=base_x,
            ty=min(grid_h - 1, i * gap),
            hp=expected_hp(rd),
            ac=target_ac(rd),
            spd=int(rd.get("speed", 6)),
            alive=True,
            ref=rd,
            xp=int(rd.get("xp", 0)),
            level=int(rd.get("level", 1)),
        ))
    return fs

def _nearest_enemy(me: _F, fighters: List[_F]) -> Optional[_F]:
    enemies = [f for f in fighters if f.alive and f.tid != me.tid]
    if not enemies:
        return None
    return min(enemies, key=lambda e: abs(e.tx - me.tx) + abs(e.ty - me.ty))

def _step_toward(me: _F, tgt: _F, fighters: List[_F], grid_w: int, grid_h: int) -> None:
    if not tgt:
        return
    def free(nx, ny) -> bool:
        if nx < 0 or ny < 0 or nx >= grid_w or ny >= grid_h:
            return False
        for o in fighters:
            if o.alive and o.tx == nx and o.ty == ny:
                return False
        return True
