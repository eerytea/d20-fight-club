# engine/model.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple
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
    """Parse strings like '1d4', '2d6+1', '1d8-1' into (num, sides, bonus)."""
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
            dmg = tuple(value.get("dmg", (1, 4, 0)))  # type: ignore[arg-type]
        else:
            dmg = _parse_damage_string(str(value.get("damage", "1d4")))
        return Weapon(
            name=value.get("name", "Unarmed"),
            dmg=dmg,
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

    def add(self, f: Fighter) -> None:
        self.fighters.append(f)


# ----------------------
# Converters / Helpers
# ----------------------
def _mod_from_score(x: int) -> int:
    """D&D-ish modifier for STR/DEX if needed."""
    return (x - 10) // 2


def fighter_from_dict(d: Dict[str, Any]) -> Fighter:
    """
    Build a Fighter from a dict. Accept many field aliases used in tests:
      - id: 'id' OR 'fighter_id'
      - defense: 'defense' OR 'def' OR 'ac'
      - atk: 'atk' OR derived from 'str'
      - speed: 'speed' OR derived from 'dex'
      - weapon: dict {'name','damage'/'dmg','reach'} or catalog key or Weapon
    Missing fields are given sensible defaults.
    """
    fid = int(d.get("id", d.get("fighter_id", d.get("id_", 0))))
    name = str(d.get("name", f"F{fid}"))
    cls = str(d.get("cls", d.get("class", "Fighter")))
    level = int(d.get("level", 1))

    # derive ovr if not present (avg of a few stats)
    ovr_val = d.get("ovr")
    if ovr_val is None:
        ac = int(d.get("ac", d.get("defense", d.get("def", 10))))
        s = int(d.get("str", d.get("atk", 10)))
        dx = int(d.get("dex", d.get("speed", 10)))
        ovr_val = int(round((ac + s + dx) / 3))
    ovr = int(ovr_val)

    hp = int(d.get("hp", d.get("max_hp", 10)))
    # attack: prefer explicit atk, else derive from STR
    atk = int(d.get("atk", _mod_from_score(int(d.get("str", 10)))))
    # defense: prefer explicit defense, else 'def', else 'ac'
    defense = int(d.get("defense", d.get("def", d.get("ac", 10))))
    # speed: prefer explicit speed, else DEX mod
    speed = int(d.get("speed", _mod_from_score(int(d.get("dex", 10)))))

    weapon = _weapon_from_any(d.get("weapon", "Unarmed"))

    xp = int(d.get("xp", 0))
    team_id = int(d.get("team_id", 0))
    age = int(d.get("age", 20))
    years_left = int(d.get("years_left", 2))

    return Fighter(
        id=fid, name=name, cls=cls, level=level, ovr=ovr, hp=hp,
        atk=atk, defense=defense, speed=speed, weapon=weapon, xp=xp,
        team_id=team_id, age=age, years_left=years_left,
    )


def team_from_dict(d: Dict[str, Any]) -> Team:
    fighters = [fighter_from_dict(fd) for fd in d.get("fighters", [])]
    color = d.get("color")
    if isinstance(color, list):
        color = tuple(color)  # type: ignore[assignment]
    return Team(
        id=int(d.get("id", 0)),
        name=str(d.get("name", "Team")),
        color=color,  # type: ignore[arg-type]
        fighters=fighters,
    )
