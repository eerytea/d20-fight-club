from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# Optional OI bias hook
try:
    from engine.ai.weights import apply_oi_bias  # (attacker, target, base_score) -> score
except Exception:
    def apply_oi_bias(attacker, target, base_score: float) -> float:
        return base_score

# ---------------------------------------------------------------------------
# Internal model
# ---------------------------------------------------------------------------

@dataclass
class _Actor:
    pid: int
    name: str
    team_id: int
    x: int
    y: int
    hp: int
    max_hp: int
    ac: int
    alive: bool = True
    role: Optional[str] = None
    xp: int = 0
    STR: int = 10
    DEX: int = 10
    CON: int = 10
    INT: int = 8
    WIS: int = 8
    CHA: int = 8

# ---------------------------------------------------------------------------
# TBCombat
# ---------------------------------------------------------------------------

class TBCombat:
    """
    Deterministic, seedable, single-occupancy turn-based combat.

    API (kept stable):
      - TBCombat(teamA, teamB, fighters, grid_w, grid_h, seed=...)
        * accepts kw aliases GRID_W/GRID_H
        * team names may be strings
      - .typed_events  (aliases: .events_typed, .events)
      - .take_turn()   (alias: .step_action())
      - .winner -> 0/1/None
      - .W, .H (grid size)
      - .round  (1-based)
      - .fighters_all -> list of _Actor
      - ._move_actor_if_free(actor, (x,y)) helper
    """

    def __init__(self, teamA: Any, teamB: Any, fighters: List[Dict[str, Any]], **kwargs):
        # Grid size with aliases
        self.W = int(kwargs.get("grid_w", kwargs.get("GRID_W", kwargs.get("w", 11))))
        self.H = int(kwargs.get("grid_h", kwargs.get("GRID_H", kwargs.get("h", 11))))
        self.seed = int(kwargs.get("seed", 12345))

        self.teamA = str(teamA)
        self.teamB = str(teamB)

        self.rng = random.Random(self.seed)
        self.typed_events: List[Dict[str, Any]] = []
        # convenient aliases
        self.events_typed = self.typed_events
        self.events = self.typed_events

        # normalize fighters into _Actor objects (tolerant input)
        self.fighters_all: List[_Actor] = []
        for i, f in enumerate(fighters):
            d = dict(f) if isinstance(f, dict) else f.__dict__.copy()
            pid = int(d.get("pid", d.get("id", i)))
            name = str(d.get("name", f"P{pid}"))
            team_id = int(d.get("team_id", d.get("tid", 0)))
            x = int(d.get("x", d.get("tx", 0)))
            y = int(d.get("y", d.get("ty", 0)))
            hp = int(d.get("hp", d.get("HP", 10)))
            mx = int(d.get("max_hp", d.get("HP_max", hp)))
            ac = int(d.get("ac", d.get("AC", 10)))
            alive = bool(d.get("alive", d.get("is_alive", True)))
            role = d.get("role", d.get("position"))
            STR = int(d.get("STR", 10)); DEX = int(d.get("DEX", 10)); CON = int(d.get("CON", 10))
            INT = int(d.get("INT", 8));  WIS = int(d.get("WIS", 8));  CHA = int(d.get("CHA", 8))
            xp = int(d.get("xp", d.get("XP", 0)))
            self.fighters_all.append(_Actor(pid, name, team_id, x, y, hp, mx, ac, alive, role, xp, STR, DEX, CON, INT, WIS, CHA))

        # layout (no overlaps; left/right bands)
        self._occupy = [[None for _ in range(self.H)] for __ in range(self.W)]
        self._layout_teams_tiles()

        # initiative: deterministic from seed + pid + team_id
        order = list(range(len(self.fighters_all)))
        def _key(ix):
            a = self.fighters_all[ix]
            # mix to 64-bit int then map to float
            h = self._mix(self.seed, f"{a.team_id}:{a.pid}")
            return (h, a.team_id)  # stable tiebreak
        order.sort(key=_key)
        self._turn_order = order
        self._turn_index = 0

        self.round = 1
        self._round_started = False
        self.winner: Optional[int] = None  # 0/1/None

        # Emit first round marker immediately
        self._emit({"type": "round", "round": self.round})
        self._round_started = True

    # ----------------------------- utils ---------------------------------

    def _mix(self, seed: int, text: str) -> int:
        x = (seed ^ 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        for b in text.encode("utf-8"):
            x ^= (b + 0x9E3779B97F4A7C15 + ((x << 6) & 0xFFFFFFFFFFFFFFFF) + (x >> 2))
            x &= 0xFFFFFFFFFFFFFFFF
        return x

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.W and 0 <= y < self.H

    def _is_free(self, x: int, y: int) -> bool:
        return self._in_bounds(x, y) and self._occupy[x][y] is None

    def _place(self, actor: _Actor, x: int, y: int):
        # clear old
        if self._in_bounds(actor.x, actor.y) and self._occupy[actor.x][actor.y] is actor:
            self._occupy[actor.x][actor.y] = None
        actor.x, actor.y = x, y
        self._occupy[x][y] = actor

    def _nearest_free(self, x: int, y: int) -> Tuple[int, int]:
        """Find the nearest free tile to (x,y) using a small ring search."""
        if self._is_free(x, y):
            return x, y
        # ring expansion up to manhattan radius ~ max(W,H)
        max_r = max(self.W, self.H)
        for r in range(1, max_r+1):
            for dx in range(-r, r+1):
                dy = r - abs(dx)
                for sy in (-1, 1) if dy != 0 else (1,):
                    nx, ny = x + dx, y + sy*dy
                    if self._is_free(nx, ny):
                        return nx, ny
        # fallback: search from (0,0)
        for xi in range(self.W):
            for yi in range(self.H):
                if self._is_free(xi, yi):
                    return xi, yi
        # grid full (shouldn't happen with small rosters)
        return max(0, min(x, self.W-1)), max(0, min(y, self.H-1))

    def _emit(self, ev: Dict[str, Any]):
        self.typed_events.append(ev)

    # ----------------------------- layout --------------------------------

    def _layout_teams_tiles(self):
        """
        Left band for team 0 (x in [1..3]), right band for team 1 (x in [W-4..W-2]).
        Rows chosen deterministically from seed + pid.
        Collisions resolved to nearest free.
        """
        left_xs  = list(range(max(0, 1), min(self.W, 4)))
        right_xs = list(range(max(0, self.W-4), max(0, self.W-1)))
        for a in self.fighters_all:
            # propose y from hashed pid
            ry = int(self._mix(self.seed, f"pid:{a.pid}") % self.H)
            if a.team_id == 0:
                rx = left_xs[int(self._mix(self.seed, f"L:{a.pid}") % len(left_xs))] if left_xs else 0
            else:
                rx = right_xs[int(self._mix(self.seed, f"R:{a.pid}") % max(1, len(right_xs)))] if right_xs else self.W-1
            px, py = self._nearest_free(rx, ry)
            self._place(a, px, py)

    # ----------------------------- turn loop ------------------------------

    def _alive(self, team_id: int) -> List[_Actor]:
        return [a for a in self.fighters_all if a.team_id == team_id and a.alive and a.hp > 0]

    def _all_alive(self) -> List[_Actor]:
        return [a for a in self.fighters_all if a.alive and a.hp > 0]

    def _enemies_of(self, actor: _Actor) -> List[_Actor]:
        return [a for a in self.fighters_all if a.team_id != actor.team_id and a.alive and a.hp > 0]

    def _adjacent(self, a: _Actor, b: _Actor) -> bool:
        return abs(a.x - b.x) + abs(a.y - b.y) == 1

    def _step_toward(self, a: _Actor, target: _Actor) -> Tuple[int, int]:
        # one-step Manhattan toward target
        dx = 0 if a.x == target.x else (1 if target.x > a.x else -1)
        dy = 0 if a.y == target.y else (1 if target.y > a.y else -1)
        # prefer horizontal if farther horizontally; deterministic tie by seed
        if abs(target.x - a.x) >= abs(target.y - a.y):
            return a.x + dx, a.y
        else:
            return a.x, a.y + dy

    def _attack_roll(self, attacker: _Actor, defender: _Actor) -> Tuple[bool, int]:
        # lightweight d20 vs AC proxy: d20 + mod >= AC → hit; dmg = 1d4 + mod (min 1)
        roll = self.rng.randint(1, 20)
        mod = max(-2, min(5, (attacker.STR - 10)//2))
        hit = (roll + mod) >= max(8, defender.ac)  # floors AC to 8 so combat resolves
        dmg = max(1, self.rng.randint(1, 4) + mod)
        return hit, dmg

    def _post_attack_down_check(self, attacker: _Actor, defender: _Actor):
        if defender.hp <= 0 and defender.alive:
            defender.alive = False
            self._emit({"type": "down", "name": defender.name})
            # xp to attacker
            attacker.xp = int(getattr(attacker, "xp", 0)) + 1

    def _score_target(self, attacker: _Actor, target: _Actor) -> float:
        # base: closer is better, low HP prey is attractive
        dist = abs(attacker.x - target.x) + abs(attacker.y - target.y)
        base = 100.0 - 10.0*dist - 0.5*target.hp
        # apply optional OI bias
        return float(apply_oi_bias(attacker, target, base))

    def _check_end(self) -> Optional[int]:
        alive0 = len(self._alive(0)) > 0
        alive1 = len(self._alive(1)) > 0
        if alive0 and alive1:
            return None
        if alive0 and not alive1:
            return 0
        if alive1 and not alive0:
            return 1
        # both wiped (rare) → draw
        return None

    # public helper used by tests/UI
    def _move_actor_if_free(self, actor: _Actor, dest_xy: Tuple[int, int]) -> bool:
        x, y = int(dest_xy[0]), int(dest_xy[1])
        if not self._in_bounds(x, y) or not self._is_free(x, y):
            self._emit({"type": "blocked", "name": actor.name, "at": (x, y)})
            return False
        self._place(actor, x, y)
        self._emit({"type": "move", "name": actor.name, "to": (x, y)})
        return True

    def take_turn(self):
        if self.winner is not None:
            return

        # rotate until we find a living actor, or detect empty combat
        for _ in range(len(self._turn_order)):
            ix = self._turn_order[self._turn_index]
            actor = self.fighters_all[ix]
            self._turn_index = (self._turn_index + 1) % len(self._turn_order)
            # on wrap -> new round marker
            if self._turn_index == 0:
                self.round += 1
                self._emit({"type": "round", "round": self.round})

            if actor.alive and actor.hp > 0:
                break
        else:
            # nobody alive -> end
            self.winner = self._check_end()
            self._emit({"type": "end", "winner": self.winner})
            return

        # pick action
        enemies = self._enemies_of(actor)
        if not enemies:
            self.winner = self._check_end()
            self._emit({"type": "end", "winner": self.winner})
            return

        # if adjacent enemy exists, attack the "best" one (deterministic tie)
        adj_enemies = [e for e in enemies if self._adjacent(actor, e)]
        if adj_enemies:
            target = sorted(adj_enemies, key=lambda t: (-self._score_target(actor, t), t.team_id, t.pid))[0]
            hit, dmg = self._attack_roll(actor, target)
            if hit:
                target.hp = max(0, target.hp - dmg)
                self._emit({"type": "hit", "name": actor.name, "target": target.name, "dmg": int(dmg)})
                self._post_attack_down_check(actor, target)
            else:
                self._emit({"type": "miss", "name": actor.name, "target": target.name})
        else:
            # move one step toward best target
            target = sorted(enemies, key=lambda t: (-self._score_target(actor, t), t.team_id, t.pid))[0]
            nx, ny = self._step_toward(actor, target)
            if not self._move_actor_if_free(actor, (nx, ny)):
                # can't move into occupied/out-of-bounds → blocked event already emitted
                pass

        # end check after action
        self.winner = self._check_end()
        if self.winner is not None:
            self._emit({"type": "end", "winner": self.winner})

    # alias for tests
    def step_action(self):
        self.take_turn()
