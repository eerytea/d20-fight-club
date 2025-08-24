from dataclasses import dataclass
from typing import Tuple, Optional

@dataclass
class Weapon:
    name: str
    damage: str
    prop: str = "str"
    reach: int = 1
    crit: Tuple[int,int] = (20,2)

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
    weapon: Weapon = Weapon("Longsword", "1d8", "str", 1, (20,2))
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
