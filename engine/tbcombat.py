from __future__ import annotations

import random
from dataclasses import dataclass
from math import inf
from typing import Any, Dict, Iterable, List, Optional, Tuple

# OI bias for target selection
try:
    from core.usecases.integration_points import apply_oi_to_scores
    from engine.tactics.opposition import OppositionInstruction  # only for type hints / setting attr
except Exception:
    def apply_oi_to_scores(base_scores, enemy_units, oi_list):  # graceful fallback
        return base_scores

# -------------------------------
# Fighter adapter & utilities
# -------------------------------

@dataclass
class _FProxy:
    """Adapter that tolerates dicts, objects, or dataclasses with varied fields."""
    _src: Any

    @property
    def pid(self) -> int:
        return int(getattr(self._src, "pid", getattr(self._src, "id", getattr(self._src, "index", 0))))

    @pid.setter
    def pid(self, v: int) -> None:
        if isinstance(self._src, dict):
            self._src["pid"] = v
        else:
            setattr(self._src, "pid", v)

    @property
    def name(self) -> str:
        return str(getattr(self._src, "name", getattr(self._src, "n", f"U{self.pid}")))

    @property
    def team_id(self) -> int:
        # 0 or 1
        return int(getattr(self._src, "team_id", getattr(self._src, "tid", getattr(self._src, "team", 0))))

    @property
    def x(self) -> int:
        return int(getattr(self._src, "x", getattr(self._src, "tx", 0)))

    @x.setter
    def x(self, v: int) -> None:
        if isinstance(self._src, dict):
            self._src["x"] = v
        else:
            setattr(self._src, "x", v)

    @property
    def y(self) -> int:
        return int(getattr(self._src, "y", getattr(self._src, "ty", 0)))

    @y.setter
    def y(self, v: int) -> None:
        if isinstance(self._src, dict):
            self._src["y"] = v
        else:
            setattr(self._src, "y", v)

    @property
    def alive(self) -> bool:
        return bool(getattr(self._src, "alive", getattr(self._src, "is_alive", True)))

    @alive.setter
    def alive(self, v: bool) -> None:
        if isinstance(self._src, dict):
            self._src["alive"] = v
        else:
            setattr(self._src, "alive", v)

    @property
    def hp(self) -> int:
        return int(getattr(self._src, "hp", getattr(self._src, "HP", 10)))

    @hp.setter
    def hp(self, v: int) -> None:
        if isinstance(self._src, dict):
            self._src["hp"] = v
        else:
            setattr(self._src, "hp", v)

    @property
    def max_hp(self) -> int:
        return int(getattr(self._src, "max_hp", getattr(self._src, "HP_max", max(10, self.hp))))

    @property
    def ac(self) -> int:
        return int(getattr(self._src, "ac", getattr(self._src, "AC", 10)))

    @property
    def spd(self) -> int:
        return int(getattr(self._src, "spd", getattr(self._src, "move", 1)))  # tiles/turn (v1=1)

    @property
    def role(self) -> Optional[str]:
        return getattr(self._src, "role", getattr(self._src, "position", None))

    def add_xp(self, amt: int) -> None:
        if isinstance(self._src, dict):
            self._src["xp"] = int(self._src.get("xp", 0)) + amt
        else:
            curr = int(getattr(self._src, "xp", 0))
            setattr(self._src, "xp", curr + amt)


