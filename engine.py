# engine.py — Turn-based D20 grid combat
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
import math, random

# ---------- Dice & modifiers ----------
def ability_mod(score: int) -> int:
    return (score - 10) // 2

def roll_dice(expr: str) -> int:
    """
    Roll '1d8+2', '2d6-1', 'd12', or '5'.
    """
    s = expr.lower().replace(" ", "")
    if s.startswith("d"):
        s = "1" + s
    if "d" not in s:
        return int(s)
    left, right = s.split("d", 1)
    n = int(left) if left.isdigit() else 1

    bonus = 0
    if "+" in right:
        dice, b = right.split("+", 1)
        bonus = int(b)
    elif "-" in right:
        dice, b = right.split("-", 1)
        bonus = -int(b)
    else:
        dice = right
    sides = int(dice)
    return sum(random.randint(1, sides) for _ in range(n)) + bonus

def d20() -> int:
    return random.randint(1, 20)

def parse_damage(expr: str):
    s = expr.replace(" ", "").lower()
    if "+" in s:
        d, b = s.split("+", 1)
        return d, int(b)
    if "-" in s:
        d, b = s.split("-", 1)
        return d, -int(b)
    return s, 0

# ---------- Data classes ----------
@dataclass
class Weapon:
    name: str
    kind: str           # "melee" | "ranged"
    damage: str         # e.g. "1d8+2"
    attr: str           # "str" or "dex"
    reach: int          # interpreted as TILES (squares)
    crit: Tuple[int, int] = (20, 2)
    prof_bonus: int = 2

    def attack_bonus(self, f: "Fighter") -> int:
        mod = ability_mod(f.dex if self.attr == "dex" else f.str_)
        return self.prof_bonus + mod

    def damage_roll(self, f: "Fighter", critical: bool=False) -> int:
        dice, bonus = parse_damage(self.damage)
        rolls = 2 if critical else 1
        total = sum(roll_dice(dice) for _ in range(rolls))
        mod = ability_mod(f.dex if self.attr == "dex" else f.str_)
        return total + bonus + mod

@dataclass
class Fighter:
    name: str
    team_id: int
    str_: int
    dex: int
    con: int
    max_hp: int
    ac: int
    speed_ft: int              # in feet (30 = 6 tiles)
    weapon: Weapon
    tactic: str = "nearest"    # 'nearest' | 'lowest'
    tx: int = 0                # tile x
    ty: int = 0                # tile y

    hp: int = field(init=False)
    alive: bool = field(default=True, init=False)
    attack_cd: float = 1.2     # unused in turn system but kept for future
    ready: bool = field(default=True, init=False)

    def __post_init__(self):
        self.hp = self.max_hp

    def tiles_per_turn(self) -> int:
        return max(0, round(self.speed_ft / 5.0))  # 5 ft per square

@dataclass
class Event:
    t: int
    kind: str
    payload: Dict[str, Any]

@dataclass
class Team:
    team_id: int
    name: str
    color: Tuple[int, int, int]

