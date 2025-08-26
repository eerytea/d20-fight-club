"""
TBCombat — turn-based D20-flavored grid combat engine (single-occupancy enforced)

Public contract (as used elsewhere in the project):
- Constructor: TBCombat(teamA, teamB, fighters, GRID_W, GRID_H, seed=None)
  * teamA/teamB: strings or simple objects used only for display; winner is 0/1
  * fighters: iterable of objects OR dicts with fields/keys:
      pid, name, team_id (0 or 1), x, y, tx, ty, hp, max_hp, alive
- Attributes emitted/used by UI & core:
  * typed_events (alias: events_typed): list of dict events appended over time
    Event shapes (all strings and ints):
      {'type': 'round', 'round': int}
      {'type': 'move', 'name': str, 'to': (x, y)}
      {'type': 'blocked', 'name': str, 'to': (x, y), 'by': str}
      {'type': 'hit', 'name': str, 'target': str, 'dmg': int}
      {'type': 'miss', 'name': str, 'target': str}
      {'type': 'down', 'name': str}  # (target name)
      {'type': 'end'}                # winner available on self.winner
  * winner: 0 or 1 when match ends; None while ongoing
  * GRID_W, GRID_H: ints

How stepping works:
- Call step_action() to perform exactly one actor action (move/attack), appending new events.
- If you prefer to pre-bake, call simulate_all() once, then read typed_events in your viewer.

Determinism:
- All stochastic choices use self.rng (seeded in __init__), NEVER the global random module.

Single-occupancy enforcement:
- Spawn collisions are deterministically nudged to the nearest free tile.
- Moves into occupied tiles do not happen; a typed {'type':'blocked', ...} event is emitted instead.
"""

from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Tuple
import math
import random


Coord = Tuple[int, int]


