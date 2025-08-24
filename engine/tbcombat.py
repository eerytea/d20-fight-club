# engine/tbcombat.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Set, Any
import random, re

from .model import Fighter, Team, Weapon  # uses your modular model
from .grid import manhattan

# ---- dice helpers (ported from old engine) ----
def _weapon_damage_str(wpn) -> str:
    if wpn is None:
        return "1d6"
    if isinstance(wpn, dict):
        return wpn.get("damage", "1d6")
    if hasattr(wpn, "damage") and getattr(wpn, "damage"):
        return getattr(wpn, "damage")
    if hasattr(wpn, "damage_die") and getattr(wpn, "damage_die"):
        return getattr(wpn, "damage_die")
    return "1d6"

import re
_DIE_FULL = re.compile(r"^\s*(\d+)[dD](\d+)(?:\+(\d+))?\s*$")

def _roll_damage(dmg_str: str, rng: random.Random) -> int:
    """
    Supports 'XdY', 'XdY+Z', or a flat integer like '4'.
    """
    s = (dmg_str or "1d6").strip()
    m = _DIE_FULL.match(s)
    if m:
        n = int(m.group(1))
        sides = int(m.group(2))
        bonus = int(m.group(3) or 0)
        total = sum(rng.randint(1, sides) for _ in range(max(1, n))) + bonus
        return max(1, total)
    # fall back: flat integer
    try:
        return max(1, int(s))
    except Exception:
        return 1


# optional ratings hook
try:
    from core.ratings import level_up   # if you have a level_up(fighter) helper
except Exception:
    def level_up(f): pass

# simple OVR→XP mapping from your old engine
def _challenge_xp_for_ovr(ovr: int) -> int:
    if ovr < 35:   return 25
    if ovr < 45:   return 50
    if ovr < 55:   return 100
    if ovr < 65:   return 200
    if ovr < 70:   return 450
    if ovr < 75:   return 700
    if ovr < 80:   return 1100
    if ovr < 85:   return 1800
    if ovr < 88:   return 2300
    return 2900

# simple D&D-like XP thresholds
_XP_THRESHOLDS = [0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000, 100000]
def _next_level_threshold(lvl: int) -> int:
    if lvl < 1: lvl = 1
    if lvl >= len(_XP_THRESHOLDS):
        return _XP_THRESHOLDS[-1] + 50000 * (lvl - (len(_XP_THRESHOLDS) - 1))
    return _XP_THRESHOLDS[lvl]

@dataclass
class Event:
    kind: str
    payload: Dict[str, Any]

# --- Weapon normalization helper (paste above TBCombat class) ---
from typing import Any

def normalize_weapon(wpn: Any):
    """
    Accepts a Weapon instance, a dict of fields, or a known string key.
    Returns a proper Weapon object; falls back to Unarmed.
    """
    # Lazy imports to avoid cycles if model imports tbcombat
    try:
        from .model import Weapon, WEAPON_CATALOG  # adjust names if yours differ
    except Exception:
        # Fallbacks if catalog not present; keep the code resilient
        class Weapon:  # very small local stand-in
            def __init__(self, name="Unarmed", dmg=(1, 4, 0), reach=1, crit=(20,2)):
                self.name = name
                self.dmg = dmg
                self.reach = reach
                self.crit = crit
        WEAPON_CATALOG = {
            "Unarmed": Weapon("Unarmed", (1,4,0), 1, (20,2))
        }

    if isinstance(wpn, Weapon):
        return wpn
    if isinstance(wpn, dict):
        # allow partial dicts
        name  = wpn.get("name", "Unarmed")
        dmg   = tuple(wpn.get("dmg", (1,4,0)))
        reach = int(wpn.get("reach", 1))
        crit  = tuple(wpn.get("crit", (20,2)))
        return Weapon(name=name, dmg=dmg, reach=reach, crit=crit)
    if isinstance(wpn, str):
        # match by key or by weapon name in catalog
        if wpn in WEAPON_CATALOG:
            return WEAPON_CATALOG[wpn]
        # try name-based lookup
        for v in WEAPON_CATALOG.values():
            if getattr(v, "name", None) == wpn:
                return v
    # final fallback
    return WEAPON_CATALOG.get("Unarmed") or Weapon("Unarmed", (1,4,0), 1, (20,2))