# ---------- Core turn-based engine ----------
class TBCombat:
    def __init__(self, teamA: Team, teamB: Team, fighters: List[Fighter],
                 grid_w: int, grid_h: int, seed: Optional[int]=None):
        self.teamA = teamA
        self.teamB = teamB
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.fighters = fighters
        self.round = 1
        self.turn_index = 0
        self.initiative: List[Fighter] = []
        self.events: List[Event] = []
        self.winner: Optional[int] = None
        self.time_tick = 0  # increments per event, for ordering
        if seed is not None:
            random.seed(seed)
        self.roll_initiative()

    # ------- helpers -------
    def log(self, kind: str, **payload):
        self.time_tick += 1
        self.events.append(Event(self.time_tick, kind, payload))

    def living_team(self, team_id: int) -> List[Fighter]:
        return [f for f in self.fighters if f.team_id == team_id and f.alive]

    def enemies_of(self, f: Fighter) -> List[Fighter]:
        return [o for o in self.fighters if o.team_id != f.team_id and o.alive]

    def distance_tiles(self, a: Fighter, b: Fighter) -> int:
        return abs(a.tx - b.tx) + abs(a.ty - b.ty)  # Manhattan for simple melee/range

    def choose_target(self, f: Fighter) -> Optional[Fighter]:
        es = self.enemies_of(f)
        if not es:
            return None
        if f.tactic == "lowest":
            return min(es, key=lambda e: e.hp)
        # nearest tiebreaker: lowest HP
        nearest = min(es, key=lambda e: (self.distance_tiles(f, e), e.hp))
        return nearest

    def roll_initiative(self):
        order = []
        for f in [x for x in self.fighters if x.alive]:
            init = d20() + ability_mod(f.dex)
            order.append((init, d20(), f))  # small tiebreaker die
            self.log("init", name=f.name, dex=f.dex, init=init)
        order.sort(key=lambda t: (t[0], t[1]), reverse=True)
        self.initiative = [t[2] for t in order]
        self.turn_index = 0
        self.log("round_start", round=self.round,
                 order=[f.name for f in self.initiative])

    def end_check(self):
        a_alive = len(self.living_team(self.teamA.team_id))
        b_alive = len(self.living_team(self.teamB.team_id))
        if a_alive == 0 and b_alive == 0:
            self.winner = -1
            self.log("end", reason="double_elim")
        elif a_alive == 0:
            self.winner = self.teamB.team_id
            self.log("end", reason="elimination", winner=self.teamB.name)
        elif b_alive == 0:
            self.winner = self.teamA.team_id
            self.log("end", reason="elimination", winner=self.teamA.name)

    # ------- movement (greedy Manhattan) -------
    def step_toward(self, f: Fighter, tgt: Fighter, steps: int):
        """
        Move up to 'steps' tiles (N/E/S/W only) greedily toward target.
        No obstacles yet (empty arena). Stops if adjacent for melee.
        """
        for _ in range(steps):
            # Stop if in melee reach already
            if f.weapon.kind == "melee":
                if self.distance_tiles(f, tgt) <= max(1, f.weapon.reach):
                    break
            # Choose axis with greater distance
            dx = tgt.tx - f.tx
            dy = tgt.ty - f.ty
            if abs(dx) >= abs(dy):
                f.tx += 1 if dx > 0 else -1 if dx < 0 else 0
            else:
                f.ty += 1 if dy > 0 else -1 if dy < 0 else 0
            # clamp to grid
            f.tx = max(0, min(self.grid_w-1, f.tx))
            f.ty = max(0, min(self.grid_h-1, f.ty))
            self.log("move_step", name=f.name, to=(f.tx, f.ty))

    # ------- attack -------
    def try_attack(self, f: Fighter, tgt: Fighter) -> bool:
        # range check
        dist = self.distance_tiles(f, tgt)
        if f.weapon.kind == "melee":
            in_range = dist <= max(1, f.weapon.reach)
        else:
            # simple ranged: use 'reach' as RANGE in tiles
            in_range = dist <= max(2, f.weapon.reach)

        if not in_range:
            return False

        nat = d20()
        total = nat + f.weapon.attack_bonus(f)
        crit = nat >= f.weapon.crit[0]
        hit = (nat == 20) or (total >= tgt.ac and nat != 1)
        self.log("attack", attacker=f.name, defender=tgt.name,
                 nat=nat, total=total, target_ac=tgt.ac, hit=hit, critical=crit)
        if hit:
            dmg = f.weapon.damage_roll(f, critical=crit)
            tgt.hp -= max(1, dmg)
            self.log("damage", attacker=f.name, defender=tgt.name,
                     amount=dmg, hp_after=max(0, tgt.hp), critical=crit)
            if tgt.hp <= 0 and tgt.alive:
                tgt.alive = False
                self.log("down", name=tgt.name, team=tgt.team_id)
                self.end_check()
        return True

    # ------- one full actor turn -------
    def take_turn(self) -> Optional[str]:
        """
        Execute the next fighter's turn (move -> attack).
        Returns the acting fighter's name, or None if combat already over.
        """
        if self.winner is not None:
            return None
        # if initiative list is empty (rare), reroll
        self.initiative = [f for f in self.initiative if f.alive]
        if not self.initiative:
            self.roll_initiative()

        # find next living actor
        for _ in range(len(self.initiative)):
            actor = self.initiative[self.turn_index % len(self.initiative)]
            self.turn_index = (self.turn_index + 1) % len(self.initiative)
            if not actor.alive:
                continue
            self.log("turn_start", actor=actor.name, round=self.round)

            # pick a target
            tgt = self.choose_target(actor)
            if tgt is None:
                self.end_check()
                return actor.name

            # MOVE toward target (tiles per turn)
            steps = actor.tiles_per_turn()
            if actor.weapon.kind == "melee":
                # move until within melee reach
                while steps > 0 and self.distance_tiles(actor, tgt) > max(1, actor.weapon.reach):
                    self.step_toward(actor, tgt, 1)
                    steps -= 1
            else:
                # ranged: try to maintain line-of-sight; here just distance
                # optionally kite to keep some distance (not yet)
                if self.distance_tiles(actor, tgt) > max(2, actor.weapon.reach):
                    self.step_toward(actor, tgt, steps)
                    steps = 0

            # ATTACK if possible
            self.try_attack(actor, tgt)

            self.log("turn_end", actor=actor.name)
            self.end_check()
            return actor.name

        # end of round -> advance round & reroll initiative
        self.round += 1
        self.log("round_end", round=self.round-1)
        self.roll_initiative()
        return "ROUND_ADVANCE"

# ---------- Factories / helpers ----------
def fighter_from_dict(d: dict) -> Fighter:
    w = d.get("weapon", {})
    weapon = Weapon(
        name=w.get("name", "Shortsword"),
        kind=w.get("kind", "melee"),
        damage=w.get("damage", "1d6"),
        attr=w.get("attr", "str"),
        reach=int(w.get("reach", 1)),            # now tiles
        crit=tuple(w.get("crit", (20, 2))),
        prof_bonus=int(w.get("prof", 2)),
    )
    str_, dex, con = int(d.get("str", 12)), int(d.get("dex", 12)), int(d.get("con", 12))
    hp = int(d.get("hp", 10 + max(1, ability_mod(con)) * 4))
    ac = int(d.get("ac", 10 + max(0, ability_mod(dex))))
    speed_ft = int(d.get("speed", 30))          # default 30 ft (6 tiles)

    f = Fighter(
        name=d.get("name", "Fighter"),
        team_id=int(d.get("team_id", 0)),
        str_=str_,
        dex=dex,
        con=con,
        max_hp=hp,
        ac=ac,
        speed_ft=speed_ft,
        weapon=weapon,
        tactic=d.get("tactic", "nearest"),
    )
    return f

def layout_teams_tiles(fighters: List[Fighter], grid_w: int, grid_h: int):
    # simple spawn lines left/right on the grid
    left = [f for f in fighters if f.team_id == 0]
    right = [f for f in fighters if f.team_id == 1]
    gap_left = grid_h // (len(left) + 1) if left else grid_h // 2
    for i, f in enumerate(left, start=1):
        f.tx, f.ty = 1, min(grid_h-1, i * gap_left)
    gap_right = grid_h // (len(right) + 1) if right else grid_h // 2
    for i, f in enumerate(right, start=1):
        f.tx, f.ty = max(0, grid_w - 2), min(grid_h-1, i * gap_right)