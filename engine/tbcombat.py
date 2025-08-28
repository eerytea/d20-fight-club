from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# Optional OI bias hook
try:
    from engine.ai import weights as _OI  # apply_oi_bias(attacker, target, base)->score
    def _apply_oi_bias(attacker, target, base: float) -> float:
        try:
            return float(_OI.apply_oi_bias(attacker, target, base))
        except Exception:
            return base
except Exception:
    def _apply_oi_bias(attacker, target, base: float) -> float:
        return base


# ----------------------- Model -----------------------

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


class TBCombat:
    """Tiny, deterministic turn-based combat used by tests.

    Public API expected by tests:
      - TBCombat(teamA, teamB, fighters, grid_w, grid_h, seed=...)
        * grid_w/grid_h can be passed positionally or as kwargs (GRID_W/GRID_H supported)
        * teamA/teamB may be strings or objects; coerced to str for display
      - .typed_events  (aliases: .events_typed, .events)
      - .fighters_all  (alias: .fighters)
      - .take_turn()   (alias: .step_action())
      - ._move_actor_if_free(actor, (x,y)) helper
      - .winner -> 0/1/None
      - .round (1-based); emits {'type':'round'} at start of each round
    """

    def __init__(self, teamA: Any, teamB: Any, fighters: List[Dict[str, Any]], *args, **kwargs):
        # Grid with aliases & positional support
        self.W = int(kwargs.get('grid_w',
                    kwargs.get('GRID_W',
                        args[0] if len(args) >= 1 else kwargs.get('w', 11))))
        self.H = int(kwargs.get('grid_h',
                    kwargs.get('GRID_H',
                        args[1] if len(args) >= 2 else kwargs.get('h', 11))))
        self.seed = int(kwargs.get('seed', 12345))

        self.teamA = str(getattr(teamA, 'name', teamA))
        self.teamB = str(getattr(teamB, 'name', teamB))

        self.rng = random.Random(self.seed)
        self.typed_events: List[Dict[str, Any]] = []
        # aliases
        self.events_typed = self.typed_events
        self.events = self.typed_events

        # Normalize fighters into _Actor objects (tolerant input)
        self.fighters_all: List[_Actor] = []
        positions_were_supplied = False
        for i, f in enumerate(fighters):
            d = dict(f) if isinstance(f, dict) else f.__dict__.copy()
            pid = int(d.get('pid', d.get('id', i)))
            name = str(d.get('name', f'P{pid}'))
            team_id = int(d.get('team_id', d.get('tid', 0)))
            # prefer explicit x/y if present (or tx/ty)
            pos_given = any(k in d for k in ('x','y','tx','ty'))
            positions_were_supplied = positions_were_supplied or pos_given
            x = int(d.get('x', d.get('tx', 0)))
            y = int(d.get('y', d.get('ty', 0)))
            hp = int(d.get('hp', d.get('HP', 10)))
            mx = int(d.get('max_hp', d.get('MAX_HP', hp)))
            ac = int(d.get('ac', d.get('AC', 10)))
            alive = bool(d.get('alive', True))
            role = d.get('role')
            xp = int(d.get('xp', 0))
            STR = int(d.get('STR', 10)); DEX = int(d.get('DEX', 10)); CON = int(d.get('CON', 10))
            INT = int(d.get('INT', 8)); WIS = int(d.get('WIS', 8)); CHA = int(d.get('CHA', 8))
            self.fighters_all.append(_Actor(pid, name, team_id, x, y, hp, mx, ac, alive, role, xp, STR, DEX, CON, INT, WIS, CHA))

        # Occupancy grid
        self._occupy: List[List[Optional[_Actor]]] = [[None for _ in range(self.H)] for __ in range(self.W)]

        # Initial placement:
        # - If any fighter had coordinates supplied, honor them but resolve collisions/out-of-bounds.
        # - Otherwise, auto-layout into left/right bands (collision-free).
        if positions_were_supplied:
            for a in self.fighters_all:
                px, py = self._clamp(a.x, a.y)
                if not self._is_free(px, py):
                    px, py = self._nearest_free(px, py)
                self._place(a, px, py)
        else:
            self._layout_teams_tiles()

        # Initiative order: deterministic from seed + pid + team_id
        order = list(range(len(self.fighters_all)))
        def _key(ix: int):
            a = self.fighters_all[ix]
            h = self._mix(self.seed, f'{a.team_id}:{a.pid}')
            return (h, a.team_id, a.pid)
        order.sort(key=_key)
        self._turn_order = order
        self._turn_index = 0

        self.round = 1
        self.winner: Optional[int] = None

        # Emit first round marker
        self._emit({'type': 'round', 'round': self.round})

    # Property expected by some tests
    @property
    def fighters(self):
        return self.fighters_all

    # ----------------------- utility -----------------------

    def _mix(self, seed: int, text: str) -> int:
        x = (seed ^ 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        for b in text.encode('utf-8'):
            x ^= (b + 0x9E3779B97F4A7C15 + ((x << 6) & 0xFFFFFFFFFFFFFFFF) + (x >> 2))
            x &= 0xFFFFFFFFFFFFFFFF
        return x

    def _clamp(self, x: int, y: int) -> Tuple[int, int]:
        return max(0, min(x, self.W-1)), max(0, min(y, self.H-1))

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.W and 0 <= y < self.H

    def _is_free(self, x: int, y: int) -> bool:
        return self._in_bounds(x, y) and self._occupy[x][y] is None

    def _place(self, actor: _Actor, x: int, y: int):
        # clear old if this actor currently occupies a tile
        if self._in_bounds(actor.x, actor.y) and self._occupy[actor.x][actor.y] is actor:
            self._occupy[actor.x][actor.y] = None
        actor.x, actor.y = x, y
        self._occupy[x][y] = actor

    def _nearest_free(self, x: int, y: int) -> Tuple[int, int]:
        if self._is_free(x, y):
            return x, y
        max_r = max(self.W, self.H)
        for r in range(1, max_r + 1):
            for dx in range(-r, r + 1):
                dy = r - abs(dx)
                for sy in (-1, 1) if dy != 0 else (1,):
                    nx, ny = x + dx, y + sy*dy
                    if self._is_free(nx, ny):
                        return nx, ny
        # fallback (grid full)
        return self._clamp(x, y)

    def _emit(self, ev: Dict[str, Any]):
        self.typed_events.append(ev)

    # ----------------------- layout -----------------------

    def _layout_teams_tiles(self):
        """Place team 0 on the left band, team 1 on the right band, resolving collisions."""
        left_xs  = list(range(max(0, 1), min(self.W, 4)))
        right_xs = list(range(max(0, self.W-4), max(0, self.W-1)))
        for a in self.fighters_all:
            ry = int(self._mix(self.seed, f'pid:{a.pid}') % self.H)
            if a.team_id == 0:
                xs = left_xs or [0]
                rx = xs[int(self._mix(self.seed, f'L:{a.pid}') % len(xs))]
            else:
                xs = right_xs or [max(0, self.W-1)]
                rx = xs[int(self._mix(self.seed, f'R:{a.pid}') % len(xs))]
            px, py = self._nearest_free(rx, ry)
            self._place(a, px, py)

    # ----------------------- turns -----------------------

    def _alive(self, team_id: int) -> List[_Actor]:
        return [a for a in self.fighters_all if a.team_id == team_id and a.alive and a.hp > 0]

    def _all_alive(self) -> List[_Actor]:
        return [a for a in self.fighters_all if a.alive and a.hp > 0]

    def _enemies_of(self, actor: _Actor) -> List[_Actor]:
        return [a for a in self.fighters_all if a.team_id != actor.team_id and a.alive and a.hp > 0]

    def _adjacent(self, a: _Actor, b: _Actor) -> bool:
        return abs(a.x - b.x) + abs(a.y - b.y) == 1

    def _step_toward(self, a: _Actor, target: _Actor) -> Tuple[int, int]:
        dx = 0 if a.x == target.x else (1 if target.x > a.x else -1)
        dy = 0 if a.y == target.y else (1 if target.y > a.y else -1)
        if abs(target.x - a.x) >= abs(target.y - a.y):
            return a.x + dx, a.y
        return a.x, a.y + dy

    def _attack_roll(self, attacker: _Actor, defender: _Actor) -> Tuple[bool, int]:
        roll = self.rng.randint(1, 20)
        mod = max(-2, min(5, (attacker.STR - 10)//2))
        hit = (roll + mod) >= max(8, defender.ac)
        dmg = max(1, self.rng.randint(1, 4) + mod)
        return hit, dmg

    def _post_attack_down_check(self, attacker: _Actor, defender: _Actor):
        if defender.hp <= 0 and defender.alive:
            defender.alive = False
            self._emit({'type': 'down', 'name': defender.name})
            attacker.xp = int(getattr(attacker, 'xp', 0)) + 1

    def _score_target(self, attacker: _Actor, target: _Actor) -> float:
        # Prefer nearby targets; add bias hook
        base = - (abs(attacker.x - target.x) + abs(attacker.y - target.y))
        return _apply_oi_bias(attacker, target, base)

    def _check_end(self) -> Optional[int]:
        a_alive = len(self._alive(0)) > 0
        b_alive = len(self._alive(1)) > 0
        if a_alive and b_alive:
            return None
        if a_alive and not b_alive:
            return 0
        if b_alive and not a_alive:
            return 1
        return None

    def _next_actor_index(self) -> Optional[int]:
        n = len(self._turn_order)
        for _ in range(n):
            ix = self._turn_order[self._turn_index]
            self._turn_index = (self._turn_index + 1) % n
            if self.fighters_all[ix].alive and self.fighters_all[ix].hp > 0:
                return ix
        return None

    def _start_next_round(self):
        self.round += 1
        self._emit({'type': 'round', 'round': self.round})

    def _move_actor_if_free(self, actor: _Actor, dest_xy: Tuple[int, int]) -> bool:
        x, y = int(dest_xy[0]), int(dest_xy[1])
        if not self._in_bounds(x, y) or not self._is_free(x, y):
            self._emit({'type': 'blocked', 'name': actor.name, 'at': (x, y)})
            return False
        self._place(actor, x, y)
        self._emit({'type': 'move', 'name': actor.name, 'to': (x, y)})
        return True

    def take_turn(self):
        if self.winner is not None:
            return

        ix = self._next_actor_index()
        if ix is None:
            # Everyone dead? End.
            self.winner = self._check_end()
            if self.winner is None:
                self._start_next_round()
            return

        actor = self.fighters_all[ix]
        enemies = self._enemies_of(actor)
        if not enemies:
            self.winner = self._check_end()
            if self.winner is None:
                self._start_next_round()
            return

        # If adjacent, swing; else step toward best target
        adj = [e for e in enemies if self._adjacent(actor, e)]
        if adj:
            target = sorted(adj, key=lambda t: (-self._score_target(actor, t), t.team_id, t.pid))[0]
            hit, dmg = self._attack_roll(actor, target)
            if hit:
                target.hp = max(0, target.hp - dmg)
                self._emit({'type': 'hit', 'name': actor.name, 'target': target.name, 'dmg': int(dmg)})
                self._post_attack_down_check(actor, target)
            else:
                self._emit({'type': 'miss', 'name': actor.name, 'target': target.name})
        else:
            target = sorted(enemies, key=lambda t: (-self._score_target(actor, t), t.team_id, t.pid))[0]
            nx, ny = self._step_toward(actor, target)
            if not self._move_actor_if_free(actor, (nx, ny)):
                pass  # blocked emits its own event

        # End check and potential round advance
        prev_winner = self.winner
        self.winner = self._check_end()
        if prev_winner is None and self.winner is None and self._turn_index == 0:
            # completed a full cycle
            self._start_next_round()

    # alias
    def step_action(self):
        self.take_turn()
