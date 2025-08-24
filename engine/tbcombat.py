# engine/tbcombat.py
from __future__ import annotations

import random
from typing import Any, List, Optional

from .model import Fighter, Team, fighter_from_dict, Weapon, WEAPON_CATALOG
from .grid import layout_teams_tiles


# --- Weapon normalization helper ---
def normalize_weapon(wpn: Any) -> Weapon:
    """
    Normalize weapon input (Weapon instance, dict, or string) into a Weapon.
    """
    if isinstance(wpn, Weapon):
        return wpn
    if isinstance(wpn, dict):
        name = wpn.get("name", "Unarmed")
        dmg = tuple(wpn.get("dmg", (1, 4, 0)))
        reach = int(wpn.get("reach", 1))
        crit = tuple(wpn.get("crit", (20, 2)))
        return Weapon(name=name, dmg=dmg, reach=reach, crit=crit)
    if isinstance(wpn, str):
        if wpn in WEAPON_CATALOG:
            return WEAPON_CATALOG[wpn]
        for v in WEAPON_CATALOG.values():
            if getattr(v, "name", None) == wpn:
                return v
    # fallback
    return WEAPON_CATALOG.get("Unarmed") or Weapon("Unarmed", (1, 4, 0), 1, (20, 2))


# --- Combat Engine ---
class TBCombat:
    """
    Turn-based combat engine.
    Handles initiative, turns, attacks, crits, XP, level-ups, and event logging.
    """

    def __init__(self, team_a: Team, team_b: Team, seed: Optional[int] = None):
        self.teams = [team_a, team_b]
        self.rng = random.Random(seed)
        self.round = 0
        self.turn_index = 0
        self.initiative_order: List[Fighter] = []
        self.log: List[str] = []

    def roll_initiative(self):
        fighters = self.teams[0].fighters + self.teams[1].fighters
        order = [(self.rng.randint(1, 20) + f.speed, f) for f in fighters if f.is_alive()]
        order.sort(key=lambda x: x[0], reverse=True)
        self.initiative_order = [f for _, f in order]
        self.log.append("Initiative rolled.")

    def next_round(self):
        self.round += 1
        self.turn_index = 0
        self.roll_initiative()
        self.log.append(f"--- Round {self.round} ---")

    def next_turn(self) -> Optional[Fighter]:
        if not self.initiative_order:
            self.next_round()
        if self.turn_index >= len(self.initiative_order):
            self.next_round()
        if not self.initiative_order:
            return None
        fighter = self.initiative_order[self.turn_index]
        self.turn_index += 1
        if not fighter.is_alive():
            return self.next_turn()
        self.log.append(f"{fighter.name}'s turn.")
        return fighter

    def attack(self, attacker: Fighter, defender: Fighter, weapon: Any = None):
        weapon = normalize_weapon(weapon or attacker.weapon)
        roll = self.rng.randint(1, 20)
        crit_range, crit_mult = weapon.crit
        total_attack = roll + attacker.atk
        self.log.append(f"{attacker.name} attacks {defender.name} with {weapon.name} (roll {roll}).")

        if roll >= crit_range:
            dmg = sum(self.rng.randint(1, weapon.dmg[1]) for _ in range(weapon.dmg[0]))
            dmg += weapon.dmg[2]
            dmg = (dmg + attacker.atk) * crit_mult
            defender.hp -= dmg
            self.log.append(f"Critical hit! {defender.name} takes {dmg} damage.")
        elif total_attack >= defender.defense:
            dmg = sum(self.rng.randint(1, weapon.dmg[1]) for _ in range(weapon.dmg[0]))
            dmg += weapon.dmg[2] + attacker.atk
            defender.hp -= dmg
            self.log.append(f"Hit! {defender.name} takes {dmg} damage.")
        else:
            self.log.append(f"{attacker.name} misses {defender.name}.")

        if defender.hp <= 0:
            defender.hp = 0
            self.log.append(f"{defender.name} is down!")
            self.award_xp(attacker, 10)

    def award_xp(self, fighter: Fighter, xp: int):
        fighter.xp += xp
        self.log.append(f"{fighter.name} gains {xp} XP.")
        if fighter.xp >= fighter.next_level_xp:
            fighter.level_up()
            self.log.append(f"{fighter.name} leveled up to {fighter.level}!")

    def is_battle_over(self) -> bool:
        alive_a = any(f.is_alive() for f in self.teams[0].fighters)
        alive_b = any(f.is_alive() for f in self.teams[1].fighters)
        return not (alive_a and alive_b)

    def winner(self) -> Optional[Team]:
        if not self.is_battle_over():
            return None
        alive_a = any(f.is_alive() for f in self.teams[0].fighters)
        return self.teams[0] if alive_a else self.teams[1]

    def get_log(self) -> List[str]:
        return self.log[:]
