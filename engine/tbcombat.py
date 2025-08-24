from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import random
import re

from .model import Fighter, Team, Weapon

# -----------------------------
# Events (for readable logs)
# -----------------------------
@dataclass
class Event:
    kind: str
    data: dict

# -----------------------------
# Dice helpers
# -----------------------------

_DICE_RE = re.compile(r"^\s*(\d+)d(\d+)([+-]\d+)?\s*$")

def _roll_d20(rng: random.Random) -> int:
    return rng.randint(1, 20)

def _mod(score: int) -> int:
    return (score - 10) // 2

def _roll_damage(expr: str, rng: random.Random) -> int:
    """
    Supports: 'XdY', 'XdY+Z', 'Z' (flat).
    """
    expr = str(expr).strip()
    if expr.isdigit() or (expr.startswith("-") and expr[1:].isdigit()):
        return int(expr)
    m = _DICE_RE.match(expr)
    if not m:
        # fallback minimal damage for unknown strings
        return 1
    x = int(m.group(1))
    y = int(m.group(2))
    z = int(m.group(3) or 0)
    total = 0
    for _ in range(x):
        total += rng.randint(1, y)
    total += z
    return max(0, total)

# -----------------------------
# Combat
# -----------------------------

class TBCombat:
    def __init__(self,
                 teamA: Team,
                 teamB: Team,
                 fighters: List[Fighter],
                 grid_w: int,
                 grid_h: int,
                 seed: int = 0):
        self.teamA = teamA
        self.teamB = teamB
        self.fighters: List[Fighter] = fighters
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.rng = random.Random(seed)
        self.turn_index: int = -1
        self.winner: Optional[int] = None  # 0 -> teamA, 1 -> teamB, -1 -> draw
        self.events: List[Event] = []

    # ---------- utility ----------
    def _alive(self, team_id: int) -> List[Fighter]:
        return [f for f in self.fighters if f.team_id == team_id and f.alive]

    def _enemies_of(self, team_id: int) -> List[Fighter]:
        return [f for f in self.fighters if f.team_id != team_id and f.alive]

    def _dist(self, a: Fighter, b: Fighter) -> int:
        return abs(a.tx - b.tx) + abs(a.ty - b.ty)

    def _find_target(self, actor: Fighter) -> Optional[Fighter]:
        enemies = self._enemies_of(actor.team_id)
        if not enemies:
            return None
        enemies.sort(key=lambda e: (self._dist(actor, e), e.hp, e.id or 0))
        return enemies[0]

    def _can_move_to(self, x: int, y: int) -> bool:
        if not (0 <= x < self.grid_w and 0 <= y < self.grid_h):
            return False
        for f in self.fighters:
            if f.alive and f.tx == x and f.ty == y:
                return False
        return True

    # ---------- turn ----------
    def take_turn(self) -> None:
        if self.winner is not None:
            return

        # end checks (in case someone died between turns)
        if not self._alive(0) and not self._alive(1):
            self.winner = -1
            self.events.append(Event("end", {"reason": "no fighters"}))
            return
        if not self._alive(0):
            self.winner = 1
            self.events.append(Event("end", {"winner": self.teamB.name}))
            return
        if not self._alive(1):
            self.winner = 0
            self.events.append(Event("end", {"winner": self.teamA.name}))
            return

        # next actor
        self.turn_index = (self.turn_index + 1) % len(self.fighters)
        actor = self.fighters[self.turn_index]
        if not actor.alive:
            return

        tgt = self._find_target(actor)
        if tgt is None:
            return

        # move if out of reach
        dist = self._dist(actor, tgt)
        reach = getattr(actor.weapon, "reach", 1)
        if dist > reach:
            dx = 0 if tgt.tx == actor.tx else (1 if tgt.tx > actor.tx else -1)
            dy = 0 if tgt.ty == actor.ty else (1 if tgt.ty > actor.ty else -1)
            # try horizontal then vertical
            candidates: List[Tuple[int,int]] = [(actor.tx + dx, actor.ty),
                                                (actor.tx, actor.ty + dy)]
            moved = False
            for nx, ny in candidates:
                if self._can_move_to(nx, ny):
                    actor.tx, actor.ty = nx, ny
                    self.events.append(Event("move", {"name": actor.name, "to": (nx, ny)}))
                    moved = True
                    break
            if moved:
                return
            # blocked: skip
            return

        # attack
        d20 = _roll_d20(self.rng)
        # basic ability choice: STR to-hit; allow DEX if higher
        to_hit_mod = max(_mod(actor.str), _mod(actor.dex))
        total_to_hit = d20 + to_hit_mod + getattr(actor.weapon, "to_hit_bonus", 0)

        hit = False
        crit = False
        if d20 >= getattr(actor.weapon, "crit_range", 20):
            hit = True
            crit = True
        elif total_to_hit >= tgt.ac:
            hit = True

        self.events.append(Event("attack", {
            "attacker": actor.name,
            "target": tgt.name,
            "roll": d20,
            "to_hit_total": total_to_hit,
            "ac": tgt.ac
        }))

        if not hit:
            self.events.append(Event("miss", {"attacker": actor.name, "target": tgt.name}))
            return

        base = _roll_damage(getattr(actor.weapon, "damage", "1d2"), self.rng)
        if crit:
            base *= getattr(actor.weapon, "crit_mult", 2)
        dmg = max(1, base + _mod(actor.str))  # small STR to damage
        tgt.hp -= dmg

        self.events.append(Event("hit", {
            "attacker": actor.name,
            "target": tgt.name,
            "damage": dmg,
            "crit": crit,
            "tgt_hp": max(0, tgt.hp)
        }))

        if tgt.hp <= 0 and tgt.alive:
            tgt.alive = False
            # simple XP award to the finisher
            actor.xp += 10
            self.events.append(Event("down", {"target": tgt.name, "by": actor.name}))

            # team wipe check immediately
            if not self._alive(tgt.team_id):
                self.winner = 0 if tgt.team_id == 1 else 1
                self.events.append(Event("end", {
                    "winner": self.teamA.name if self.winner == 0 else self.teamB.name
                }))
