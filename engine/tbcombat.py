# engine/tbcombat.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import random

# Try to use your typed events module; fall back to simple dicts if missing.
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
            return f"Match ended: {e.get('winner','draw')}"
        return str(e)

# Ratings hooks (level_up refreshes OVR etc.)
try:
    from core.ratings import level_up
except Exception:
    def level_up(f):  # no-op if ratings not present
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
    # Read a simple "1dX" from weapon, else fallback
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
    # add ability bonus
    # prefer STR; some classes in ratings use DEX for damage—keep simple for v1
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
    ref: Dict             # back-reference to roster dict
    xp: int
    level: int

def _mk_fighters(team: Dict, tid: int, grid_w: int, grid_h: int) -> List[_F]:
    roster = team.get("roster") or team.get("fighters") or []
    roster = roster[:]
    # lay them out: left team near x=1, right team near x=max-2
    fs: List[_F] = []
    gap = grid_h // (len(roster) + 1) if roster else grid_h // 2
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

    # try x then y; if blocked, try y then x
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
    # 5e-like thresholds
    thresholds = [0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000]
    return thresholds[min(max(lvl, 0), len(thresholds) - 1)]

def _award_xp(contributors: List[_F], defeated_ref: Dict, events_typed: List[Dict], events_str: List[str]) -> None:
    xp_val = _challenge_xp_for_ovr(int(defeated_ref.get("ovr", 50)))
    if not contributors:
        return
    share = max(1, xp_val // len(contributors))
    for f in contributors:
        # ensure progress fields exist
        f.xp = int(getattr(f, "xp", 0)) + share
        f.ref["xp"] = f.xp
        # multiple level ups if needed
        before = f.level
        while f.xp >= _next_level_threshold(f.level):
            # ratings.level_up will bump stats + refresh OVR/value/wage
            level_up(f.ref)
            f.level = int(f.ref.get("level", f.level + 1))
            events_typed.append({"type": "level_up", "name": f.name, "level": f.level})
            events_str.append(format_event({"type": "level_up", "name": f.name, "level": f.level}))
            if f.level - before > 10:
                break

class TBCombat:
    """
    Minimal d20 vs AC engine with typed + string logs.
    run(auto=True) returns:
      {
        "kills_home": int, "kills_away": int, "winner": "home"|"away"|None,
        "events_typed": [...], "events": [...]
      }
    """
    def __init__(self, home_team: Dict, away_team: Dict, seed: int, turn_limit: int = 100,
                 grid_w: int = 15, grid_h: int = 9):
        self.seed = int(seed)
        self.turn_limit = int(turn_limit)
        self.grid_w = int(grid_w)
        self.grid_h = int(grid_h)
        self.rng = random.Random(self.seed)

        self.home = _mk_fighters(home_team, 0, grid_w, grid_h)
        self.away = _mk_fighters(away_team, 1, grid_w, grid_h)
        self.fighters: List[_F] = self.home + self.away

        self.events_typed: List[Dict] = []
        self.events_str: List[str] = []

        self.k_home = 0
        self.k_away = 0

    def _alive_team(self, tid: int) -> bool:
        return any(f.alive and f.tid == tid for f in self.fighters)

    def _end_if_done(self) -> Optional[str]:
        a = self._alive_team(0)
        b = self._alive_team(1)
        if a and b:
            return None
        if a and not b:
            return "home"
        if b and not a:
            return "away"
        return None  # both eliminated simultaneously → draw

    def run(self, auto: bool = True) -> Dict[str, Any]:
        # Simple initiative: shuffle once per round
        round_no = 1
        while round_no <= self.turn_limit:
            self.events_typed.append({"type": "round", "round": round_no})
            self.events_str.append(format_event({"type": "round", "round": round_no}))

            order = [f for f in self.fighters if f.alive]
            self.rng.shuffle(order)

            for me in order:
                if not me.alive:
                    continue
                # end early if one side eliminated during the round
                maybe = self._end_if_done()
                if maybe is not None:
                    break

                # choose target and move/attack
                tgt = _nearest_enemy(me, self.fighters)
                if tgt is None:
                    continue  # nothing to do

                # if not adjacent, step toward (speed steps, but do it 1 step/action to keep logs short)
                steps = max(1, int(me.spd))
                for _ in range(steps):
                    if _adjacent(me, tgt):
                        break
                    _step_toward(me, tgt, self.fighters, self.grid_w, self.grid_h)
                    self.events_typed.append({"type":"move","name":me.name,"to":(me.tx,me.ty)})
                    self.events_str.append(format_event({"type":"move","name":me.name,"to":(me.tx,me.ty)}))
                    # target might have changed position due to earlier moves—refresh pointer
                    tgt = _nearest_enemy(me, self.fighters)
                    if tgt is None:
                        break

                if tgt is None:
                    continue

                if _adjacent(me, tgt):
                    # attack!
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
                            # map KO to team kill
                            if tgt.tid == 0:
                                self.k_away += 1
                            else:
                                self.k_home += 1
                            self.events_typed.append({"type":"down","target":tgt.name})
                            self.events_str.append(format_event({"type":"down","target":tgt.name}))
                            # credit XP to the attacker only (simple rule for now)
                            _award_xp([me], tgt.ref, self.events_typed, self.events_str)
                    else:
                        self.events_typed.append({"type":"miss","name":me.name,"target":tgt.name})
                        self.events_str.append(format_event({"type":"miss","name":me.name,"target":tgt.name}))

            winner = self._end_if_done()
            if winner is not None:
                self.events_typed.append({"type":"end","winner":winner})
                self.events_str.append(format_event({"type":"end","winner":winner}))
                return {
                    "kills_home": self.k_home,
                    "kills_away": self.k_away,
                    "winner": winner,
                    "events_typed": self.events_typed,
                    "events": self.events_str,
                }
            round_no += 1

        # Turn limit → draw
        self.events_typed.append({"type":"end","winner":None})
        self.events_str.append(format_event({"type":"end","winner":None}))
        return {
            "kills_home": self.k_home,
            "kills_away": self.k_away,
            "winner": None,
            "events_typed": self.events_typed,
            "events": self.events_str,
        }
