# engine.py — Turn-based D20 grid combat (clean build)

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any, Set
import random, re
from core.ratings import total_xp_multiplier  # age * dev-trait XP multiplier

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

def _weapon_damage_str(wpn) -> str:
    """
    Accepts either a dict ({"damage": "1d8"}) or an object with .damage/.damage_die.
    Falls back to '1d6'.
    """
    if wpn is None:
        return "1d6"
    if isinstance(wpn, dict):
        return wpn.get("damage", "1d6")
    if hasattr(wpn, "damage") and getattr(wpn, "damage"):
        return getattr(wpn, "damage")
    if hasattr(wpn, "damage_die") and getattr(wpn, "damage_die"):
        return getattr(wpn, "damage_die")
    return "1d6"

# ---------- Data classes ----------
@dataclass
class Weapon:
    name: str
    kind: str           # "melee" | "ranged"
    damage: str         # e.g. "1d8+2"
    attr: str           # "str" or "dex"
    reach: int          # tiles
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
    speed_ft: int              # 30 ft = 6 tiles
    weapon: Weapon
    tactic: str = "nearest"    # 'nearest' | 'lowest'
    tx: int = 0                # tile x
    ty: int = 0                # tile y

    hp: int = field(init=False)
    alive: bool = field(default=True, init=False)
    attack_cd: float = 1.2     # placeholder for future RT logic
    ready: bool = field(default=True, init=False)

    def __post_init__(self):
        self.hp = self.max_hp

    def tiles_per_turn(self) -> int:
        return max(0, round(self.speed_ft / 5.0))  # 5 ft per tile

@dataclass
class Team:
    team_id: int
    name: str
    color: Tuple[int, int, int]

# ---------- Events ----------
class Event:
    def __init__(self, kind: str, payload: Dict):
        self.kind = kind
        self.payload = payload

# ---------- XP thresholds / KO reward ----------
_DIE_RE = re.compile(r"^\s*(\d+)[dD](\d+)\s*$")

# Scaled-down thresholds suitable for a sports season (tunable).
_XP_THRESHOLDS = [0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000, 100000]
def _next_level_threshold(lvl: int) -> int:
    if lvl < 1:
        lvl = 1
    if lvl >= len(_XP_THRESHOLDS):
        return _XP_THRESHOLDS[-1] + 50000 * (lvl - (len(_XP_THRESHOLDS) - 1))
    return _XP_THRESHOLDS[lvl]

def _roll_damage(dmg_str: str, rng: random.Random) -> int:
    m = _DIE_RE.match(dmg_str or "1d6")
    if not m:
        return 1
    n, s = int(m.group(1)), int(m.group(2))
    return sum(rng.randint(1, s) for _ in range(max(1, n)))

def _challenge_xp_for_ovr(ovr: int) -> int:
    """Map OVR (25..90) to a D&D-like XP value for KO rewards."""
    if ovr < 35:   return 25       # CR 1/8
    if ovr < 45:   return 50       # CR 1/4
    if ovr < 55:   return 100      # CR 1/2
    if ovr < 65:   return 200      # CR 1
    if ovr < 70:   return 450      # CR 2
    if ovr < 75:   return 700      # CR 3
    if ovr < 80:   return 1100     # CR 4
    if ovr < 85:   return 1800     # CR 5
    if ovr < 88:   return 2300     # CR 6
    return 2900                    # CR 7 (top-tier)