# --- end helper ---


class TBCombat:
    """
    Turn-based grid combat with:
    - initiative order + round events
    - greedy Manhattan movement (avoid off-board and occupied tiles)
    - d20 attack events: attack, damage, down, end
    - XP award to damage contributors on down + optional level_up
    - event log accessible via self.events
    """
    def __init__(self, teamA: Team, teamB: Team, fighters: List[Fighter], grid_w: int, grid_h: int, seed: Optional[int] = None):
        self.teamA = teamA
        self.teamB = teamB
        self.fighters = fighters
        self.grid_w, self.grid_h = grid_w, grid_h
        self.rng = random.Random(seed)
        self.events: List[Event] = []
        self.round = 1
        self.turn_index = 0
        self.winner: Optional[int] = None  # 0 = teamA, 1 = teamB, -1 = draw

        # init fields & initiative
        for f in self.fighters:
            if getattr(f, "hp", None) is None:
                f.hp = f.max_hp
            f.alive = True
            setattr(f, "_init", self.rng.randint(1, 20))

            if getattr(f, "level", None) is None:
                f.level = 1
            if getattr(f, "xp", None) is None:
                f.xp = 0

        # initiative order (desc)
        self.order = sorted(range(len(self.fighters)), key=lambda i: getattr(self.fighters[i], "_init", 0), reverse=True)

        # XP bookkeeping
        self._contributors: Dict[int, Set[int]] = {}   # target_idx -> set(attacker_idx)
        self._last_hitter: Dict[int, int] = {}

        # init events
        for f in self.fighters:
            self.events.append(Event("init", {"name": f.name, "init": getattr(f, "_init", 0)}))
        self.events.append(Event("round_start", {"round": self.round}))

    # --- utility ---
    def _enemies_of(self, tid: int) -> List[int]:
        return [i for i, f in enumerate(self.fighters) if f.alive and f.team_id != tid]

    def _nearest_enemy_idx(self, actor_idx: int) -> Optional[int]:
        ax = self.fighters[actor_idx]
        enemies = self._enemies_of(ax.team_id)
        if not enemies: return None
        return min(enemies, key=lambda j: manhattan(ax.tx, ax.ty, self.fighters[j].tx, self.fighters[j].ty))

    def _adjacent(self, a: Fighter, b: Fighter) -> bool:
        return manhattan(a.tx, a.ty, b.tx, b.ty) == 1

    def _free(self, x: int, y: int, ignore_idx: Optional[int] = None) -> bool:
        if x < 0 or y < 0 or x >= self.grid_w or y >= self.grid_h: return False
        for k, o in enumerate(self.fighters):
            if k == ignore_idx: continue
            if o.alive and o.tx == x and o.ty == y: return False
        return True

    def _step_toward(self, a: Fighter, tx: int, ty: int, idx: int) -> bool:
        dx = 1 if tx > a.tx else -1 if tx < a.tx else 0
        dy = 1 if ty > a.ty else -1 if ty < a.ty else 0
        # try x first then y, fallback swap
        if dx != 0 and self._free(a.tx + dx, a.ty, idx):
            a.tx += dx; return True
        if dy != 0 and self._free(a.tx, a.ty + dy, idx):
            a.ty += dy; return True
        if dy != 0 and self._free(a.tx, a.ty + dy, idx):
            a.ty += dy; return True
        if dx != 0 and self._free(a.tx + dx, a.ty, idx):
            a.tx += dx; return True
        return False

    # --- actions ---
    def _attack(self, ai: int, di: int):
        attacker = self.fighters[ai]
        defender = self.fighters[di]
        atk_mod = getattr(attacker, "atk_mod", 0)
        ac = getattr(defender, "ac", 12)
        d20 = self.rng.randint(1, 20)
        crit = (d20 == 20)
        hit = (d20 + atk_mod >= ac) or crit

        self.events.append(Event("attack", {
            "attacker": attacker.name, "defender": defender.name,
            "nat": d20, "target_ac": ac, "critical": crit, "hit": hit,
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

        # track contributors
        self._contributors.setdefault(di, set()).add(ai)
        self._last_hitter[di] = ai

        self.events.append(Event("damage", {
            "attacker": attacker.name, "defender": defender.name,
            "amount": dmg, "hp_after": defender.hp
        }))

        if not defender.alive:
            self.events.append(Event("down", {"name": defender.name}))
            self._award_xp_on_down(di)

    def _award_xp_on_down(self, target_i: int):
        contribs = list(self._contributors.get(target_i, []))
        if not contribs:
            last = self._last_hitter.get(target_i)
            if last is not None:
                contribs = [last]
        if not contribs:
            return
        target = self.fighters[target_i]
        xp_value = _challenge_xp_for_ovr(int(getattr(target, "ovr", 50)))
        share = max(1, xp_value // max(1, len(contribs)))
        for ai in contribs:
            f = self.fighters[ai]
            if not getattr(f, "alive", True):
                continue
            if getattr(f, "xp", None) is None: f.xp = 0
            if getattr(f, "level", None) is None: f.level = 1
            before = f.level
            f.xp += share
            while f.xp >= _next_level_threshold(f.level):
                level_up(f)
                self.events.append(Event("level_up", {"name": f.name, "level": f.level}))
                if f.level - before > 10:  # safety
                    break

    def _team_alive(self, tid: int) -> bool:
        return any(f.alive and f.team_id == tid for f in self.fighters)

    def _check_end(self):
        a = self._team_alive(0); b = self._team_alive(1)
        if a and b: return
        if a and not b:
            self.winner = 0; self.events.append(Event("end", {"winner": self.teamA.name, "reason": "all opponents down"}))
        elif b and not a:
            self.winner = 1; self.events.append(Event("end", {"winner": self.teamB.name, "reason": "all opponents down"}))
        else:
            self.winner = -1; self.events.append(Event("end", {"reason": "all fighters down"}))

    def take_turn(self):
        if self.winner is not None:
            return

        if self.turn_index >= len(self.order):
            # round rollover
            self.events.append(Event("round_end", {"round": self.round}))
            self.round += 1
            self.turn_index = 0
            self.events.append(Event("round_start", {"round": self.round}))

        i = self.order[self.turn_index]
        self.turn_index += 1
        actor = self.fighters[i]
        if not actor.alive:
            return

        self.events.append(Event("turn_start", {"actor": actor.name}))

        tgt_i = self._nearest_enemy_idx(i)
        if tgt_i is None:
            self._check_end()
            return
        target = self.fighters[tgt_i]

        # move toward target until adjacent or out of steps
        steps = getattr(actor, "speed", 6)
        for _ in range(max(1, steps)):
            if not actor.alive or not target.alive:
                break
            if self._adjacent(actor, target):
                break
            if not self._step_toward(actor, target.tx, target.ty, i):
                break
            self.events.append(Event("move_step", {"name": actor.name, "to": (actor.tx, actor.ty)}))

        # move toward target until within reach
        reach = 1
        wpn = getattr(actor, "weapon", None)
            if isinstance(wpn, dict):
        reach = int(wpn.get("reach", 1))
            elif hasattr(wpn, "reach"):
        reach = int(getattr(wpn, "reach") or 1)

    def _in_reach(a, b, r):
        return manhattan(a.tx, a.ty, b.tx, b.ty) <= max(1, r)

        steps = getattr(actor, "speed", 6)
        for _ in range(max(1, steps)):
        if not actor.alive or not target.alive:
        break
        if _in_reach(actor, target, reach):
        break
        if not self._step_toward(actor, target.tx, target.ty, i):
        break
        self.events.append(Event("move_step", {"name": actor.name, "to": (actor.tx, actor.ty)}))

        if actor.alive and target.alive and _in_reach(actor, target, reach):
        self._attack(i, tgt_i)


        self._check_end()
