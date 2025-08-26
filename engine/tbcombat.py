# engine/tbcombat.py
from __future__ import annotations

import random
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple, Optional

GRID_W, GRID_H = 15, 9

@dataclass
class Team:
    tid: int
    name: str
    color: Tuple[int, int, int]

def fighter_from_dict(d: Dict[str, Any]) -> Any:
    dd = dict(d)
    dd.setdefault("pid", str(dd.get("pid") or dd.get("id") or dd.get("name") or "F"))
    dd.setdefault("name", str(dd.get("name") or dd["pid"]))
    dd.setdefault("team_id", int(dd.get("team_id", 0)))
    lv = int(dd.get("level", dd.get("lvl", 1)))
    hp = int(dd.get("hp", 10 + lv * 2))
    dd.setdefault("level", lv)
    dd.setdefault("hp", hp)
    dd.setdefault("max_hp", int(dd.get("max_hp", hp)))
    dd.setdefault("ac", int(dd.get("ac", 10 + lv // 2)))
    dd.setdefault("atk", int(dd.get("atk", 2 + lv // 2)))
    dd.setdefault("alive", bool(dd.get("alive", True)))
    dd.setdefault("x", int(dd.get("x", 0)))
    dd.setdefault("y", int(dd.get("y", 0)))
    dd.setdefault("tx", int(dd.get("tx", dd["x"])))
    dd.setdefault("ty", int(dd.get("ty", dd["y"])))
    dd.setdefault("xp", int(dd.get("xp", 0)))
    return SimpleNamespace(**dd)

def layout_teams_tiles(fighters: List[Any], W: int, H: int) -> None:
    """Simple left/right columns — exclusive tiles by construction."""
    home = [f for f in fighters if getattr(f, "team_id", 0) == 0]
    away = [f for f in fighters if getattr(f, "team_id", 0) == 1]
    gapL = max(1, H // (len(home) + 1)) if home else 2
    gapR = max(1, H // (len(away) + 1)) if away else 2
    for i, f in enumerate(home, start=1):
        f.x = f.tx = 1; f.y = f.ty = min(H - 1, i * gapL)
    for i, f in enumerate(away, start=1):
        f.x = f.tx = max(0, W - 2); f.y = f.ty = min(H - 1, i * gapR)

class TBCombat:
    """Minimal deterministic TB combat with typed events and no-tile-stacking rule."""

    def __init__(self, teamA: Team, teamB: Team, fighters: List[Any], W: int, H: int, seed: int = 0):
        self.teamA = teamA
        self.teamB = teamB
        self.W, self.H = int(W), int(H)
        self.fighters: List[Any] = [fighter_from_dict(f.__dict__ if hasattr(f, "__dict__") else f) for f in fighters]
        self.rng = random.Random(int(seed))

        # public logs (string and typed)
        self.events: List[str] = []
        self.events_typed: List[Dict[str, Any]] = []
        # alias some names other code may look for
        self.typed_events = self.events_typed
        self.event_log_typed = self.events_typed
        self.log = self.events

        self.round: int = 1
        self.turn_index: int = 0
        self.winner: Optional[str] = None  # 'home' | 'away' | 'draw'
        self._push_round_banner()

        # ensure initial exclusivity
        self._enforce_exclusive_tiles()

    # ---------- occupancy helpers ----------
    def _alive(self, f: Any) -> bool:
        return bool(getattr(f, "alive", True)) and int(getattr(f, "hp", 0)) > 0

    def _occupied(self, x: int, y: int, ignore: Optional[Any] = None) -> bool:
        for g in self.fighters:
            if g is ignore: continue
            if not self._alive(g): continue
            if int(getattr(g, "x", -1)) == x and int(getattr(g, "y", -1)) == y:
                return True
        return False

    def _neighbors_8(self, x: int, y: int) -> List[Tuple[int, int]]:
        out = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0: continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.W and 0 <= ny < self.H:
                    out.append((nx, ny))
        return out

    def _find_alt_free(self, x: int, y: int, actor: Any) -> Optional[Tuple[int, int]]:
        # Prefer neighbors closer to target tile if possible
        neigh = self._neighbors_8(x, y)
        self.rng.shuffle(neigh)
        for nx, ny in neigh:
            if not self._occupied(nx, ny, ignore=actor):
                return (nx, ny)
        return None

    def _enforce_exclusive_tiles(self) -> None:
        """Resolve any accidental stacking by gently nudging later occupants to nearest free."""
        seen = set()
        for f in self.fighters:
            if not self._alive(f): continue
            x, y = int(getattr(f, "x", 0)), int(getattr(f, "y", 0))
            key = (x, y)
            if key in seen:
                alt = self._find_alt_free(x, y, f)
                if alt:
                    f.x, f.y = alt
                else:
                    # if totally surrounded, leave as-is; draw path will still offset visually
                    pass
            else:
                seen.add(key)

    # ---------- events ----------
    def _push_round_banner(self) -> None:
        self.events_typed.append({"type": "round", "round": self.round})
        self.events.append(f"— Round {self.round} —")

    def _emit_move(self, f: Any, to_xy: Tuple[int, int]) -> None:
        self.events_typed.append({"type": "move", "name": f.name, "to": tuple(to_xy)})
        self.events.append(f"{f.name} moves to {tuple(to_xy)}")

    def _emit_hit(self, a: Any, d: Any, dmg: int) -> None:
        self.events_typed.append({"type": "hit", "name": a.name, "target": d.name, "dmg": int(dmg)})
        self.events.append(f"{a.name} hits {d.name} for {int(dmg)}")

    def _emit_miss(self, a: Any, d: Any) -> None:
        self.events_typed.append({"type": "miss", "name": a.name, "target": d.name})
        self.events.append(f"{a.name} misses {d.name}")

    def _emit_down(self, d: Any) -> None:
        self.events_typed.append({"type": "down", "name": d.name})
        self.events.append(f"{d.name} is down!")

    def _emit_end(self) -> None:
        self.events_typed.append({"type": "end"})
        self.events.append("End of match")

    # ---------- turn loop ----------
    def _teams_alive(self) -> Tuple[bool, bool]:
        a_alive = any(self._alive(f) and f.team_id == 0 for f in self.fighters)
        b_alive = any(self._alive(f) and f.team_id == 1 for f in self.fighters)
        return a_alive, b_alive

    def _closest_enemy(self, f: Any) -> Optional[Any]:
        best = None
        best_d = 1e9
        fx, fy = int(f.x), int(f.y)
        for g in self.fighters:
            if not self._alive(g): continue
            if g.team_id == f.team_id: continue
            d = abs(int(g.x) - fx) + abs(int(g.y) - fy)
            if d < best_d:
                best_d = d
                best = g
        return best

    def _step_move_towards(self, f: Any, tgt: Any) -> None:
        # Move by 1 step towards target; respect no-stacking rule
        fx, fy = int(f.x), int(f.y)
        tx, ty = int(tgt.x), int(tgt.y)
        dx = 0 if tx == fx else (1 if tx > fx else -1)
        dy = 0 if ty == fy else (1 if ty > fy else -1)

        intended = (fx + dx, fy + dy)
        nx, ny = intended
        # clamp
        nx = max(0, min(self.W - 1, nx))
        ny = max(0, min(self.H - 1, ny))

        if not self._occupied(nx, ny, ignore=f):
            f.x, f.y = nx, ny
            self._emit_move(f, (nx, ny))
            return

        # try an alternative neighbor that is free (prefer those closer to target)
        choices = self._neighbors_8(fx, fy)
        # sort by manhattan distance to target, then shuffle stable by rng
        choices.sort(key=lambda p: abs(p[0] - tx) + abs(p[1] - ty))
        for cx, cy in choices:
            if not self._occupied(cx, cy, ignore=f):
                f.x, f.y = cx, cy
                self._emit_move(f, (cx, cy))
                return

        # stuck: don't move this turn
        # (we still emit nothing; that’s fine)

    def _adjacent(self, a: Any, b: Any) -> bool:
        return max(abs(int(a.x) - int(b.x)), abs(int(a.y) - int(b.y))) <= 1

    def _attack(self, a: Any, d: Any) -> None:
        roll = self.rng.randint(1, 20)
        atk  = int(getattr(a, "atk", 2))
        ac   = int(getattr(d, "ac", 10))
        total = roll + atk
        if total >= ac:
            dmg = max(1, self.rng.randint(1, 6) + (getattr(a, "level", 1)//2))
            d.hp = max(0, int(d.hp) - dmg)
            if d.hp <= 0:
                d.alive = False
            self._emit_hit(a, d, dmg)
            if not self._alive(d):
                # award XP on down
                a.xp = int(getattr(a, "xp", 0)) + 10
                self._emit_down(d)
        else:
            self._emit_miss(a, d)

    def _maybe_end_match(self) -> bool:
        a_alive, b_alive = self._teams_alive()
        if a_alive and b_alive:
            return False
        if a_alive and not b_alive:
            self.winner = "home"
        elif b_alive and not a_alive:
            self.winner = "away"
        else:
            self.winner = "draw"
        self._emit_end()
        return True

    def take_turn(self, n: int = 1) -> None:
        for _ in range(max(1, int(n))):
            if self.winner is not None:
                return

            # find next alive actor
            N = len(self.fighters)
            idx = self.turn_index
            for _spin in range(N):
                f = self.fighters[idx]
                idx = (idx + 1) % N
                if self._alive(f):
                    self.turn_index = idx
                    break
            actor = self.fighters[(idx - 1) % N]
            if not self._alive(actor):
                # everyone is dead? end match
                if self._maybe_end_match():
                    return
                continue

            # pick closest enemy
            tgt = self._closest_enemy(actor)
            if tgt is None:
                if self._maybe_end_match():
                    return
                continue

            # if adjacent -> attack, else move
            if self._adjacent(actor, tgt):
                self._attack(actor, tgt)
            else:
                self._step_move_towards(actor, tgt)

            # after action, enforce exclusivity in case external effects stacked tiles
            self._enforce_exclusive_tiles()

            if self._maybe_end_match():
                return

            # start-of-next-round banner after everyone acted roughly once
            # (simple round handling: every N actions, bump round)
            if self.turn_index == 0:
                self.round += 1
                self._push_round_banner()

    # aliases used by some callers
    def step(self, n: int = 1) -> None:
        self.take_turn(n)

    def advance(self, n: int = 1) -> None:
        self.take_turn(n)

    def tick(self, n: int = 1) -> None:
        self.take_turn(n)

    def update(self, n: int = 1) -> None:
        self.take_turn(n)
