# engine/tbcombat.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Iterable
import random

try:
    from .events import format_event  # type: ignore
except Exception:
    def format_event(e) -> str:
        t = e.get("type", "?")
        if t == "move":
            return f"{e['name']} moves to {e['to']}"
        if t == "hit":
            return f"{e['name']} hits {e['target']} for {e['dmg']}!"
        if t == "miss":
            return f"{e['name']} misses {e['target']}"
        if t == "down":
            return f"{e['target']} is down!"
        if t == "level_up":
            return f"{e['name']} reached level {e['level']}!"
        if t == "round":
            return f"— Round {e['round']} —"
        if t == "end":
            w = e.get("winner", None)
            return f"Match ended: {w if w is not None else 'draw'}"
        return str(e)

try:
    from core.ratings import level_up
except Exception:
    def level_up(f):
        f["level"] = f.get("level", 1) + 1

def ability_mod(score: int) -> int:
    return (int(score) - 10) // 2

def d20(rng: random.Random) -> int:
    return rng.randint(1, 20)

def expected_hp(f: Dict) -> int:
    return int(f.get("hp", 10))

def attack_bonus(f: Dict) -> int:
    prof = int(f.get("prof", 2))
    atk_mod = int(f.get("atk_mod", ability_mod(f.get("str", 10)) + prof))
    return atk_mod

def target_ac(f: Dict) -> int:
    return int(f.get("ac", 12))

def damage_roll(f: Dict, crit: bool, rng: random.Random) -> int:
    dmg = 0
    w = f.get("weapon", {"damage": "1d6"})
    try:
        s = w.get("damage", "1d6").lower()
        n, s = s.split("d")
        n = int(n) * (2 if crit else 1)
        s = int(s)
        dmg = sum(rng.randint(1, s) for _ in range(max(1, n)))
    except Exception:
        dmg = rng.randint(1, 6) * (2 if crit else 1)
    dmg += max(0, ability_mod(int(f.get("str", 10))))
    return max(0, dmg)

@dataclass
class _F:
    name: str
    tid: int
    tx: int
    ty: int
    hp: int
    ac: int
    spd: int
    alive: bool
    ref: Dict                # dict snapshot for combat math
    xp: int
    level: int
    origin: Optional[Any] = None  # original object to propagate XP/level to (if not dict)

def _mk_from_external(ob: Any, default_tx: int = 0, default_ty: int = 0) -> _F:
    get = lambda k, d=None: (getattr(ob, k, None) if not isinstance(ob, dict) else ob.get(k, None)) or d
    name = get("name", "F")
    tid = int(get("team_id", 0))
    tx = int(get("x", get("tx", default_tx)))
    ty = int(get("y", get("ty", default_ty)))
    hp = int(get("hp", 10))
    ac = int(get("ac", 12))
    spd = int(get("speed", 6))
    lvl = int(get("level", 1))
    xp  = int(get("xp", 0))
    if isinstance(ob, dict):
        ref = ob
        origin = None
    else:
        # keep a dict for fast math but remember origin to propagate XP/level
        ref = {
            "name": name, "team_id": tid, "hp": hp, "ac": ac, "speed": spd,
            "level": lvl, "xp": xp, "str": getattr(ob, "str", 10),
            "prof": getattr(ob, "prof", 2), "atk_mod": getattr(ob, "atk_mod", ability_mod(getattr(ob, "str", 10)) + 2),
            "weapon": getattr(ob, "weapon", {"damage": "1d6"}),
            "ovr": getattr(ob, "ovr", 50),
        }
        origin = ob
    return _F(name=name, tid=tid, tx=tx, ty=ty, hp=hp, ac=ac, spd=spd, alive=True, ref=ref, xp=xp, level=lvl, origin=origin)

def _mk_from_team_dict(team: Dict, tid: int, grid_w: int, grid_h: int) -> List[_F]:
    roster = team.get("roster") or team.get("fighters") or []
    roster = roster[:]
    fs: List[_F] = []
    gap = grid_h // (len(roster) + 1) if roster else max(1, grid_h // 2)
    base_x = 1 if tid == 0 else max(0, grid_w - 2)
    for i, rd in enumerate(roster, start=1):
        fs.append(_F(
            name=rd.get("name", f"P{tid}-{i}"),
            tid=tid,
            tx=base_x,
            ty=min(grid_h - 1, i * gap),
            hp=expected_hp(rd),
            ac=target_ac(rd),
            spd=int(rd.get("speed", 6)),
            alive=True,
            ref=rd,
            xp=int(rd.get("xp", 0)),
            level=int(rd.get("level", 1)),
            origin=None,
        ))
    return fs

