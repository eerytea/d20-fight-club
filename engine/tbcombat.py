# engine/tbcombat.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional, Iterable
import random
import math

# Global grid defaults (UI also uses 11×11 as the common baseline)
GRID_W = 11
GRID_H = 11

Coord = Tuple[int, int]


# -------------------- data models --------------------

@dataclass
class Team:
    tid: int
    name: str
    color: Tuple[int, int, int] = (220, 220, 220)


@dataclass
class Fighter:
    pid: int
    name: str
    team_id: int            # MUST be 0 or 1 for engine/UI
    x: int
    y: int
    tx: int
    ty: int
    hp: int
    max_hp: int
    alive: bool = True
    # optional, used by tests and progression
    ac: int = 10
    spd: int = 1
    xp: int = 0

    @property
    def pos(self) -> Coord:
        return (self.x, self.y)

    def set_pos(self, xy: Coord) -> None:
        self.x, self.y = xy
        self.tx, self.ty = xy


# -------------------- helpers used by tests --------------------

def fighter_from_dict(d: Dict) -> Fighter:
    """Create a Fighter from a flexible dict used by tests and content."""
    return Fighter(
        pid=int(d.get("pid", d.get("id", 0))),
        name=str(d.get("name", "Unit")),
        team_id=int(d.get("team_id", d.get("tid", 0))),
        x=int(d.get("x", d.get("tx", 0))),
        y=int(d.get("y", d.get("ty", 0))),
        tx=int(d.get("tx", d.get("x", 0))),
        ty:int(d.get("ty", d.get("y", 0))),
        hp=int(d.get("hp", d.get("max_hp", 10))),
        max_hp=int(d.get("max_hp", d.get("hp", 10))),
        ac=int(d.get("ac", 10)),
        spd=int(d.get("spd", 1)),
        xp=int(d.get("xp", 0)),
    )


