from __future__ import annotations
from dataclasses import dataclass, field, fields as dataclass_fields
from typing import Any, Dict, Tuple

# -----------------------------
# Core dataclasses
# -----------------------------

@dataclass
class Weapon:
    name: str = "Unarmed"
    damage: str = "1d2"      # dice string like "1d6", "2d6+1"
    to_hit_bonus: int = 0
    crit_range: int = 20     # nat20 crit
    crit_mult: int = 2
    reach: int = 1           # melee reach in Manhattan tiles

@dataclass
class Fighter:
    # identity / placement
    id: int | None = None
    team_id: int = 0
    name: str = "Fighter"
    tx: int = 0
    ty: int = 0
    alive: bool = True

    # combat stats
    level: int = 1
    ac: int = 10
    hp: int = 10
    max_hp: int = 10

    # ability scores (D&D-ish)
    str_: int = 10
    dex: int = 10
    con: int = 10
    int_: int = 10
    wis: int = 10
    cha: int = 10

    # misc
    age: int | None = None
    cls: str | None = None  # class name (optional)

    # equipment
    weapon: Weapon = field(default_factory=Weapon)

    # tracking
    xp: int = 0

    # convenience accessors for common aliases (str/int reserved words)
    @property
    def str(self) -> int:
        return self.str_

    @property
    def int(self) -> int:
        return self.int_


@dataclass
class Team:
    id: int
    name: str
    color: Tuple[int, int, int] = (180, 180, 180)


# -----------------------------
# Helpers for flexible creation
# -----------------------------

def _pick(d: Dict[str, Any], *keys, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default

def _to_weapon(w: Any) -> Weapon:
    """
    Accept:
      - Weapon instance
      - dict with known or aliased fields
      - str: either dice ("1d6+1") or name ("Shortsword")
      - None -> default Weapon()
    """
    if isinstance(w, Weapon):
        return w
    if isinstance(w, dict):
        kw: Dict[str, Any] = {}
        # copy recognized fields
        for f in dataclass_fields(Weapon):
            if f.name in w:
                kw[f.name] = w[f.name]
        # friendly aliases/defaults
        kw.setdefault("name", _pick(w, "weapon_name", default="Unarmed"))
        kw.setdefault("damage", _pick(w, "weapon_damage", "dmg", default="1d2"))
        kw.setdefault("to_hit_bonus", _pick(w, "to_hit_bonus", "to_hit", "atk_mod", default=0))
        kw.setdefault("crit_range", int(_pick(w, "crit_range", default=20)))
        kw.setdefault("crit_mult", int(_pick(w, "crit_mult", default=2)))
        kw.setdefault("reach", int(_pick(w, "reach", default=1)))
        return Weapon(**kw)
    if isinstance(w, str):
        s = w.strip()
        has_dice = ("d" in s.lower()) and any(ch.isdigit() for ch in s)
        if has_dice:
            return Weapon(name="Custom", damage=s, to_hit_bonus=0, crit_range=20, crit_mult=2, reach=1)
        return Weapon(name=s, damage="1d4", to_hit_bonus=0, crit_range=20, crit_mult=2, reach=1)
    return Weapon()


def fighter_from_dict(d: Dict[str, Any]) -> Fighter:
    """
    Build a Fighter from flexible dicts used by tests/core.creator.
    Accepted keys:
      id/fighter_id, team_id, name, class, level/lvl, ac, hp/current_hp, max_hp
      str/STR, dex, con, int/INT, wis, cha
      weapon (dict/str) or weapon_* flattened fields
      age (optional)
    Unknown keys are ignored.
    """
    fid = _pick(d, "id", "fighter_id")
    name = _pick(d, "name", default=f"Fighter {fid}" if fid is not None else "Fighter")
    team_id = int(_pick(d, "team_id", "team", default=0))
    level = int(_pick(d, "level", "lvl", default=1))
    ac = int(_pick(d, "ac", default=10))
    age = _pick(d, "age", default=None)
    cls = _pick(d, "class", "cls", default=None)

    # stats (case-insensitive + aliasing for 'str'/'int')
    def _stat(key: str, default=10) -> int:
        return int(_pick(d, key, key.upper(), default=default))

    STR = _stat("str")
    DEX = _stat("dex")
    CON = _stat("con")
    INT = _stat("int")
    WIS = _stat("wis")
    CHA = _stat("cha")

    # HP
    max_hp = int(_pick(d, "max_hp", "maxHP", default=_pick(d, "hp", "HP", default=10)))
    hp = int(_pick(d, "hp", "current_hp", "HP", default=max_hp))

    # weapon: accept dict/str; or flattened weapon_* fields
    wdict = _pick(d, "weapon", default=None)
    if wdict is None:
        maybe: Dict[str, Any] = {}
        if "weapon_name" in d:   maybe["name"] = d["weapon_name"]
        if "weapon_damage" in d: maybe["damage"] = d["weapon_damage"]
        if "damage" in d and "weapon_damage" not in maybe: maybe["damage"] = d["damage"]
        if any(k in d for k in ("to_hit_bonus", "to_hit", "atk_mod")):
            maybe["to_hit_bonus"] = _pick(d, "to_hit_bonus", "to_hit", "atk_mod", default=0)
        if "reach" in d: maybe["reach"] = d["reach"]
        wdict = maybe or None
    weapon = _to_weapon(wdict)

    # optional global atk_mod merges into weapon
    atk_mod = _pick(d, "atk_mod")
    if atk_mod is not None:
        weapon = Weapon(
            name=weapon.name,
            damage=weapon.damage,
            to_hit_bonus=int(weapon.to_hit_bonus) + int(atk_mod),
            crit_range=weapon.crit_range,
            crit_mult=weapon.crit_mult,
            reach=weapon.reach,
        )

    # Build fighter with safe field names
    f = Fighter(
        id=fid,
        team_id=team_id,
        name=name,
        level=level,
        ac=ac,
        hp=hp,
        max_hp=max_hp,
        str_=STR,
        dex=DEX,
        con=CON,
        int_=INT,
        wis=WIS,
        cha=CHA,
        age=age,
        cls=cls,
        weapon=weapon,
    )
    return f