def _get(obj: Any, key: str, default=None):
    """Attribute/dict accessor (supports both dot-attrs and mapping keys)."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _set(obj: Any, key: str, value: Any) -> None:
    """Attribute/dict setter (supports both dot-attrs and mapping keys)."""
    if isinstance(obj, dict):
        obj[key] = value
    else:
        setattr(obj, key, value)


class TBCombat:
    def __init__(
        self,
        teamA: Any,
        teamB: Any,
        fighters: Iterable[Any],
        GRID_W: int,
        GRID_H: int,
        seed: Optional[int] = None,
    ) -> None:
        self.teamA = teamA
        self.teamB = teamB
        self.GRID_W = int(GRID_W)
        self.GRID_H = int(GRID_H)
        self.rng = random.Random(seed if seed is not None else 0)

        # Normalize fighters list (keep references as given — UI may hold onto them)
        self.fighters: List[Any] = list(fighters)

        # Guarantee team_id is 0/1 (normalize quietly; UI also normalizes in match state)
        for f in self.fighters:
            tid = _get(f, "team_id", 0)
            _set(f, "team_id", 1 if tid in (1, "1", True) else 0)

        # Typed event stream (alias maintained for older code)
        self.typed_events: List[Dict[str, Any]] = []
        self.events_typed = self.typed_events  # alias for compatibility

        self.round: int = 1
        self._started_round: bool = False  # to emit round banner once per round
        self._turn_cursor: int = 0         # index into self._turn_order
        self._build_turn_order()

        # Occupancy and spawn fixups
        self._rebuild_occupied()
        self._fix_spawn_collisions()

        # Match state
        self.winner: Optional[int] = None
        self._ended: bool = False

        # Emit opening round marker immediately for viewer sanity
        self._emit({"type": "round", "round": self.round})
        self._started_round = True

    # ---------- Core loop utilities ----------

    def step_action(self) -> List[Dict[str, Any]]:
        """
        Perform exactly one actor's action (move or attack).
        Returns the list of events appended by this call (convenience).
        """
        if self._ended:
            return []

        start_len = len(self.typed_events)

        # Pick next alive actor (advance turn cursor as needed)
        actor = self._next_actor()
        if actor is None:
            # Round rollover (no alive actors found in this pass)
            self._advance_round()
            actor = self._next_actor()
            if actor is None:
                # Both sides dead? End in a draw: choose winner by kills/hp — keep simple: team 0 wins tie-breaker.
                self._end_match(winner=0)
                return self.typed_events[start_len:]

        # Decide action: if adjacent enemy => attack; else move toward closest enemy
        enemy = self._closest_enemy(actor)
        if enemy is None:
            # No enemies alive: actor's team wins
            self._end_match(winner=_get(actor, "team_id"))
            return self.typed_events[start_len:]

        ax, ay = _get(actor, "x"), _get(actor, "y")
        ex, ey = _get(enemy, "x"), _get(enemy, "y")
        if self._manhattan(ax, ay, ex, ey) == 1:
            self._attack(actor, enemy)
        else:
            self._step_toward(actor, (ex, ey))

        # Check victory after the action
        self._check_victory()

        return self.typed_events[start_len:]

    def simulate_all(self, max_rounds: int = 500) -> None:
        """Run until end or until max_rounds exceeded (safety)."""
        while not self._ended and self.round <= max_rounds:
            self.step_action()
        if not self._ended:
            # Failsafe: end by remaining HP sum
            winner = self._winner_by_hp_sum()
            self._end_match(winner=winner)

    # ---------- Internals ----------

    def _build_turn_order(self) -> None:
        """Deterministic order: by (team_id, pid) so team 0, then 1, alternating by actor index naturally."""
        # Split by team, sort by pid to stabilize
        t0 = [f for f in self.fighters if _get(f, "team_id") == 0]
        t1 = [f for f in self.fighters if _get(f, "team_id") == 1]
        t0.sort(key=lambda f: _get(f, "pid", 0))
        t1.sort(key=lambda f: _get(f, "pid", 0))
        # Interleave to roughly alternate sides
        interleaved: List[Any] = []
        i = 0
        while i < len(t0) or i < len(t1):
            if i < len(t0):
                interleaved.append(t0[i])
            if i < len(t1):
                interleaved.append(t1[i])
            i += 1
        self._turn_order = interleaved
        self._turn_cursor = 0

    def _next_actor(self) -> Optional[Any]:
        """Return next alive actor and advance _turn_cursor to its position. If none alive in this scan, return None."""
        n = len(self._turn_order)
        if n == 0:
            return None
        # Scan at most n entries to find next alive
        for _ in range(n):
            actor = self._turn_order[self._turn_cursor]
            if _get(actor, "alive", True) and _get(actor, "hp", 1) > 0:
                return actor
            # dead -> skip forward
            self._turn_cursor = (self._turn_cursor + 1) % n
        # Nobody alive in the entire order
        return None

    def _advance_turn_cursor(self) -> None:
        n = len(self._turn_order)
        if n:
            self._turn_cursor = (self._turn_cursor + 1) % n
            if self._turn_cursor == 0:
                self._advance_round()

    def _advance_round(self) -> None:
        self.round += 1
        self._started_round = False
        self._emit({"type": "round", "round": self.round})
        self._started_round = True

    # ---------- Movement & Occupancy ----------

    def _rebuild_occupied(self) -> None:
        """Recreate occupied map from alive fighters."""
        self.occupied: Dict[Coord, int] = {}
        for f in self.fighters:
            if not _get(f, "alive", True):
                continue
            key = (_get(f, "x"), _get(f, "y"))
            if key in self.occupied:
                # leave as-is; spawn fixup will resolve
                pass
            else:
                self.occupied[key] = _get(f, "pid")

    def _fix_spawn_collisions(self) -> None:
        """Deterministically nudge spawn collisions to nearest free tiles, and note it with a 'note' event."""
        colliding: Dict[Coord, List[str]] = {}
        seen: Dict[Coord, int] = {}
        for f in self.fighters:
            if not _get(f, "alive", True):
                continue
            xy = (_get(f, "x"), _get(f, "y"))
            pid = _get(f, "pid")
            if xy in seen:
                # need to nudge this fighter
                nx, ny = self._nearest_free(xy)
                # reserve new spot
                self.occupied.pop(xy, None)  # in case it was set
                self.occupied[(nx, ny)] = pid
                _set(f, "x", nx)
                _set(f, "y", ny)
                colliding.setdefault(xy, []).append(_get(f, "name", f"PID{pid}"))
            else:
                seen[xy] = pid

        if colliding:
            # Emit a non-critical note for debugging (UI may ignore)
            self._emit({"type": "note", "msg": f"Spawn collisions resolved: {colliding}"})

    def _nearest_free(self, start_xy: Coord) -> Coord:
        sx, sy = start_xy
        # Spiral/ring search in deterministic order
        maxr = max(self.GRID_W, self.GRID_H) + 2
        if (sx, sy) not in self.occupied and self._in_bounds(sx, sy):
            return sx, sy
        for r in range(1, maxr):
            # top/bottom edges
            for dx in range(-r, r + 1):
                for dy in (-r, r):
                    x, y = sx + dx, sy + dy
                    if self._in_bounds(x, y) and (x, y) not in self.occupied:
                        return x, y
            # left/right edges (skip corners already checked)
            for dy in range(-r + 1, r):
                for dx in (-r, r):
                    x, y = sx + dx, sy + dy
                    if self._in_bounds(x, y) and (x, y) not in self.occupied:
                        return x, y
        # Fallback to start (shouldn't happen on sane grids)
        return sx, sy

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.GRID_W and 0 <= y < self.GRID_H

    def _can_enter(self, x: int, y: int) -> Tuple[bool, Optional[int]]:
        if not self._in_bounds(x, y):
            return False, None
        occ = self.occupied.get((x, y))
        return (occ is None), occ

    def _move_actor_if_free(self, actor: Any, to_xy: Coord) -> bool:
        tx, ty = to_xy
        ok, occ_pid = self._can_enter(tx, ty)
        if not ok:
            by_name = self._name_from_pid(occ_pid)
            self._emit({"type": "blocked", "name": _get(actor, "name", "?"), "to": (tx, ty), "by": by_name})
            # Consume the actor's action even if blocked (classic "bump loses AP")
            self._advance_turn_cursor()
            return False

        # Move: vacate old tile, occupy new
        old = (_get(actor, "x"), _get(actor, "y"))
        self.occupied.pop(old, None)
        _set(actor, "x", tx)
        _set(actor, "y", ty)
        self.occupied[(tx, ty)] = _get(actor, "pid")
        self._emit({"type": "move", "name": _get(actor, "name", "?"), "to": (tx, ty)})
        self._advance_turn_cursor()
        return True

    def _step_toward(self, actor: Any, target_xy: Coord) -> None:
        """Greedy Manhattan approach — choose axis with greater distance; break ties deterministically by X then Y."""
        ax, ay = _get(actor, "x"), _get(actor, "y")
        tx, ty = target_xy
        dx = tx - ax
        dy = ty - ay

        step_x = 0 if dx == 0 else (1 if dx > 0 else -1)
        step_y = 0 if dy == 0 else (1 if dy > 0 else -1)

        # Prefer axis with larger absolute distance; tie-break by X first
        if abs(dx) > abs(dy):
            cand = (ax + step_x, ay)
        elif abs(dy) > abs(dx):
            cand = (ax, ay + step_y)
        else:
            # equal — prefer X then Y deterministically
            cand = (ax + step_x, ay) if step_x != 0 else (ax, ay + step_y)

        self._move_actor_if_free(actor, cand)

    # ---------- Combat ----------

    def _attack(self, actor: Any, enemy: Any) -> None:
        """Very simple D20-ish: roll to-hit; fixed-ish damage range; all via self.rng for determinism."""
        # Consume actor's action regardless of outcome
        self._advance_turn_cursor()

        # To-hit: ~65% chance by default, seeded
        roll = self.rng.random()
        hit = roll < 0.65

        a_name = _get(actor, "name", "?")
        e_name = _get(enemy, "name", "?")

        if not hit:
            self._emit({"type": "miss", "name": a_name, "target": e_name})
            return

        dmg = 1 + int(self.rng.random() * 4)  # 1..4
        self._emit({"type": "hit", "name": a_name, "target": e_name, "dmg": dmg})

        # Apply damage
        new_hp = max(0, _get(enemy, "hp", 0) - dmg)
        _set(enemy, "hp", new_hp)
        if new_hp <= 0 and _get(enemy, "alive", True):
            _set(enemy, "alive", False)
            # Free up the tile immediately
            self.occupied.pop((_get(enemy, "x"), _get(enemy, "y")), None)
            self._emit({"type": "down", "name": e_name})

    # ---------- Victory / Helpers ----------

    def _check_victory(self) -> None:
        a_alive = any(_get(f, "alive", True) and _get(f, "team_id") == 0 for f in self.fighters)
        b_alive = any(_get(f, "alive", True) and _get(f, "team_id") == 1 for f in self.fighters)
        if a_alive and b_alive:
            return
        if a_alive and not b_alive:
            self._end_match(winner=0)
        elif b_alive and not a_alive:
            self._end_match(winner=1)
        else:
            # nobody alive -> tie-break by HP (should be zero), then by team id
            self._end_match(winner=self._winner_by_hp_sum())

    def _winner_by_hp_sum(self) -> int:
        sum0 = sum(_get(f, "hp", 0) for f in self.fighters if _get(f, "team_id") == 0)
        sum1 = sum(_get(f, "hp", 0) for f in self.fighters if _get(f, "team_id") == 1)
        if sum1 > sum0:
            return 1
        return 0

    def _end_match(self, winner: int) -> None:
        if self._ended:
            return
        self.winner = 1 if winner == 1 else 0
        self._emit({"type": "end"})
        self._ended = True

    def _emit(self, ev: Dict[str, Any]) -> None:
        # Keep event list small-ish if someone loops forever elsewhere
        self.typed_events.append(ev)

    def _name_from_pid(self, pid: Optional[int]) -> str:
        if pid is None:
            return "Unknown"
        for f in self.fighters:
            if _get(f, "pid") == pid:
                return _get(f, "name", f"PID{pid}")
        return f"PID{pid}"

    @staticmethod
    def _manhattan(x1: int, y1: int, x2: int, y2: int) -> int:
        return abs(x1 - x2) + abs(y1 - y2)

    def _closest_enemy(self, actor: Any) -> Optional[Any]:
        """Return closest enemy by Manhattan distance; tie-break by lowest pid to be deterministic."""
        ax, ay = _get(actor, "x"), _get(actor, "y")
        my_team = _get(actor, "team_id")
        best = None
        best_key = None
        for f in self.fighters:
            if not _get(f, "alive", True):
                continue
            if _get(f, "team_id") == my_team:
                continue
            dist = self._manhattan(ax, ay, _get(f, "x"), _get(f, "y"))
            key = (dist, _get(f, "pid", 0))
            if best is None or key < best_key:
                best = f
                best_key = key
        return best
