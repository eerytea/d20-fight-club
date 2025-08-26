# engine/tbcombat.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import random

# Default grid (UI often uses 11×11; tests may override via kwargs)
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


# -------------------- helpers used by tests/content --------------------

def fighter_from_dict(d: Dict) -> Fighter:
    """Create a Fighter from a flexible dict used by tests and content."""
    return Fighter(
        pid=int(d.get("pid", d.get("id", 0))),
        name=str(d.get("name", "Unit")),
        team_id=int(d.get("team_id", d.get("tid", 0))),
        x=int(d.get("x", d.get("tx", 0))),
        y=int(d.get("y", d.get("ty", 0))),
        tx=int(d.get("tx", d.get("x", 0))),
        ty=int(d.get("ty", d.get("y", 0))),
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

    t0 = [f for f in fighters if _get_team_id(f) == 0]
    t1 = [f for f in fighters if _get_team_id(f) == 1]

    def positions(xs: int, count: int) -> List[Coord]:
        if count <= 0:
            return []
        gap = max(1, (H - 2) // max(1, count))
        top = 1
        ys = [min(H - 2, top + i * gap) for i in range(count)]
        return [(xs, y) for y in ys]

    for f, pos in zip(t0, positions(left_x, len(t0))):
        _set_pos(f, pos)
    for f, pos in zip(t1, positions(right_x, len(t1))):
        _set_pos(f, pos)


# -------------------- generic field helpers (robust to plain objects/dicts) --------------------

def _getattr_or_key(o, k, default=None):
    if isinstance(o, dict):
        return o.get(k, default)
    return getattr(o, k, default)

def _setattr_or_key(o, k, v):
    if isinstance(o, dict):
        o[k] = v
    else:
        try:
            setattr(o, k, v)
        except Exception:
            # object may be slot/frozen; ignore
            pass

def _get_team_id(f) -> int:
    v = _getattr_or_key(f, "team_id", None)
    if v is None:
        v = _getattr_or_key(f, "tid", None)
    if v is None:
        v = _getattr_or_key(f, "team", 0)
    try:
        return int(v)
    except Exception:
        return 0

def _is_alive(f) -> bool:
    v = _getattr_or_key(f, "alive", True)
    try:
        return bool(v)
    except Exception:
        return True

def _set_alive(f, alive: bool) -> None:
    _setattr_or_key(f, "alive", bool(alive))

def _get_pos(f) -> Coord:
    x = _getattr_or_key(f, "x", _getattr_or_key(f, "tx", 0))
    y = _getattr_or_key(f, "y", _getattr_or_key(f, "ty", 0))
    try:
        return (int(x), int(y))
    except Exception:
        return (0, 0)

def _set_pos(f, xy: Coord) -> None:
    if hasattr(f, "set_pos"):
        try:
            f.set_pos(xy)  # type: ignore[attr-defined]
            return
        except Exception:
            pass
    # fallback: direct fields / dict
    _setattr_or_key(f, "x", int(xy[0]))
    _setattr_or_key(f, "y", int(xy[1]))
    _setattr_or_key(f, "tx", int(xy[0]))
    _setattr_or_key(f, "ty", int(xy[1]))

def _get_name(f) -> str:
    n = _getattr_or_key(f, "name", None)
    if n is None:
        n = f"Unit{_getattr_or_key(f, 'pid', _getattr_or_key(f, 'id', ''))}"
    return str(n)

def _get_hp(f) -> int:
    return int(_getattr_or_key(f, "hp", _getattr_or_key(f, "max_hp", 1)))

def _set_hp(f, hp: int) -> None:
    _setattr_or_key(f, "hp", int(hp))


# -------------------- combat engine --------------------

class TBCombat:
    """
    Deterministic TB combat engine with:
      - single-occupancy grid enforcement (spawn + movement)
      - typed events: round / move / hit / miss / down / blocked / end
      - take_turn() that either moves or attacks
      - XP awarded (+1) to attacker when a defender is downed

    API used by tests/UI:
      TBCombat(teamA, teamB, fighters, grid_w, grid_h, seed=...)
      (also accepts GRID_W/GRID_H kw aliases and string team names)
      .typed_events  (list of dict events)
      .events_typed  (alias)
      .events        (alias)
      .winner        (0/1 or None)
      .take_turn()
      .step_action() (alias to take_turn)
      ._move_actor_if_free(actor, dest_xy)  # used in tests
    """
    def __init__(self,
                 teamA,
                 teamB,
                 fighters: List,
                 grid_w: Optional[int] = None,
                 grid_h: Optional[int] = None,
                 seed: Optional[int] = None,
                 **kwargs):
        # Accept legacy/alias kwargs used in tests: GRID_W/GRID_H
        if grid_w is None:
            grid_w = kwargs.pop("GRID_W", GRID_W)
        if grid_h is None:
            grid_h = kwargs.pop("GRID_H", GRID_H)

        # Accept strings for team names in tests
        if not isinstance(teamA, Team):
            teamA = Team(0, str(teamA))
        if not isinstance(teamB, Team):
            teamB = Team(1, str(teamB))

        self.teamA = teamA
        self.teamB = teamB
        self.GRID_W = int(grid_w)
        self.GRID_H = int(grid_h)
        self.rng = random.Random(seed if seed is not None else 12345)

        # normalize team ids to 0/1 defensively
        normd: List = []
        for f in fighters:
            tid_like = _get_team_id(f)
            if tid_like not in (0, 1):
                # Map by original tid against our team tids; else default by sign
                tid_like = 0 if tid_like in (teamA.tid, 0) else 1
            _setattr_or_key(f, "team_id", tid_like)
            normd.append(f)
        self.fighters = normd

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
            if _is_alive(f):
                occ[_get_pos(f)] = i
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
        # fallback
        for y in range(self.GRID_H):
            for x in range(self.GRID_W):
                if (x, y) not in occ:
                    return (x, y)
        return start_xy

    def _fix_spawn_collisions(self) -> None:
        seen = {}
        for i, f in enumerate(self.fighters):
            if not _is_alive(f):
                continue
            x, y = _get_pos(f)
            if not self._in_bounds(x, y):
                _set_pos(f, (min(self.GRID_W-1, max(0, x)),
                             min(self.GRID_H-1, max(0, y))))
                x, y = _get_pos(f)
            xy = (x, y)
            if xy in seen:
                nx, ny = self._nearest_free(xy)
                _set_pos(f, (nx, ny))
            else:
                seen[xy] = i

    # -------- turn logic --------

    def _build_turn_order(self) -> List[int]:
        # deterministic by (team_id, pid/id/index) so tests are stable
        order = list(range(len(self.fighters)))
        def _key(i: int):
            f = self.fighters[i]
            pid = _getattr_or_key(f, "pid", _getattr_or_key(f, "id", i))
            return (_get_team_id(f), pid)
        order.sort(key=_key)
        return order

    def _emit_round(self) -> None:
        self.typed_events.append({"type": "round", "round": self._round})

    def _emit_end_if_finished(self) -> None:
        a_alive = any(_is_alive(f) and _get_team_id(f) == 0 for f in self.fighters)
        b_alive = any(_is_alive(f) and _get_team_id(f) == 1 for f in self.fighters)
        if not a_alive and not b_alive:
            self.winner = None
            self.typed_events.append({"type": "end"})
        elif not a_alive:
            self.winner = 1
            self.typed_events.append({"type": "end"})
        elif not b_alive:
            self.winner = 0
            self.typed_events.append({"type": "end"})

    def _advance_index(self) -> None:
        n = len(self._order)
        for _ in range(n):
            self._idx = (self._idx + 1) % n
            i = self._order[self._idx]
            f = self.fighters[i]
            if _is_alive(f):
                if self._idx == 0:
                    self._round += 1
                    self._emit_round()
                return
        self._emit_end_if_finished()

    def _award_xp(self, fighter, amount: int = 1) -> None:
        """Give XP to the fighter (defensive against missing attribute)."""
        try:
            cur = int(_getattr_or_key(fighter, "xp", 0))
            _setattr_or_key(fighter, "xp", cur + int(amount))
        except Exception:
            pass

    # --- occupancy helper expected by tests ---
    def _move_actor_if_free(self, actor, dest_xy: Coord) -> bool:
        """Internal: move actor to dest if tile is free; otherwise emit 'blocked' and return False."""
        x, y = dest_xy
        if not self._in_bounds(x, y):
            self.typed_events.append({"type": "blocked", "name": _get_name(actor), "at": _get_pos(actor)})
            return False
        occ = set(self.occupied.keys())
        if (x, y) in occ:
            self.typed_events.append({"type": "blocked", "name": _get_name(actor), "at": _get_pos(actor)})
            return False
        _set_pos(actor, (x, y))
        self.typed_events.append({"type": "move", "name": _get_name(actor), "to": (x, y)})
        return True

    def _try_step_toward(self, actor, target) -> bool:
        ax, ay = _get_pos(actor)
        tx, ty = _get_pos(target)
        cand: List[Coord] = []

        dx = 1 if tx > ax else (-1 if tx < ax else 0)
        dy = 1 if ty > ay else (-1 if ty < ay else 0)

        if dx != 0:
            cand.append((ax + dx, ay))
        if dy != 0:
            cand.append((ax, ay + dy))
        cand.extend([(ax+1, ay), (ax-1, ay), (ax, ay+1), (ax, ay-1)])

        for (nx, ny) in cand:
            if self._move_actor_if_free(actor, (nx, ny)):
                return True
        return False  # blocked events already emitted

    def _attack(self, attacker, defender) -> None:
        # very simple d20 vs AC proxy
        def_ac = int(_getattr_or_key(defender, "ac", 10))
        roll = self.rng.randint(1, 20)
        hit = roll >= max(5, def_ac // 2 + 5)
        if hit:
            dmg = max(1, self.rng.randint(1, 6))
            hp_after = max(0, _get_hp(defender) - dmg)
            _set_hp(defender, hp_after)
            self.typed_events.append({"type": "hit", "name": _get_name(attacker),
                                      "target": _get_name(defender), "dmg": dmg})
            if hp_after <= 0 and _is_alive(defender):
                _set_alive(defender, False)
                self.typed_events.append({"type": "down", "name": _get_name(defender)})
                # award XP to attacker on down (fixes unit test)
                self._award_xp(attacker, 1)
                self._emit_end_if_finished()
        else:
            self.typed_events.append({"type": "miss", "name": _get_name(attacker),
                                      "target": _get_name(defender)})

    def _closest_enemy(self, actor):
        foes = [f for f in self.fighters if _is_alive(f) and _get_team_id(f) != _get_team_id(actor)]
        if not foes:
            return None
        def _pidlike(f):
            return _getattr_or_key(f, "pid", _getattr_or_key(f, "id", 0))
        foes.sort(key=lambda f: (self._distance(_get_pos(actor), _get_pos(f)), _pidlike(f)))
        return foes[0]

    def _distance(self, a: Coord, b: Coord) -> int:
        return abs(a[0]-b[0]) + abs(a[1]-b[1])

    def _adjacent(self, a: Coord, b: Coord) -> bool:
        return self._distance(a, b) == 1

    def take_turn(self) -> None:
        """Perform one atomic action for the current actor."""
        if self.winner is not None:
            return

        # choose current alive actor; if dead, advance to next alive
        for _ in range(len(self._order)):
            idx = self._order[self._idx]
            actor = self.fighters[idx]
            if _is_alive(actor):
                break
            self._advance_index()
        else:
            self._emit_end_if_finished()
            return

        target = self._closest_enemy(actor)
        if target is None:
            self._emit_end_if_finished()
            return

        if self._adjacent(_get_pos(actor), _get_pos(target)):
            self._attack(actor, target)
        else:
            self._try_step_toward(actor, target)

        self._advance_index()

    # historical alias some UIs called
    def step_action(self) -> None:
        self.take_turn()
