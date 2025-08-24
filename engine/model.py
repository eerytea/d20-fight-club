from dataclasses import dataclass
from typing import Tuple, Optional
from dataclasses import dataclass, field

@dataclass
class Weapon:
    name: str = "Unarmed"
    damage: str = "1d2"      # dice string your roller already handles
    to_hit_bonus: int = 0
    crit_range: int = 20
    crit_mult: int = 2

@dataclass
class Team:
    tid: int
    name: str
    color: Tuple[int,int,int] = (120,180,255)

@dataclass
class Fighter:
    name: str
    team_id: int
    str_: int = 10
    dex: int = 10
    con: int = 10
    int_: int = 10
    wis: int = 10
    cha: int = 10
    max_hp: int = 10
    ac: int = 12
    speed_ft: int = 6
    weapon: Weapon = field(default_factory=Weapon)
    prof_bonus: int = 2
    tactic: str = "nearest"
    # grid
    tx: int = 0
    ty: int = 0
    # runtime
    hp: int = 10
    alive: bool = True
    attack_cd: float = 1.2
    ready: bool = True
# engine/model.py (append near your dataclasses)
from dataclasses import fields as dataclass_fields
from typing import Any, Dict

def _pick(d: Dict[str, Any], *keys, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default

def _to_weapon(w: Any) -> Weapon:
    """
    Accepts:
      - dict like {"name": "Shortsword", "damage": "1d6", "to_hit_bonus": 2, "crit_range": 20, "crit_mult": 2}
      - str  like "1d4" or "Shortsword 1d6"
      - Weapon instance
      - None -> default unarmed
    """
    if isinstance(w, Weapon):
        return w
    if isinstance(w, dict):
        # only pass known Weapon fields
        kw = {}
        for f in dataclass_fields(Weapon):
            if f.name in w:
                kw[f.name] = w[f.name]
        # Friendly aliases
        if "to_hit_bonus" not in kw:
            alias = _pick(w, "to_hit", "atk_mod", default=0)
            kw["to_hit_bonus"] = alias
        if "name" not in kw:
            kw["name"] = _pick(w, "weapon_name", default="Unarmed")
        if "damage" not in kw:
            kw["damage"] = _pick(w, "dmg", default="1d2")
        return Weapon(**kw)
    if isinstance(w, str):
        # Very simple parse: if a dice pattern exists in the string, treat it as damage
        # otherwise assume it's a name with default damage.
        s = w.strip()
        has_dice = any(ch.isdigit() for ch in s) and "d" in s.lower()
        if has_dice:
            return Weapon(name="Custom", damage=s, to_hit_bonus=0, crit_range=20, crit_mult=2)
        else:
            return Weapon(name=s, damage="1d4", to_hit_bonus=0, crit_range=20, crit_mult=2)
    return Weapon()  # default unarmed
def fighter_from_dict(d: Dict[str, Any]) -> "Fighter":
    """
    Build a Fighter from a flexible dict format.
    Understands keys like:
      name, id/fighter_id, team_id
      level/lvl, ac, hp/current_hp, max_hp
      str/dex/con/int/wis/cha (case-insensitive)
      weapon (dict/str) or weapon_* fields
      atk_mod/to_hit added into weapon.to_hit_bonus if present
      age (optional), class (optional)
    Unknown keys are ignored.
    """
    # Basic identity
    fid = _pick(d, "id", "fighter_id", default=None)
    name = _pick(d, "name", default=(f"Fighter {fid}" if fid is not None else "Fighter"))
    team_id = int(_pick(d, "team_id", "team", default=0))
    level = int(_pick(d, "level", "lvl", default=1))
    ac = int(_pick(d, "ac", default=10))
    age = _pick(d, "age", default=None)  # keep if your Fighter has it; else ignore

    # Stats (case-insensitive)
    def _stat(key, default=10):
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

    # Weapon (accept dict / str / Weapon)
    wdict = _pick(d, "weapon", default=None)
    # Allow flattened fields like weapon_name, weapon_damage, to_hit/atk_mod
    if wdict is None:
        maybe = {}
        if "weapon_name" in d: maybe["name"] = d["weapon_name"]
        if "weapon_damage" in d or "damage" in d:
            maybe["damage"] = _pick(d, "weapon_damage", "damage")
        if "to_hit" in d or "atk_mod" in d or "to_hit_bonus" in d:
            maybe["to_hit_bonus"] = _pick(d, "to_hit_bonus", "to_hit", "atk_mod", default=0)
        wdict = maybe if maybe else None
    weapon = _to_weapon(wdict)

    # Fold global atk_mod into the weapon to-hit bonus if provided
    atk_mod = _pick(d, "atk_mod", default=None)
    if atk_mod is not None:
        try:
            weapon = Weapon(
                name=weapon.name,
                damage=weapon.damage,
                to_hit_bonus=int(weapon.to_hit_bonus) + int(atk_mod),
                crit_range=weapon.crit_range,
                crit_mult=weapon.crit_mult,
            )
        except Exception:
            # If Weapon signature differs, just ignore the merge rather than crash
            pass

    # Build kwargs restricted to Fighter's dataclass fields
    f_fields = {f.name for f in dataclass_fields(Fighter)}

    # Common mapping
    candidate = {
        "id": fid,
        "name": name,
        "team_id": team_id,
        "level": level,
        "ac": ac,
        "hp": hp,
        "max_hp": max_hp,
        "str": STR,
        "dex": DEX,
        "con": CON,
        "int": INT,
        "wis": WIS,
        "cha": CHA,
        "weapon": weapon,
        "age": age,
    }

    # Filter to Fighter fields only; drop None for missing optional fields
    kwargs = {k: v for k, v in candidate.items() if k in f_fields and v is not None}

    # If your Fighter uses different field names (e.g., strength instead of str), map here:
    alias_map = {
        "strength": "str",
        "dexterity": "dex",
        "constitution": "con",
        "intelligence": "int",
        "wisdom": "wis",
        "charisma": "cha",
    }
    for dest, src in alias_map.items():
        if dest in f_fields and src in kwargs and dest not in kwargs:
            kwargs[dest] = kwargs[src]

    return Fighter(**kwargs)
# top of engine/model.py
from dataclasses import dataclass, field

@dataclass
class Weapon:
    name: str = "Unarmed"
    damage: str = "1d2"
    to_hit_bonus: int = 0
    crit_range: int = 20
    crit_mult: int = 2
    reach: int = 1          # ← NEW: melee distance in Manhattan tiles