def _m_dist(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# -------------------------------
# TBCombat (single-occupancy)
# -------------------------------

class TBCombat:
    """
    Minimal, deterministic TB engine:
      - single occupancy
      - simple pathing: step toward nearest enemy
      - d20 vs AC hit model
      - typed events stream
    Contract compatibility:
      - constructor: TBCombat(teamA, teamB, fighters, grid_w, grid_h, seed=..., **aliases)
      - .typed_events (.events_typed/.events aliases)
      - .take_turn() (alias .step_action())
      - emits: round, move, hit, miss, down, blocked, end
      - sets .winner to 0/1/None
    """

    def __init__(self,
                 teamA: Any,
                 teamB: Any,
                 fighters: Iterable[Any],
                 grid_w: int = 11,
                 grid_h: int = 11,
                 seed: Optional[int] = None,
                 **kwargs):
        # Accept kw aliases GRID_W/GRID_H
        grid_w = int(kwargs.get("GRID_W", grid_w))
        grid_h = int(kwargs.get("GRID_H", grid_h))
        self.W = grid_w
        self.H = grid_h

        self.teamA = teamA
        self.teamB = teamB
        self.seed = seed if seed is not None else 12345
        self.rng = random.Random(int(self.seed) & 0xFFFFFFFF)

        # Normalize fighters
        self.fighters_all: List[_FProxy] = []
        for i, f in enumerate(list(fighters)):
            fp = _FProxy(f)
            if getattr(f, "pid", None) is None and (isinstance(f, dict) and "pid" not in f):
                fp.pid = i
            if getattr(f, "alive", None) is None and (isinstance(f, dict) and "alive" not in f):
                fp.alive = True
            self.fighters_all.append(fp)

        # Split by team
        self.team0 = [f for f in self.fighters_all if f.team_id == 0]
        self.team1 = [f for f in self.fighters_all if f.team_id == 1]

        # Spawn layout (repair overlaps; left/right bands)
        self._layout_spawn_bands(self.team0, side="left")
        self._layout_spawn_bands(self.team1, side="right")
        self._occupy = {(f.x, f.y): f.pid for f in self.fighters_all if f.alive}

        # Turn queue deterministic by pid then team then name
        self._turn_ix = 0
        self.turn_order = sorted(
            [f for f in self.fighters_all if f.alive],
            key=lambda z: (z.team_id, z.pid, z.name)
        )

        # Events & state
        self.typed_events: List[Dict[str, Any]] = []
        self.events_typed = self.typed_events   # alias
        self.events = self.typed_events         # alias
        self.round = 1
        self.winner: Optional[int] = None

        # Optional: opposition instructions holder (list[OppositionInstruction])
        self.opposition_instructions: List[Any] = getattr(self, "opposition_instructions", [])

        # Emit round start
        self._emit({"type": "round", "round": self.round})

    # --- layout / occupancy helpers -----------------------------------------

    def _layout_spawn_bands(self, team: List[_FProxy], side: str = "left") -> None:
        """Assign spawn positions; if provided x/y exist, keep but resolve overlaps."""
        used: set[Tuple[int, int]] = set()
        band_x = 1 if side == "left" else max(0, self.W - 2)
        y = 1
        for f in team:
            # keep existing if in-bounds & unique
            if 0 <= f.x < self.W and 0 <= f.y < self.H and (f.x, f.y) not in used:
                used.add((f.x, f.y))
                continue
            # otherwise place in band, resolving collisions
            nx, ny = band_x, y
            while (nx, ny) in used or not (0 <= nx < self.W and 0 <= ny < self.H):
                ny += 1
                if ny >= self.H - 1:
                    ny = 1
                    nx += -1 if side == "right" else 1
                    if nx <= 0 or nx >= self.W - 1:
                        nx = max(1, min(self.W - 2, nx))
                        break
            f.x, f.y = nx, ny
            used.add((nx, ny))

    def _is_free(self, xy: Tuple[int, int]) -> bool:
        return 0 <= xy[0] < self.W and 0 <= xy[1] < self.H and self._occupy.get(xy) is None

    def _move_actor_if_free(self, actor: _FProxy, dest_xy: Tuple[int, int]) -> bool:
        """Public helper (used by tests)."""
        if not self._is_free(dest_xy):
            self._emit({"type": "blocked", "name": actor.name, "at": dest_xy})
            return False
        self._occupy.pop((actor.x, actor.y), None)
        actor.x, actor.y = dest_xy
        self._occupy[(actor.x, actor.y)] = actor.pid
        self._emit({"type": "move", "name": actor.name, "to": (actor.x, actor.y)})
        return True

    # --- events --------------------------------------------------------------

    def _emit(self, ev: Dict[str, Any]) -> None:
        self.typed_events.append(ev)

    # --- main loop -----------------------------------------------------------

    def _alive_team(self, tid: int) -> List[_FProxy]:
        group = self.team0 if tid == 0 else self.team1
        return [f for f in group if f.alive and f.hp > 0]

    def _nearest_enemy(self, actor: _FProxy, enemies: List[_FProxy]) -> Optional[_FProxy]:
        if not enemies:
            return None
        best = None
        best_d = inf
        for e in enemies:
            d = _m_dist((actor.x, actor.y), (e.x, e.y))
            if d < best_d:
                best_d = d
                best = e
        return best

    def _choose_target_for(self, actor: _FProxy, enemies: List[_FProxy]) -> Optional[_FProxy]:
        """Base: closer is better; then apply Opposition Instructions to bias."""
        base_scores: Dict[int, float] = {}
        enemy_dicts: List[Dict[str, Any]] = []
        for e in enemies:
            pid = int(e.pid)
            dist = max(1, _m_dist((actor.x, actor.y), (e.x, e.y)))
            base_scores[pid] = 1.0 / dist  # closer -> higher
            enemy_dicts.append({
                "pid": pid,
                "role": e.role,
                "DEX": getattr(e._src, "DEX", None) if not isinstance(e._src, dict) else e._src.get("DEX"),
                "WIS": getattr(e._src, "WIS", None) if not isinstance(e._src, dict) else e._src.get("WIS"),
                "STR": getattr(e._src, "STR", None) if not isinstance(e._src, dict) else e._src.get("STR"),
            })
        oi_list = getattr(self, "opposition_instructions", []) or []
        try:
            scored = apply_oi_to_scores(base_scores, enemy_dicts, oi_list)
        except Exception:
            scored = base_scores
        best_pid = max(scored, key=scored.get, default=None)
        if best_pid is None:
            return self._nearest_enemy(actor, enemies)
        for e in enemies:
            if e.pid == best_pid:
                return e
        return self._nearest_enemy(actor, enemies)

    def _attack(self, attacker: _FProxy, defender: _FProxy) -> None:
        d20 = self.rng.randint(1, 20)
        atk = d20  # lightweight proxy; extend with STR/DEX mods later
        if atk >= defender.ac or d20 == 20:
            dmg = self.rng.randint(1, 6) + (1 if d20 == 20 else 0)
            defender.hp = max(0, defender.hp - dmg)
            self._emit({"type": "hit", "name": attacker.name, "target": defender.name, "dmg": int(dmg)})
            if defender.hp <= 0 and defender.alive:
                defender.alive = False
                self._occupy.pop((defender.x, defender.y), None)
                self._emit({"type": "down", "name": defender.name})
                attacker.add_xp(1)  # XP on down
        else:
            self._emit({"type": "miss", "name": attacker.name, "target": defender.name})

    def _step_actor(self, actor: _FProxy) -> None:
        enemies = self._alive_team(1 if actor.team_id == 0 else 0)
        if not enemies:
            return
        tgt = self._choose_target_for(actor, enemies)
        if not tgt:
            return
        # If adjacent, attack
        if _m_dist((actor.x, actor.y), (tgt.x, tgt.y)) == 1:
            self._attack(actor, tgt)
            return
        # else move one step toward target (4-way)
        dx = 1 if tgt.x > actor.x else (-1 if tgt.x < actor.x else 0)
        dy = 1 if tgt.y > actor.y else (-1 if tgt.y < actor.y else 0)
        # prefer horizontal if farther; simple priority
        cand = []
        if abs(tgt.x - actor.x) >= abs(tgt.y - actor.y) and dx != 0:
            cand.append((actor.x + dx, actor.y))
            if dy != 0:
                cand.append((actor.x, actor.y + dy))
        else:
            if dy != 0:
                cand.append((actor.x, actor.y + dy))
            if dx != 0:
                cand.append((actor.x + dx, actor.y))
        for nx, ny in cand:
            if self._is_free((nx, ny)):
                self._move_actor_if_free(actor, (nx, ny))
                return
        # blocked
        self._emit({"type": "blocked", "name": actor.name, "at": (actor.x, actor.y)})

    def _check_winner(self) -> Optional[int]:
        a = len(self._alive_team(0))
        b = len(self._alive_team(1))
        if a == 0 and b == 0:
            return None
        if a == 0:
            return 1
        if b == 0:
            return 0
        return None

    # Public step
    def take_turn(self) -> None:
        """Advance one atomic action."""
        if self.winner is not None:
            return
        if not self.turn_order:
            return
        actor = self.turn_order[self._turn_ix % len(self.turn_order)]
        self._turn_ix += 1
        if actor.alive and actor.hp > 0:
            self._step_actor(actor)
        # round bookkeeping: after each full cycle
        if self._turn_ix % len(self.turn_order) == 0:
            self.round += 1
            self._emit({"type": "round", "round": self.round})
        w = self._check_winner()
        if w is not None:
            self.winner = w
            self._emit({"type": "end", "winner": w})

    # Alias for compatibility
    def step_action(self) -> None:
        self.take_turn()