def layout_teams_tiles(fighters: List[Fighter], W: int, H: int) -> None:
    """
    Deterministic lineup: team 0 on the left column band, team 1 on the right.
    We ensure no overlap at spawn (engine enforces single occupancy again in combat).
    """
    left_x = 1
    right_x = max(0, W - 2)

    t0 = [f for f in fighters if f.team_id == 0]
    t1 = [f for f in fighters if f.team_id == 1]

    # space vertically
    def positions(xs: int, count: int) -> List[Coord]:
        if count <= 0:
            return []
        gap = max(1, (H - 2) // max(1, count))
        top = 1
        ys = [min(H - 2, top + i * gap) for i in range(count)]
        return [(xs, y) for y in ys]

    for f, pos in zip(t0, positions(left_x, len(t0))):
        f.set_pos(pos)
    for f, pos in zip(t1, positions(right_x, len(t1))):
        f.set_pos(pos)


# -------------------- combat engine --------------------

class TBCombat:
    """
    Minimal, deterministic TB combat engine with:
      - single-occupancy grid enforcement
      - typed events: round/move/hit/miss/down/end
      - take_turn() that either moves or attacks
      - XP awarded (+1) to attacker when a defender is downed

    API expected by UI/tests:
      TBCombat(teamA, teamB, fighters, GRID_W, GRID_H, seed=...)
      .typed_events  (list of dict events)
      .events_typed  (alias)
      .events        (alias)
      .winner        (0/1 or None)
      .take_turn()
      .step_action() (alias to take_turn)
    """
    def __init__(self,
                 teamA: Team,
                 teamB: Team,
                 fighters: List[Fighter],
                 grid_w: int,
                 grid_h: int,
                 seed: Optional[int] = None):
        self.teamA = teamA
        self.teamB = teamB
        self.GRID_W = int(grid_w)
        self.GRID_H = int(grid_h)
        self.rng = random.Random(seed if seed is not None else 12345)

        # normalize team ids to 0/1 defensively
        for f in fighters:
            if f.team_id not in (0, 1):
                f.team_id = 0 if f.team_id in (teamA.tid, 0) else 1

        self.fighters: List[Fighter] = fighters[:]
        self.typed_events: List[Dict] = []
        self.events_typed = self.typed_events
        self.events = self.typed_events

        self._round = 1
        self._order: List[int] = self._build_turn_order()  # indices into self.fighters
        self._idx = 0
        self.winner: Optional[int] = None

        # occupancy fix for spawns
        self._fix_spawn_collisions()

        # announce first round
        self._emit_round()

    # -------- occupancy & geometry --------

    @property
    def occupied(self) -> Dict[Coord, int]:
        occ: Dict[Coord, int] = {}
        for i, f in enumerate(self.fighters):
            if f.alive:
                occ[(f.x, f.y)] = i
        return occ

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.GRID_W and 0 <= y < self.GRID_H

    def _distance(self, a: Coord, b: Coord) -> int:
        return abs(a[0]-b[0]) + abs(a[1]-b[1])

    def _adjacent(self, a: Coord, b: Coord) -> bool:
        return self._distance(a, b) == 1

    def _nearest_free(self, start_xy: Coord) -> Coord:
        sx, sy = start_xy
        maxr = max(self.GRID_W, self.GRID_H) + 2
        occ = set(self.occupied.keys())
        if (sx, sy) not in occ and self._in_bounds(sx, sy):
            return (sx, sy)
        for r in range(1, maxr):
            for dx in range(-r, r + 1):
                for dy in (-r, r):
                    x, y = sx + dx, sy + dy
                    if self._in_bounds(x, y) and (x, y) not in occ:
                        return (x, y)
            for dy in range(-r + 1, r):
                for dx in (-r, r):
                    x, y = sx + dx, sy + dy
                    if self._in_bounds(x, y) and (x, y) not in occ:
                        return (x, y)
        # as absolute fallback
        for y in range(self.GRID_H):
            for x in range(self.GRID_W):
                if (x, y) not in occ:
                    return (x, y)
        return start_xy

    def _fix_spawn_collisions(self) -> None:
        seen = {}
        for i, f in enumerate(self.fighters):
            if not f.alive:
                continue
            xy = (f.x, f.y)
            if not self._in_bounds(f.x, f.y):
                f.set_pos((min(self.GRID_W-1, max(0, f.x)),
                           min(self.GRID_H-1, max(0, f.y))))
                xy = f.pos
            if xy in seen:
                # move this fighter to nearest free
                nx, ny = self._nearest_free(xy)
                f.set_pos((nx, ny))
            else:
                seen[xy] = i

    # -------- turn logic --------

    def _build_turn_order(self) -> List[int]:
        # deterministic by (team_id, pid) so tests are stable
        order = list(range(len(self.fighters)))
        order.sort(key=lambda i: (self.fighters[i].team_id, self.fighters[i].pid))
        return order

    def _emit_round(self) -> None:
        self.typed_events.append({"type": "round", "round": self._round})

    def _emit_end_if_finished(self) -> None:
        a_alive = any(f.alive and f.team_id == 0 for f in self.fighters)
        b_alive = any(f.alive and f.team_id == 1 for f in self.fighters)
        if not a_alive and not b_alive:
            self.winner = None  # draw
            self.typed_events.append({"type": "end"})
        elif not a_alive:
            self.winner = 1
            self.typed_events.append({"type": "end"})
        elif not b_alive:
            self.winner = 0
            self.typed_events.append({"type": "end"})

    def _advance_index(self) -> None:
        # move to next alive actor; if we looped, new round
        n = len(self._order)
        for _ in range(n):
            self._idx = (self._idx + 1) % n
            i = self._order[self._idx]
            f = self.fighters[i]
            if f.alive:
                if self._idx == 0:
                    self._round += 1
                    self._emit_round()
                return
        # nobody alive on either side ends game
        self._emit_end_if_finished()

    def _award_xp(self, fighter: Fighter, amount: int = 1) -> None:
        """Give XP to the fighter (defensive against missing attribute)."""
        try:
            fighter.xp = int(getattr(fighter, "xp", 0)) + int(amount)
        except Exception:
            pass

    # movement try: one step toward target if free
    def _try_step_toward(self, actor: Fighter, target: Fighter) -> bool:
        ax, ay = actor.x, actor.y
        tx, ty = target.x, target.y
        cand: List[Coord] = []

        dx = 1 if tx > ax else (-1 if tx < ax else 0)
        dy = 1 if ty > ay else (-1 if ty < ay else 0)

        # prefer axis that reduces distance most
        if dx != 0:
            cand.append((ax + dx, ay))
        if dy != 0:
            cand.append((ax, ay + dy))

        # add simple alternatives
        cand.extend([(ax+1, ay), (ax-1, ay), (ax, ay+1), (ax, ay-1)])

        occ = set(self.occupied.keys())
        for (nx, ny) in cand:
            if self._in_bounds(nx, ny) and (nx, ny) not in occ:
                actor.set_pos((nx, ny))
                self.typed_events.append({"type": "move", "name": actor.name, "to": (nx, ny)})
                return True
        # blocked
        return False

    def _attack(self, attacker: Fighter, defender: Fighter) -> None:
        # very simple d20 vs AC
        roll = self.rng.randint(1, 20)
        hit = roll >= max(5, int(defender.ac) // 2 + 5)  # keep hit rate reasonable
        if hit:
            dmg = max(1, self.rng.randint(1, 6))
            defender.hp = max(0, defender.hp - dmg)
            self.typed_events.append({"type": "hit", "name": attacker.name,
                                      "target": defender.name, "dmg": dmg})
            if defender.hp <= 0 and defender.alive:
                defender.alive = False
                self.typed_events.append({"type": "down", "name": defender.name})
                # >>> Award XP to attacker on down (fixes unit test) <<<
                self._award_xp(attacker, 1)
                # ensure tile is now free (defender disappears)
                self._emit_end_if_finished()
        else:
            self.typed_events.append({"type": "miss", "name": attacker.name,
                                      "target": defender.name})

    def _closest_enemy(self, actor: Fighter) -> Optional[Fighter]:
        foes = [f for f in self.fighters if f.alive and f.team_id != actor.team_id]
        if not foes:
            return None
        foes.sort(key=lambda f: (self._distance(actor.pos, f.pos), f.pid))
        return foes[0]

    def take_turn(self) -> None:
        """Perform one atomic action for the current actor."""
        if self.winner is not None:
            return

        # choose current alive actor; if dead, advance to next alive
        for _ in range(len(self._order)):
            idx = self._order[self._idx]
            actor = self.fighters[idx]
            if actor.alive:
                break
            self._advance_index()
        else:
            self._emit_end_if_finished()
            return

        target = self._closest_enemy(actor)
        if target is None:
            self._emit_end_if_finished()
            return

        if self._adjacent(actor.pos, target.pos):
            self._attack(actor, target)
        else:
            moved = self._try_step_toward(actor, target)
            if not moved:
                # blocked: no-op turn to avoid deadlock but still advance
                self.typed_events.append({"type": "move", "name": actor.name, "to": actor.pos})

        # advance to next actor, maybe new round
        self._advance_index()

    # historical alias some UIs called
    def step_action(self) -> None:
        self.take_turn()
