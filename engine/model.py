# engine/model.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple, Any
import re


# ----------------------
# Weapon & Catalog
# ----------------------
@dataclass
class Weapon:
    name: str = "Unarmed"
    # damage tuple: (num_dice, sides, flat_bonus)
    dmg: Tuple[int, int, int] = (1, 4, 0)
    reach: int = 1
    # crit tuple: (threat range lower bound on d20, multiplier)
    crit: Tuple[int, int] = (20, 2)


WEAPON_CATALOG: Dict[str, Weapon] = {
    "Unarmed": Weapon("Unarmed", (1, 4, 0), 1, (20, 2)),
    "Dagger":  Weapon("Dagger",  (1, 4, 0), 1, (19, 2)),
    "Sword":   Weapon("Sword",   (1, 8, 0), 1, (19, 2)),
    "Spear":   Weapon("Spear",   (1, 6, 0), 2, (20, 3)),
}


def _parse_damage_string(s: str) -> Tuple[int, int, int]:
    """
    Parse strings like '1d4', '2d6+1', '1d8-1' into (num, sides, bonus).
    """
    s = s.strip().lower()
    m = re.fullmatch(r"\s*(\d+)\s*d\s*(\d+)\s*([+-]\s*\d+)?\s*", s)
    if not m:
        return (1, 4, 0)
    n = int(m.group(1))
    sides = int(m.group(2))
    bonus = 0
    if m.group(3):
        bonus = int(m.group(3).replace(" ", ""))
    return (n, sides, bonus)


def _weapon_from_any(value: Any) -> Weapon:
    """Normalize a weapon that might be a Weapon, dict, or string key."""
    if isinstance(value, Weapon):
        return value
    if isinstance(value, dict):
        # Accept either 'dmg' tuple or 'damage' string
        if "dmg" in value:
            dmg = tuple(value.get("dmg", (1, 4, 0)))
        else:
            dmg = _parse_damage_string(str(value.get("damage", "1d4")))
        return Weapon(
            name=value.get("name", "Unarmed"),
            dmg=dmg,  # type: ignore[arg-type]
            reach=int(value.get("reach", 1)),
            crit=tuple(value.get("crit", (20, 2))),  # type: ignore[arg-type]
        )
    if isinstance(value, str):
        if value in WEAPON_CATALOG:
            return WEAPON_CATALOG[value]
        # try match by weapon.name
        for w in WEAPON_CATALOG.values():
            if w.name == value:
                return w
    return WEAPON_CATALOG["Unarmed"]


# ----------------------
# Fighter & Team
# ----------------------
@dataclass
class Fighter:
    id: int
    name: str
    cls: str
    level: int
    ovr: int
    hp: int
    atk: int
    defense: int
    speed: int
    weapon: Weapon = field(default_factory=lambda: WEAPON_CATALOG["Unarmed"])
    xp: int = 0

    # career/UI helpers
    team_id: int = 0
    age: int = 20
    years_left: int = 2

    def is_alive(self) -> bool:
        return self.hp > 0

    @property
    def next_level_xp(self) -> int:
        # simple curve: 100, 200, 300, ...
        return 100 * self.level

    def level_up(self) -> None:
        self.level += 1
        # modest stat bumps to make leveling feel good
        self.hp += 2
        self.atk += 1
        self.defense += 1
        # keep speed stable by default

    def summary(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "class": self.cls,
            "level": self.level, "ovr": self.ovr, "hp": self.hp,
            "atk": self.atk, "def": self.defense, "spd": self.speed,
            "weapon": self.weapon.name, "reach": self.weapon.reach,
            "xp": self.xp, "age": self.age, "years_left": self.years_left,
            "team_id": self.team_id,
        }


@dataclass
class Team:
    id: int
    name: str
    color: Tuple[int, int, int] | None = None
    fighters: List[Fighter] = field(default_factory=list)

    def alive(self) -> Iterable[Fighter]:
        return (f for f in self.fighters if f.is_alive())

    def add(s