# ---------- TBCombat ----------
class TBCombat:
    """
    Turn-based grid combat with d20 attacks, greedy movement, and an event log.
    Includes XP on KO with age/development multipliers; handles level-ups.
    """
    def __init__(self, teamA: Team, teamB: Team, fighters: List[Fighter], grid_w: int, grid_h: int, seed: Optional[int] = None):
        self.teamA = teamA
        self.teamB = teamB
        self.fighters = fighters
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.rng = random.Random(seed)
        self.events: List[Event] = []
        self.round = 1
        self.turn_index = 0
        self.winner: Optional[int] = None  # 0 teamA, 1 teamB, -1 both down

        # Init fighter state + initiative
        for f in self.fighters:
            init_roll = self.rng.randint(1, 20) + getattr(f, "eva_mod", 0)
            setattr(f, "_init", init_roll)
            f.max_hp = getattr(f, "max_hp", getattr(f, "hp", 10))
            if getattr(f, "hp", None) is None:
                f.hp = f.max_hp
            f.alive = True if getattr(f, "alive", True) else False
            if getattr(f, "level", None) is None: f.level = 1
            if getattr(f, "xp", None) is None:    f.xp = 0

        self.order = sorted(range(len(self.fighters)), key=lambda i: getattr(self.fighters[i], "_init", 0), reverse=True)

        # For XP attribution: target_key -> set(attacker_keys); and last hitter
        self._contributors: Dict[str, Set[str]] = {}
        self._last_hitter: Dict[str, str] = {}

        # Emit init events
        for f in self.fighters:
            self.events.append(Event("init", {"name": f.name, "init": getattr(f, "_init", 0)}))
        self.events.append(Event("round_start", {"round": self.round}))

    # -------- utility --------
    def _key_for(self, f) -> str:
        return getattr(f, "pid", None) or f"{id(f)}"

    def _enemies_of(self, team_id: int) -> List[Fighter]:
        return [x for x in self.fighters if x.alive and x.team_id != team_id]

    def _dist(self, a: Fighter, b: Fighter) -> int:
        return abs(a.tx - b.tx) + abs(a.ty - b.ty)

    def _nearest_enemy(self, f: Fighter) -> Optional[Fighter]:
        enemies = self._enemies_of(f.team_id)
        if not enemies:
            return None
        return min(enemies, key=lambda e: self._dist(f, e))

    def _adjacent(self, a: Fighter, b: Fighter) -> bool:
        return self._dist(a, b) == 1

    def _try_move_toward(self, f: Fighter, target: Fighter):
        """Greedy Manhattan step toward target; avoids stepping off board or onto occupied tiles."""
        if not target:
            return
        steps = f.tiles_per_turn()
        for _ in range(max(1, steps)):
            if not f.alive:
                break
            if self._adjacent(f, target):
                break

            dx = 1 if target.tx > f.tx else -1 if target.tx < f.tx else 0
            dy = 1 if target.ty > f.ty else -1 if target.ty < f.ty else 0

            def free(nx, ny):
                if nx < 0 or ny < 0 or nx >= self.grid_w or ny >= self.grid_h:
                    return False
                for o in self.fighters:
                    if o.alive and o is not f and o.tx == nx and o.ty == ny:
                        return False
                return True

            moved = False
            if dx != 0 and free(f.tx + dx, f.ty):
                f.tx += dx; moved = True
            elif dy != 0 and free(f.tx, f.ty + dy):
                f.ty += dy; moved = True
            elif dy != 0 and free(f.tx, f.ty + dy):
                f.ty += dy; moved = True
            elif dx != 0 and free(f.tx + dx, f.ty):
                f.tx += dx; moved = True

            if moved:
                self.events.append(Event("move_step", {"name": f.name, "to": (f.tx, f.ty)}))
            else:
                break

    # -------- combat actions --------
    def _attack(self, attacker: Fighter, defender: Fighter):
        atk_mod = getattr(attacker, "atk_mod", 0)
        ac = getattr(defender, "ac", 12)
        roll = self.rng.randint(1, 20)
        crit = (roll == 20)
        hit = (roll + atk_mod >= ac) or crit

        self.events.append(Event("attack", {
            "attacker": attacker.name,
            "defender": defender.name,
            "nat": roll,
            "target_ac": ac,
            "critical": crit,
            "hit": hit
        }))

        if not hit:
            return

        dmg_str = _weapon_damage_str(getattr(attacker, "weapon", None))
        dmg = _roll_damage(dmg_str, self.rng)
        if crit:
            dmg += _roll_damage(dmg_str, self.rng)

        defender.hp -= max(1, dmg)
        if defender.hp <= 0:
            defender.hp = 0
            defender.alive = False

        # track contributors for XP
        tkey = self._key_for(defender)
        akey = self._key_for(attacker)
        self._contributors.setdefault(tkey, set()).add(akey)
        self._last_hitter[tkey] = akey

        self.events.append(Event("damage", {
            "attacker": attacker.name,
            "defender": defender.name,
            "amount": dmg,
            "hp_after": defender.hp
        }))

        if not defender.alive:
            self.events.append(Event("down", {"name": defender.name}))
            self._award_xp_on_down(defender)

    def _award_xp_on_down(self, target: Fighter):
        """
        Distribute XP to anyone who damaged 'target' (solo gets all, else split).
        Multiplies each share by age/dev-trait via total_xp_multiplier.
        """
        tkey = self._key_for(target)
        contributors = list(self._contributors.get(tkey, []))
        if not contributors:
            last = self._last_hitter.get(tkey)
            if last:
                contributors = [last]

        ovr = getattr(target, "ovr", 50)
        xp_value = _challenge_xp_for_ovr(int(ovr))

        if not contributors:
            return

        base_share = max(1, xp_value // len(contributors))

        # Back-map keys to fighters
        key_to_f = {self._key_for(f): f for f in self.fighters}
        for k in contributors:
            f = key_to_f.get(k)
            if f is None or not getattr(f, "alive", True):
                continue

            # ensure xp/level fields exist
            if getattr(f, "xp", None) is None:
                f.xp = 0
            if getattr(f, "level", None) is None:
                f.level = 1

            # apply multipliers
            try:
                mult = total_xp_multiplier(f.__dict__)
            except Exception:
                mult = 1.0
            gained = max(1, int(round(base_share * mult)))

            before_lvl = f.level
            f.xp += gained

            # level-up chain
            try:
                while f.xp >= _next_level_threshold(f.level):
                    # we defer to ratings.level_up if present;
                    # otherwise no-op (fail-safe)
                    from core.ratings import level_up as _lvl_up
                    _lvl_up(f)
                    self.events.append(Event("level_up", {"name": getattr(f, "name", "Fighter"), "level": f.level}))
                    if f.level - before_lvl > 10:  # safety valve
                        break
            except Exception:
                pass

    # -------- turn engine --------
    def _team_alive(self, tid: int) -> bool:
        return any(f.alive and f.team_id == tid for f in self.fighters)

    def _check_end(self):
        a = self._team_alive(0)
        b = self._team_alive(1)
        if a and b:
            return
        if a and not b:
            self.winner = 0
            self.events.append(Event("end", {"winner": self.teamA.name, "reason": "all opponents down"}))
        elif b and not a:
            self.winner = 1
            self.events.append(Event("end", {"winner": self.teamB.name, "reason": "all opponents down"}))
        else:
            self.winner = -1
            self.events.append(Event("end", {"reason": "all fighters down"}))

    def take_turn(self):
        if self.winner is not None:
            return

        if self.turn_index >= len(self.order):
            # new round
            self.round += 1
            self.turn_index = 0
            self.events.append(Event("round_end", {"round": self.round - 1}))
            self.events.append(Event("round_start", {"round": self.round}))

        idx = self.order[self.turn_index]
        actor = self.fighters[idx]
        self.turn_index += 1

        if not actor.alive:
            return  # skip dead

        self.events.append(Event("turn_start", {"actor": actor.name}))

        target = self._nearest_enemy(actor)
        if not target:
            self._check_end()
            return

        if not self._adjacent(actor, target):
            self._try_move_toward(actor, target)

        if actor.alive and target.alive and self._adjacent(actor, target):
            self._attack(actor, target)

        self._check_end()

# ---------- Factories / helpers ----------
def fighter_from_dict(d: dict) -> Fighter:
    w = d.get("weapon", {})
    weapon = Weapon(
        name=w.get("name", "Shortsword"),
        kind=w.get("kind", "melee"),
        damage=w.get("damage", "1d6"),
        attr=w.get("attr", "str"),
        reach=int(w.get("reach", 1)),            # tiles
        crit=tuple(w.get("crit", (20, 2))),
        prof_bonus=int(w.get("prof", 2)),
    )
    str_, dex, con = int(d.get("str", 12)), int(d.get("dex", 12)), int(d.get("con", 12))
    hp = int(d.get("hp", 10 + max(1, ability_mod(con)) * 4))
    ac = int(d.get("ac", 10 + max(0, ability_mod(dex))))
    speed_ft = int(d.get("speed", 30))          # default 30 ft (6 tiles)

    name = d.get("name")
    if not name:
        try:
            from core.creator import make_placeholder_name
            name = make_placeholder_name(random.Random())
        except Exception:
            name = f"Fighter {abs(hash(str(d)))%10000}"

    f = Fighter(
        name=name,
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
        f.tx, f.ty = 1, min(grid_h - 1, i * gap_left)
    gap_right = grid_h // (len(right) + 1) if right else grid_h // 2
    for i, f in enumerate(right, start=1):
        f.tx, f.ty = max(0, grid_w - 2), min(grid_h - 1, i * gap_right)
