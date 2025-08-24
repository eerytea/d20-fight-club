import random
from dataclasses import dataclass
from typing import List, Dict, Optional
from .model import Fighter, Team, Weapon

@dataclass
class Event:
    kind: str
    payload: Dict

def _mod(score: int) -> int:
    return (score - 10) // 2

def _roll_dice(spec: str, rng: random.Random) -> int:
    # "2d6+3" etc.
    parts = spec.lower().replace(' ', '').split('d')
    if len(parts) == 1:
        return int(parts[0])
    n = int(parts[0]) if parts[0] else 1
    rest = parts[1]
    plus = 0
    if '+' in rest:
        die, add = rest.split('+',1)
        plus = int(add)
    elif '-' in rest:
        die, sub = rest.split('-',1)
        plus = -int(sub)
    else:
        die = rest
    sides = int(die)
    return sum(rng.randint(1, sides) for _ in range(n)) + plus

class TBCombat:
    def __init__(self, teamA: Team, teamB: Team, fighters: List[Fighter], W: int, H: int, seed: int = 12345):
        self.teamA, self.teamB = teamA, teamB
        self.fighters = fighters
        self.W, self.H = W, H
        self.rng = random.Random(seed)
        self.round = 1
        self.turn_index = 0
        self.events: List[Event] = []
        self.winner: Optional[int] = None
        for f in self.fighters:
            f.hp = f.max_hp
        self.events.append(Event("round_start", {"round": self.round}))

    def _alive(self, tid: int) -> List[Fighter]:
        return [f for f in self.fighters if f.team_id == tid and f.alive]

    def _find_target(self, f: Fighter) -> Optional[Fighter]:
        enemies = self._alive(1 - f.team_id)
        if not enemies: return None
        # nearest by manhattan
        enemies.sort(key=lambda e: abs(e.tx - f.tx) + abs(e.ty - f.ty))
        return enemies[0]

    def _move_towards(self, actor: Fighter, target: Fighter):
        # simple greedy move one tile towards
        dx = 1 if target.tx > actor.tx else (-1 if target.tx < actor.tx else 0)
        dy = 1 if target.ty > actor.ty else (-1 if target.ty < actor.ty else 0)
        nx, ny = actor.tx + dx, actor.ty + dy
        nx = max(0, min(self.W-1, nx)); ny = max(0, min(self.H-1, ny))
        if (nx, ny) != (actor.tx, actor.ty):
            actor.tx, actor.ty = nx, ny
            self.events.append(Event("move_step", {"name": actor.name, "to": (nx, ny)}))

    def _attack(self, attacker: Fighter, defender: Fighter):
        atk_mod = _mod(attacker.str_) if attacker.weapon.prop == "str" else _mod(attacker.dex)
        atk_mod += attacker.prof_bonus
        ac = defender.ac
        d20 = self.rng.randint(1, 20)
        crit = (d20 == 20)
        hit = (d20 + atk_mod >= ac) or crit
        self.events.append(Event("attack", {
            "attacker": attacker.name, "defender": defender.name,
            "nat": d20, "target_ac": ac, "critical": crit, "hit": hit
        }))
        if not hit: return
        dmg_str = attacker.weapon.damage if isinstance(attacker.weapon, Weapon) else str(attacker.weapon)
        dmg = _roll_dice(dmg_str, self.rng)
        if attacker.weapon.prop == "str": dmg += _mod(attacker.str_)
        else: dmg += _mod(attacker.dex)
        if crit: dmg *= attacker.weapon.crit[1]
        dmg = max(1, dmg)
        defender.hp -= dmg
        self.events.append(Event("damage", {
            "attacker": attacker.name, "defender": defender.name,
            "amount": dmg, "hp_after": max(0, defender.hp)
        }))
        if defender.hp <= 0 and defender.alive:
            defender.alive = False
            self.events.append(Event("down", {"name": defender.name}))

    def take_turn(self):
        if self.winner is not None: return
        alive_allies = self._alive(0) + self._alive(1)
        if not self._alive(0): self.winner = 1; self.events.append(Event("end", {"winner": self.teamB.name})); return
        if not self._alive(1): self.winner = 0; self.events.append(Event("end", {"winner": self.teamA.name})); return
        if not alive_allies: self.winner = -1; self.events.append(Event("end", {"reason": "no fighters"})); return

        self.turn_index = (self.turn_index + 1) % len(self.fighters)
        actor = self.fighters[self.turn_index]
        if not actor.alive:
            return

        tgt = self._find_target(actor)
        if tgt is None: return
        # in range?
        dist = abs(tgt.tx - actor.tx) + abs(tgt.ty - actor.ty)
        if dist > actor.weapon.reach:
            self._move_towards(actor, tgt)
        else:
            self._attack(actor, tgt)

        # round bookkeeping (very simple)
        if self.turn_index == len(self.fighters) - 1:
            self.round += 1
            self.events.append(Event("round_start", {"round": self.round}))
