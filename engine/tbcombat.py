# engine/tbcombat.py
from __future__ import annotations

import random
from typing import List, Optional, Any, Tuple

from .model import Fighter, Team, fighter_from_dict, Weapon  # re-exported in engine/__init__
from core.config import TURN_LIMIT, CRIT_NAT, CRIT_MULTIPLIER


def _roll_dice(rng: random.Random, spec: str) -> int:
    """
    Very small dice parser: "XdY+Z" | "XdY" | "Y" | int-like.
    """
    s = str(spec).lower().strip()
    try:
        return int(s)
    except ValueError:
        pass
    total = 0
    mod = 0
    if "+" in s:
        s, mod_s = s.split("+", 1)
        try:
            mod = int(mod_s)
        except Exception:
            mod = 0
    if "d" in s:
        x_s, y_s = s.split("d", 1)
        try:
            x = int(x_s) if x_s else 1
        except Exception:
            x = 1
        try:
            y = int(y_s)
        except Exception:
            y = 6
        for _ in range(max(1, x)):
            total += rng.randint(1, max(2, y))
    else:
        try:
            total += int(s)
        except Exception:
            total += 1
    return total + mod


class TBCombat:
    """
    Minimal, deterministic-enough TB engine to satisfy tests and exhibition.
    - Fighters act in simple initiative order per round (by 'speed' then id)
    - On a turn: try to attack nearest enemy within reach; otherwise 'move' (no pathing yet)
    - Attack: d20 + atk vs target.ac; crit on natural CRIT_NAT; damage from weapon spec
    - Downed fighters set alive=False, hp<=0; winner is team that still has alive units
    - Awards small XP on down (attacker + team-wide small bonus at end)
    """

    def __init__(
        self,
        team_home: Team,
        team_away: Team,
        fighters: List[Fighter],
        grid_w: int,
        grid_h: int,
        *,
        seed: Optional[int] = None,
    ) -> None:
        self.team_home = team_home
        self.team_away = team_away
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.rng = random.Random(seed if seed is not None else 12345)

        # Fighters already hydrated & laid out
        self.fighters: List[Fighter] = list(fighters)

        # Event log as simple strings (UI can show/filter if desired)
        self.events: List[str] = []

        # Winner: 0 (home), 1 (away), or None while ongoing
        self.winner: Optional[int] = None

        # Track who downed whom for XP
        self._last_attacker_by_target: dict[int, int] = {}  # key = target.id, val = attacker.id

        # Per-round initiative order (recomputed each round)
        self._round_order: List[int] = []
        self._turn_index: int = 0
        self._round: int = 0

        self._rebuild_round_order()

    # ------------------- core loop -------------------

    def take_turn(self) -> None:
        if self.winner is not None:
            return

        # Safety: if state is degenerate or we've exceeded a cap, end it
        if self._round > TURN_LIMIT:
            self._end_in_draw()
            return
        if not any(f.alive and f.team_id == 0 for f in self.fighters):
            self._end(1)
            return
        if not any(f.alive and f.team_id == 1 for f in self.fighters):
            self._end(0)
            return

        # If we've consumed the current round, start a new one
        if self._turn_index >= len(self._round_order):
            self._rebuild_round_order()

        # Next actor
        idx = self._round_order[self._turn_index]
        self._turn_index += 1
        actor = self.fighters[idx]
        if not actor.alive:
            return

        # Find target
        target_idx = self._choose_target(actor)
        if target_idx is None:
            self.events.append(f"{actor.name} waits.")
            return
        target = self.fighters[target_idx]

        # Attack attempt
        d20 = self.rng.randint(1, 20)
        attack_total = d20 + max(0, getattr(actor, "atk", 0))
        crit = (d20 == CRIT_NAT)
        hit = crit or (attack_total >= getattr(target, "ac", 10))

        if hit:
            base = _roll_dice(self.rng, getattr(actor.weapon, "damage", "1d6"))
            dmg = base * (CRIT_MULTIPLIER if crit else 1)
            target.hp -= max(1, int(dmg))
            self._last_attacker_by_target[target.id] = actor.id
            self.events.append(
                f"{actor.name} hits {target.name} for {dmg}{' (crit)' if crit else ''}"
            )
            if target.hp <= 0 and target.alive:
                target.alive = False
                self.events.append(f"{target.name} is down!")
                self._award_on_down(target_id=target.id)
        else:
            self.events.append(f"{actor.name} misses {target.name}")

        # Check victory
        if not any(f.alive and f.team_id == 0 for f in self.fighters):
            self._end(1)
        elif not any(f.alive and f.team_id == 1 for f in self.fighters):
            self._end(0)

    # ------------------- helpers -------------------

    def _rebuild_round_order(self) -> None:
        self._round += 1
        alive_indices = [i for i, f in enumerate(self.fighters) if f.alive]
        # Sort by 'speed' desc then id for determinism
        alive_indices.sort(key=lambda i: (-int(getattr(self.fighters[i], "speed", 0)), int(self.fighters[i].id)))
        self._round_order = alive_indices
        self._turn_index = 0
        self.events.append(f"--- Round {self._round} ---")

    def _choose_target(self, actor: Fighter) -> Optional[int]:
        # naive nearest enemy by Manhattan distance; if in reach, pick that one
        enemies = [ (i, f) for i, f in enumerate(self.fighters) if f.alive and f.team_id != actor.team_id ]
        if not enemies:
            return None

        def dist(a: Fighter, b: Fighter) -> int:
            ax, ay = getattr(a, "tx", 0), getattr(a, "ty", 0)
            bx, by = getattr(b, "tx", 0), getattr(b, "ty", 0)
            return abs(ax - bx) + abs(ay - by)

        reach = int(getattr(actor.weapon, "reach", 1))
        # Prefer enemies already in reach
        in_reach = [ (i, f) for (i, f) in enemies if dist(actor, f) <= reach ]
        if in_reach:
            # choose lowest hp then nearest then lowest id (deterministic)
            in_reach.sort(key=lambda t: (int(t[1].hp), dist(actor, t[1]), int(t[1].id)))
            return in_reach[0][0]

        # Otherwise "move" closer (abstract, no pathing); we just log it
        # (Movement not required for tests; could adjust tx/ty to step closer later)
        nearest = sorted(enemies, key=lambda t: (dist(actor, t[1]), int(t[1].id)))[0]
        self.events.append(f"{actor.name} closes on {nearest[1].name}")
        return nearest[0]

    def _award_on_down(self, target_id: int) -> None:
        # Small XP award to the attacker that downed target
        attacker_id = self._last_attacker_by_target.get(target_id)
        if attacker_id is None:
            return
        for f in self.fighters:
            if f.id == attacker_id:
                f.xp = int(getattr(f, "xp", 0)) + 10

    def _end_in_draw(self) -> None:
        self.winner = None
        self.events.append("Match ended in a draw (turn cap).")

    def _end(self, winner_team_id_rel: int) -> None:
        # winner_team_id_rel is team_id relative to combat (0=home, 1=away)
        self.winner = winner_team_id_rel
        self.events.append(f"Winner: {'Home' if winner_team_id_rel == 0 else 'Away'}")
        # Team-wide small XP bonus
        for f in self.fighters:
            if f.alive and f.team_id == winner_team_id_rel:
                f.xp = int(getattr(f, "xp", 0)) + 5
