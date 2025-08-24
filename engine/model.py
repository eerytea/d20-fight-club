# engine/model.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple, Any


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


# A minimal built-in catalog you can extend elsewhere
WEAPON_CATALOG: Dict[str, Weapon] = {
    "Unarmed": Weapon("Unarmed", (1, 4, 0), 1, (20, 2)),
    "Dagger":  Weapon("Dagger",  (1, 4, 0), 1, (19, 2)),
    "Sword":   Weapon("Sword",   (1, 8, 0), 1, (19, 2)),
    "Spear":   Weapon("Spear",   (1, 6, 0), 2, (20, 3)),
}


def _weapon_from_any(value: Any) -> Weapon:
    """Normalize a weapon that might be a Weapon, dict, or string key."""
    if isinstance(value, Weapon):
        return value
    if isinstance(value, dict):
        return Weapon(
            name=value.get("name", "Unarmed"),
            dmg=tuple(value.get("dmg", (1, 4, 0))),
            reach=int(value.get("reach", 1)),
            crit=tuple(value.get("crit", (20, 2))),
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

    # optional career fields (friendly defaults for back-compat)
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
        self.speed += 0  # keep speed stable by default

    def summary(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "class": self.cls,
            "level": self.level, "ovr": self.ovr, "hp": self.hp,
            "atk": self.atk, "def": self.defense, "spd": self.speed,
            "weapon": self.weapon.name, "reach": self.weapon.reach,
            "xp": self.xp, "age": self.age, "years_left": self.years_left,
        }


@dataclass
class Team:
    id: int
    name: str
    fighters: List[Fighter] = field(default_factory=list)

    def alive(self) -> Iterable[Fighter]:
        return (f for f in self.fighters if f.is_alive())

    def add(self, f: Fighter) -> None:
        self.fighters.append(f)


# ----------------------
# Converters / Helpers
# ----------------------
def fighter_from_dict(d: Dict[str, Any]) -> Fighter:
    """
    Build a Fighter from a dict. Accepts weapon as string/dict/Weapon.
    Required keys: id, name, cls, level, ovr, hp, atk, defense, speed.
    Optional: weapon, xp, age, years_left.
    """
    weapon = _weapon_from_any(d.get("weapon", "Unarmed"))
    return Fighter(
        id=int(d["id"]),
        name=str(d["name"]),
        cls=str(d.get("cls", d.get("class", "Fighter"))),
        level=int(d.get("level", 1)),
        ovr=int(d.get("ovr", 1)),
        hp=int(d.get("hp", 10)),
        atk=int(d.get("atk", 1)),
        defense=int(d.get("defense", d.get("def", 10))),
        speed=int(d.get("speed", 0)),
        weapon=weapon,
        xp=int(d.get("xp", 0)),
        age=int(d.get("age", 20)),
        years_left=int(d.get("years_left", 2)),
    )


def team_from_dict(d: Dict[str, Any]) -> Team:
    fighters = [fighter_from_dict(fd) for fd in d.get("fighters", [])]
    return Team(
        id=int(d.get("id", 0)),
        name=str(d.get("name", "Team")),
        fighters=fighters,
    )
