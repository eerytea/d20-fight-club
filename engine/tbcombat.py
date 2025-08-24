# engine/tbcombat.py
from __future__ import annotations

import random
from typing import Any, List, Optional

from .model import Fighter, Team, Weapon, WEAPON_CATALOG
from .grid import layout_teams_tiles


# --- helpers -------------------------------------------------------------

def _normalize_weapon(wpn: Any) -> Weapon:
    """Accept Weapon | dict | str and return a Weapon."""
    if isinstance(wpn, Weapon):
        return wpn
    if isinstance(wpn, dict):
        name = wpn.get("name", "Unarmed")
        # allow either tuple dmg or "XdY(+/-)Z" strings in other parts of the codebase
        dmg = tuple(wpn.get("dmg", (1, 4, 0)))
        reach = int(wpn.get("reach", 1))
        crit = tuple(wpn.get("crit", (20, 2)))
        return Weapon(name=name, dmg=dmg, reach=reach, crit=crit)  # type: ignore[arg-type]
    if isinstance(wpn, str):
        if wpn in WEAPON_CATALOG:
            return WEAPON_CATALOG[wpn]
        for v in WEAPON_CATALOG.values():
            if getattr(v, "name", None) == wpn:
                return v
    return WEAPON_CATALOG["Unarmed"]


def _roll_damage(rng: random.Random, dmg_tuple: tuple[int, int, int]) -> int:
    n, sides, bonus = dmg_tuple
    total = sum(rng.randint(1, sides) for _ in range(max(1, n)))
    return total + int(bonus)


# --- main engine ---------------------------------------------------------

class TBCombat:
    """
    Minimal, test-friendly turn-based combat engine.

    Expected constructor by tests:
        TBCombat(team_home, team_away, fighters, grid_w, grid_h, seed=...)

    Where:
      - fighters: flat list of Fighter with team_id in {0,1}
      - layout_teams_tiles has already set f.tx/f.ty, but we don't require it
    """

    def __init__(
        self,
        team_home: Team,
        team_away: Team,
        fighters: List[Fighter],
        grid_w: int,
        grid_h: int,
        seed: Optional[int] = None,
    ):
        self.team_home = team_home
        self.team_away = team_away
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.fighters: List[Fighter] = fighters
        self.rng = random.Random(seed)
        self._turn_idx = 0
        self._round = 0
        self._initiative: List[int] = []  # store indices into self.fighters
        self.event_log: List[str] = []
        self._winner: Optional[int] = None  # 0=home, 1=away, None=in progress

        # If positions not already set, lay them out (safe no-op if already set)
        try:
            # test calls layout_teams_tiles before creating TBCombat
            # but if not, do it here for safety
            if not hasattr(self.fighters[0], "tx"):
                layout_teams_tiles(self.fighters, grid_w, grid_h)
        except Exception:
            pass

        self._roll_initiative()

    # --- public surface used by tests -----------------------------------

    @property
    def winner(self) -> Optional[int]:
        """
        Test reads .winner and expects None until a side is eliminated,
        then 0 for home or 1 for away.
        """
        return self._winner

    def take_turn(self) -> None:
        """Advance combat by one fighter action."""
        if self._winner is not None:
            return

        # skip dead actors automatically
        for _ in range(len(self._initiative) + 2):
            if not self._initiative:
                self._start_round()
            idx = self._initiative[self._turn_idx]
            if self.fighters[idx].is_alive():
                break
            self._advance_turn()

        actor = self.fighters[self._initiative[self._turn_idx]]
        if not actor.is_alive():
            self._advance_turn()
            return

        # choose a living enemy
        enemy_tid = 1 if actor.team_id == 0 else 0
        targets = [f for f in self.fighters if f.team_id == enemy_tid and f.is_alive()]
        if not targets:
            self._resolve_winner()
            return
        target = self.rng.choice(targets)

        # basic attack roll: d20 + atk vs target.defense
        w = _normalize_weapon(getattr(actor, "weapon", WEAPON_CATALOG["Unarmed"]))
        roll = self.rng.randint(1, 20)
        total = roll + int(actor.atk)

        if roll >= w.crit[0]:  # crit threat met
            dmg = _roll_damage(self.rng, w.dmg) + int(actor.atk)
            dmg *= int(w.crit[1])
            target.hp -= max(1, dmg)
            self.event_log.append(f"{actor.name} crits {target.name} for {dmg}.")
            self._award_xp(actor, 10)
        elif total >= int(target.defense):
            dmg = _roll_damage(self.rng, w.dmg) + int(actor.atk)
            target.hp -= max(1, dmg)
            self.event_log.append(f"{actor.name} hits {target.name} for {dmg}.")
            self._award_xp(actor, 5)
        else:
            self.event_log.append(f"{actor.name} misses {target.name}.")

        if target.hp <= 0:
            target.hp = 0
            self.event_log.append(f"{target.name} is down!")
            self._award_xp(actor, 10)

        self._check_end()
        self._advance_turn()

    # --- internals ------------------------------------------------------

    def _roll_initiative(self) -> None:
        # initiative = sorted by (d20 + speed), desc
        rolls = []
        for i, f in enumerate(self.fighters):
            if f.is_alive():
                rolls.append((self.rng.randint(1, 20) + int(f.speed), i))
        rolls.sort(key=lambda t: t[0], reverse=True)
        self._initiative = [i for _, i in rolls]
        self._turn_idx = 0
        self._round += 1
        self.event_log.append(f"Init round {self._round}.")

    def _start_round(self) -> None:
        self._roll_initiative()

    def _advance_turn(self) -> None:
        if not self._initiative:
            self._roll_initiative()
            return
        self._turn_idx += 1
        if self._turn_idx >= len(self._initiative):
            self._start_round()

    def _award_xp(self, fighter: Fighter, xp: int) -> None:
        fighter.xp += xp
        # simple level up: every 100 XP
        while fighter.xp >= fighter.next_level_xp:
            fighter.level_up()
            self.event_log.append(f"{fighter.name} leveled to {fighter.level}.")

    def _check_end(self) -> None:
        home_alive = any(f.is_alive() for f in self.fighters if f.team_id == 0)
        away_alive = any(f.is_alive() for f in self.fighters if f.team_id == 1)
        if home_alive and away_alive:
            return
        self._resolve_winner()

    def _resolve_winner(self) -> None:
        home_alive = any(f.is_alive() for f in self.fighters if f.team_id == 0)
        away_alive = any(f.is_alive() for f in self.fighters if f.team_id == 1)
        if home_alive and not away_alive:
            self._winner = 0
        elif away_alive and not home_alive:
            self._winner = 1
        else:
            # simultaneous wipe—treat as no winner (could be -1 if you prefer)
            self._winner = 0  # pick home for determinism