def _nearest_enemy(me: _F, fighters: List[_F]) -> Optional[_F]:
    enemies = [f for f in fighters if f.alive and f.tid != me.tid]
    if not enemies:
        return None
    return min(enemies, key=lambda e: abs(e.tx - me.tx) + abs(e.ty - me.ty))

def _step_toward(me: _F, tgt: _F, fighters: List[_F], grid_w: int, grid_h: int) -> None:
    if not tgt:
        return
    def free(nx, ny) -> bool:
        if nx < 0 or ny < 0 or nx >= grid_w or ny >= grid_h:
            return False
        for o in fighters:
            if o.alive and o.tx == nx and o.ty == ny:
                return False
        return True
    dx = 1 if tgt.tx > me.tx else -1 if tgt.tx < me.tx else 0
    dy = 1 if tgt.ty > me.ty else -1 if tgt.ty < me.ty else 0
    nx, ny = me.tx + dx, me.ty
    if dx != 0 and free(nx, ny):
        me.tx, me.ty = nx, ny
        return
    nx, ny = me.tx, me.ty + dy
    if dy != 0 and free(nx, ny):
        me.tx, me.ty = nx, ny

def _adjacent(a: _F, b: _F) -> bool:
    return abs(a.tx - b.tx) + abs(a.ty - b.ty) == 1

def _challenge_xp_for_ovr(ovr: int) -> int:
    if ovr < 35:   return 25
    if ovr < 45:   return 50
    if ovr < 55:   return 100
    if ovr < 65:   return 200
    if ovr < 70:   return 450
    if ovr < 75:   return 700
    if ovr < 80:   return 1100
    if ovr < 85:   return 1800
    return 2300

def _next_level_threshold(lvl: int) -> int:
    thresholds = [0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000]
    return thresholds[min(max(lvl, 0), len(thresholds) - 1)]

