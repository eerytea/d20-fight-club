# engine/tbcombat.py
from __future__ import annotations

import random
from typing import List, Optional, Any

from .model import Fighter, Team, fighter_from_dict, Weapon
from core.config import TURN_LIMIT, CRIT_NAT, CRIT_MULTIPLIER
from .events import (
    Event, StartRound, Move, Hit, Miss, Down, End, format_event
)


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
    Deterministic TB engine with both string and typed event logs.
    API preserved:
      - .fighters: List[Fighter]
      - .events: List[str]
      - .winner: Optional[int]  (0=home, 1=away, None=draw/in-progress)
      - take_turn(): advances the simulation by one actor
    New:
      - .events_typed: List[Event]
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

        self.fighters: List[Fighter] = list(fighters)

        # Logs (existing string log kept for compatibility; typed log added)
        self.events: List[str] = []
        self.events_typed: List[Event] = []

        self.winner: Optional[int] = None
        self._last_attacker_by_target: dict[int, int] = {}

        self._round_order: List[int] = []
        self._turn_index: int = 0
        self._round: int = 0

        self._rebuild_round_order()

    # ------------------- core loop -------------------

    def take_turn(self) -> None:
        if self.winner is not None:
            return

        if self._round > TURN_LIMIT:
            self._end_in_draw()
            return
        if not any(f.alive and f.team_id == 0 for f in self.fighters):
            self._end(1)
            return
        if not any(f.alive and f.team_id == 1 for f in self.fighters):
            self._end(0)
            return

        if self._turn_index >= len(self._round_order):
            self._rebuild_round_order()

        idx = self._round_order[self._turn_index]
        self._turn_index += 1
        actor = self.fighters[idx]
        if not actor.alive:
            return

        target_idx = self._choose_target(actor)
        if target_idx is None:
            self._log_str("wait", f"{actor.name} waits.")
            return
        target = self.fighters[target_idx]

        d20 = self.rng.randint(1, 20)
        attack_total = d20 + max(0, getattr(actor, "atk", 0))
        crit = (d20 == CRIT_NAT)
        hit = crit or (attack_total >= getattr(target, "ac", 10))

        if hit:
            base = _roll_dice(self.rng, getattr(actor.weapon, "damage", "1d6"))
            dmg = base * (CRIT_MULTIPLIER if crit else 1)
            target.hp -= max(1, int(dmg))
            self._last_attacker_by_target[target.id] = actor.id
            self._log_typed(Hit(attacker_id=actor.id, target_id=target.id, damage=int(dmg), crit=crit))
            if target.hp <= 0 and target.alive:
                target.alive = False
                self._log_typed(Down(target_id=target.id, by_attacker_id=actor.id))
        else:
            self._log_typed(Miss(attacker_id=actor.id, target_id=target.id))

        if not any(f.alive and f.team_id == 0 for f in self.fighters):
            self._end(1)
        elif not any(f.alive and f.team_id == 1 for f in self.fighters):
            self._end(0)

    # ------------------- helpers -------------------

    def _rebuild_round_order(self) -> None:
        self._round += 1
        alive_indices = [i for i, f in enumerate(self.fighters) if f.alive]
        alive_indices.sort(key=lambda i: (-int(getattr(self.fighters[i], "speed", 0)), int(self.fighters[i].id)))
        self._round_order = alive_indices
        self._turn_index = 0
        self._log_typed(StartRound(round_no=self._round))

    def _choose_target(self, actor: Fighter) -> Optional[int]:
        enemies = [(i, f) for i, f in enumerate(self.fighters) if f.alive and f.team_id != actor.team_id]
        if not enemies:
            return None

        def dist(a: Fighter, b: Fighter) -> int:
            ax, ay = getattr(a, "tx", 0), getattr(a, "ty", 0)
            bx, by = getattr(b, "tx", 0), getattr(b, "ty", 0)
            return abs(ax - bx) + abs(ay - by)

        reach = int(getattr(actor.weapon, "reach", 1))
        in_reach = [(i, f) for (i, f) in enemies if dist(actor, f) <= reach]
        if in_reach:
            in_reach.sort(key=lambda t: (int(t[1].hp), dist(actor, t[1]), int(t[1].id)))
            return in_reach[0][0]

        nearest = sorted(enemies, key=lambda t: (dist(actor, t[1]), int(t[1].id)))[0]
        self._log_typed(Move(actor_id=actor.id, target_id=nearest[1].id))
        return nearest[0]

    def _award_on_down(self, target_id: int) -> None:
        attacker_id = self._last_attacker_by_target.get(target_id)
        if attacker_id is None:
            return
        for f in self.fighters:
            if f.id == attacker_id:
                f.xp = int(getattr(f, "xp", 0)) + 10

    def _end_in_draw(self) -> None:
        self.winner = None
        self._log_typed(End(winner=None))

    def _end(self, winner_team_id_rel: int) -> None:
        self.winner = winner_team_id_rel
        self._log_typed(End(winner=winner_team_id_rel))
        for f in self.fighters:
            if f.alive and f.team_id == winner_team_id_rel:
                f.xp = int(getattr(f, "xp", 0)) + 5

    # ------------------- logging bridges -------------------

    def _log_typed(self, ev: Event) -> None:
        """Append to typed log and keep the legacy string log in sync."""
        self.events_typed.append(ev)
        # Synthesize a plain string using id->name map when possible
        names = {f.id: getattr(f, "name", f"F#{f.id}") for f in self.fighters}
        self.events.append(format_event(ev, name_of=names.get))

    def _log_str(self, _tag: str, msg: str) -> None:
        """Only for rare legacy messages; also mirror to typed Move/Hit/Miss if possible."""
        self.events.append(msg)