def _award_xp(contributors: List[_F], defeated_ref: Dict, events_typed: List[Dict], events_str: List[str]) -> None:
    xp_val = _challenge_xp_for_ovr(int(defeated_ref.get("ovr", 50)))
    if not contributors or xp_val <= 0:
        return
    share = max(1, xp_val // len(contributors))
    for f in contributors:
        f.xp = int(getattr(f, "xp", 0)) + share
        f.ref["xp"] = f.xp
        leveled = 0
        while f.xp >= _next_level_threshold(f.level):
            level_up(f.ref)
            f.level = int(f.ref.get("level", f.level + 1))
            events_typed.append({"type": "level_up", "name": f.name, "level": f.level})
            events_str.append(format_event({"type": "level_up", "name": f.name, "level": f.level}))
            leveled += 1
            if leveled > 10:
                break
        # propagate XP/level back to original object if present
        if f.origin is not None:
            try:
                setattr(f.origin, "xp", f.xp)
            except Exception:
                pass
            try:
                setattr(f.origin, "level", f.level)
            except Exception:
                pass

class TBCombat:
    """
    Flexible ctor:
      (1) New path:
          TBCombat(home_team_dict, away_team_dict, seed: int, turn_limit=100, grid_w=15, grid_h=9)
      (2) Legacy test path:
          TBCombat(teamA, teamB, fighters_list, GRID_W, GRID_H, seed=999)
    """
    def __init__(self, home_team: Any, away_team: Any, *args, **kwargs):
        self.turn_limit = int(kwargs.pop("turn_limit", 100))
        self.grid_w = int(kwargs.pop("grid_w", 15))
        self.grid_h = int(kwargs.pop("grid_h", 9))

        self.round_no = 1
        self.winner: Optional[int] = None  # tests expect 0 or 1
        self.events_typed: List[Dict] = []
        self.events_str: List[str] = []
        self.k_home = 0
        self.k_away = 0

        # Legacy signature: third positional is fighter list
        if args and isinstance(args[0], (list, tuple)):
            fighters_in: Iterable[Any] = args[0]
            if len(args) >= 3:
                self.grid_w = int(args[1])
                self.grid_h = int(args[2])
            self.seed = int(kwargs.get("seed", 0))
            self.rng = random.Random(self.seed)
            self.fighters: List[_F] = [_mk_from_external(ob, 0, idx) for idx, ob in enumerate(fighters_in)]
            return

        # New path (team dicts + seed positional or kw)
        if args:
            seed = int(args[0])
        else:
            seed = int(kwargs.get("seed", 0))
        self.seed = seed
        self.rng = random.Random(self.seed)

        self.grid_w = int(kwargs.get("grid_w", self.grid_w))
        self.grid_h = int(kwargs.get("grid_h", self.grid_h))

        self.home = _mk_from_team_dict(home_team, 0, self.grid_w, self.grid_h)
        self.away = _mk_from_team_dict(away_team, 1, self.grid_w, self.grid_h)
        self.fighters: List[_F] = self.home + self.away

    def step(self) -> None:
        if self.winner is not None or self.round_no > self.turn_limit:
            return
        self.events_typed.append({"type": "round", "round": self.round_no})
        self.events_str.append(format_event({"type": "round", "round": self.round_no}))

        order = [f for f in self.fighters if f.alive]
        self.rng.shuffle(order)
        for me in order:
            if not me.alive:
                continue
            maybe = self._end_if_done()
            if maybe is not None:
                self.winner = maybe
                break
            tgt = _nearest_enemy(me, self.fighters)
            if tgt is None:
                continue
            steps = max(1, int(me.spd))
            for _ in range(steps):
                if _adjacent(me, tgt):
                    break
                _step_toward(me, tgt, self.fighters, self.grid_w, self.grid_h)
                self.events_typed.append({"type":"move","name":me.name,"to":(me.tx,me.ty)})
                self.events_str.append(format_event({"type":"move","name":me.name,"to":(me.tx,me.ty)}))
                tgt = _nearest_enemy(me, self.fighters)
                if tgt is None:
                    break
            if tgt is None:
                continue
            if _adjacent(me, tgt):
                roll = d20(self.rng)
                crit = (roll == 20)
                total = roll + attack_bonus(me.ref)
                if crit or total >= tgt.ac:
                    dmg = damage_roll(me.ref, crit, self.rng)
                    tgt.hp -= dmg
                    self.events_typed.append({"type":"hit","name":me.name,"target":tgt.name,"dmg":dmg,"crit":crit})
                    self.events_str.append(format_event({"type":"hit","name":me.name,"target":tgt.name,"dmg":dmg,"crit":crit}))
                    if tgt.hp <= 0 and tgt.alive:
                        tgt.alive = False
                        if tgt.tid == 0: self.k_away += 1
                        else:            self.k_home += 1
                        self.events_typed.append({"type":"down","target":tgt.name})
                        self.events_str.append(format_event({"type":"down","target":tgt.name}))
                        _award_xp([me], tgt.ref, self.events_typed, self.events_str)
                else:
                    self.events_typed.append({"type":"miss","name":me.name,"target":tgt.name})
                    self.events_str.append(format_event({"type":"miss","name":me.name,"target":tgt.name}))
        maybe = self._end_if_done()
        if maybe is not None and self.winner is None:
            self.winner = maybe  # 0 or 1
            self.events_typed.append({"type":"end","winner":maybe})
            self.events_str.append(format_event({"type":"end","winner":maybe}))
        self.round_no += 1
        if self.round_no > self.turn_limit and self.winner is None:
            # If somehow nobody died, force a winner by comparing kills
            self.winner = 0 if self.k_home >= self.k_away else 1
            self.events_typed.append({"type":"end","winner":self.winner})
            self.events_str.append(format_event({"type":"end","winner":self.winner}))

    # alias expected by tests
    def take_turn(self) -> None:
        self.step()

    def run(self, auto: bool = True) -> Dict[str, Any]:
        while self.winner is None and self.round_no <= self.turn_limit:
            self.step()
        return {
            "kills_home": self.k_home,
            "kills_away": self.k_away,
            "winner": self.winner,
            "events_typed": self.events_typed,
            "events": self.events_str,
        }

    def _alive_team(self, tid: int) -> bool:
        return any(f.alive and f.tid == tid for f in self.fighters)

    def _end_if_done(self) -> Optional[int]:
        a = self._alive_team(0)
        b = self._alive_team(1)
        if a and b: return None
        if a and not b: return 0
        if b and not a: return 1
        return None
