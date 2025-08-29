# engine/tbcombat.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import random

__all__ = ["TBCombat", "Team"]

# --- Optional type for controllers (not required at import time) ---
try:
    from engine.team_tactics import BaseController  # for typing
except Exception:
    class BaseController:  # fallback stub
        def decide(self, world, actor): return []

# --- Team container ---
@dataclass
class Team:
    tid: int
    name: str
    color: Tuple[int, int, int] = (200, 200, 200)

# --- Ability mods ---
def _mod(score: int) -> int:
    try:
        return (int(score) - 10) // 2
    except Exception:
        return 0

def _dex_mod(f) -> int:
    return _mod(getattr(f, "dex", getattr(f, "DEX", 10)))

def _str_mod(f) -> int:
    return _mod(getattr(f, "str", getattr(f, "STR", 10)))

def _ability_mod(f, ability: str) -> int:
    a = ability.upper()
    if a == "DEX": return _dex_mod(f)
    if a == "STR": return _str_mod(f)
    if a == "FINESSE": return max(_dex_mod(f), _str_mod(f))  # 🎯 Patch B
    return 0

# --- Dice helpers ---
def _parse_dice(spec: Any) -> Tuple[int, int]:
    if isinstance(spec, (tuple, list)) and len(spec) == 2:
        return max(1, int(spec[0])), max(1, int(spec[1]))
    if isinstance(spec, str):
        s = spec.lower().strip()
        if "d" in s:
            a, b = s.split("d", 1)
            a = a.strip() or "1"
            try:
                return max(1, int(a)), max(1, int(b))
            except Exception:
                return 1, 4
        try:
            v = int(spec)
            return 1, max(1, v)
        except Exception:
            return 1, 4
    if isinstance(spec, int):
        return 1, max(1, spec)
    return 1, 4

def _roll_dice(rng: random.Random, num: int, sides: int) -> int:
    return sum(rng.randint(1, sides) for _ in range(max(1, num)))

def _roll_d20(rng: random.Random, adv: int = 0) -> Tuple[int, int]:
    adv = 1 if adv > 0 else -1 if adv < 0 else 0
    if adv == 0:
        n = rng.randint(1, 20)
        return n, n
    a = rng.randint(1, 20)
    b = rng.randint(1, 20)
    return (a, max(a, b)) if adv > 0 else (a, min(a, b))

# --- Grid & distance ---
def _chebyshev(a: Tuple[int,int], b: Tuple[int,int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

# --- Helpers ---
def _alive(f) -> bool:
    return bool(getattr(f, "alive", True)) and getattr(f, "hp", 1) > 0

def _ensure_xy(f):
    for attr in ("x", "tx"):
        if not hasattr(f, attr):
            try: setattr(f, attr, 0)
            except Exception: pass
    for attr in ("y", "ty"):
        if not hasattr(f, attr):
            try: setattr(f, attr, 0)
            except Exception: pass

def _name(f) -> str:
    n = getattr(f, "name", None)
    if n: return str(n)
    first = getattr(f, "first", getattr(f, "first_name", "")) or ""
    last  = getattr(f, "last", getattr(f, "last_name", "")) or ""
    s = (first + " " + last).strip()
    return s if s else f"F{getattr(f, 'pid', getattr(f, 'id', '?'))}"

def _team_id(f) -> int:
    return int(getattr(f, "team_id", getattr(f, "tid", 0)))

def _ac(f) -> int:
    if hasattr(f, "ac"):
        try: return int(getattr(f, "ac"))
        except Exception: pass
    dex = getattr(f, "dex", getattr(f, "DEX", 10))
    armor_bonus = getattr(f, "armor_bonus", 0)
    return 10 + _mod(dex) + int(armor_bonus)

def _weapon_profile(f) -> Tuple[int, int, str, int]:
    """
    Returns (num_dice, die_sides, ability_used, reach)
    ability_used in {"STR","DEX","FINESSE"}
    """
    w = getattr(f, "weapon", None)
    if w is None:
        return (1, 4, "STR", 1)

    # dict style: {"dice":"1d8","reach":2,"ability":"STR","finesse":True}
    if isinstance(w, dict):
        num, sides = _parse_dice(w.get("dice", w.get("formula", "1d4")))
        reach = int(w.get("reach", 1))
        ability = str(w.get("ability", w.get("mod", "STR"))).upper()
        finesse = bool(w.get("finesse", False))
        if finesse:
            ability = "FINESSE"
        if ability not in ("STR","DEX","FINESSE"):
            ability = "STR"
        return (num, sides, ability, max(1, reach))

    # str style: "1d6 rapier", "1d8 (finesse) reach=2"
    if isinstance(w, str):
        wl = w.lower()
        reach = 1
        if "reach" in wl:
            try:
                part = wl.split("reach", 1)[1]
                digits = "".join(ch for ch in part if ch.isdigit())
                if digits: reach = int(digits)
            except Exception: pass
        num, sides = _parse_dice(wl.split("reach",1)[0].strip())
        finesse_keys = ("finesse","rapier","dagger","shortsword","scimitar","whip")
        if any(k in wl for k in finesse_keys):
            ability = "FINESSE"
        elif "dex" in wl:
            ability = "DEX"
        else:
            ability = "STR"
        return (num, sides, ability, max(1, reach))

    # int -> 1dX
    if isinstance(w, int):
        num, sides = _parse_dice(w)
        return (num, sides, "STR", 1)

    return (1, 4, "STR", 1)

# --- TBCombat core ---
class TBCombat:
    """
    Turn-based combat on a rectangular grid.

    - Initiative once at start (d20 + DEX mod), fixed across rounds.
    - Per-turn speed (default 4); multi-step movement until in reach.
    - Melee attacks with weapon profiles (XdY + mod), reach, crits on nat 20.
    - Advantage/disadvantage with persistent booleans OR one-shot stacks (Patch B).
    - Opportunity Attacks: leaving an enemy's reach provokes one reaction per enemy per round.
    - Optional Controllers (per-team) to drive behavior/policy.
    - Event stream: 'round_start','turn_start','move_step','blocked','attack','damage','down','end'.
    """
    def __init__(self, teamA: Team, teamB: Team, fighters: List[Any], cols: int, rows: int, seed: Optional[int] = None):
        self.teams = [teamA, teamB]
        self.cols = int(cols)
        self.rows = int(rows)
        self.rng = random.Random(seed if seed is not None else random.randint(0, 10_000_000))

        self.fighters: List[Any] = list(fighters)
        for f in self.fighters:
            _ensure_xy(f)
            if not hasattr(f, "alive"):
                try: setattr(f, "alive", True)
                except Exception: pass
            if not hasattr(f, "hp"):
                try: setattr(f, "hp", getattr(f, "max_hp", 10))
                except Exception: pass
            if not hasattr(f, "speed"):
                try: setattr(f, "speed", 4)
                except Exception: pass
            # Patch B: one-shot adv/dis stacks
            if not hasattr(f, "_adv_once"):
                try: setattr(f, "_adv_once", 0)
                except Exception: pass
            if not hasattr(f, "_dis_once"):
                try: setattr(f, "_dis_once", 0)
                except Exception: pass

        # battle state
        self.events: List[Any] = []
        self.round: int = 1
        self.turn_idx: int = 0
        self.winner: Optional[int] = None

        # initiative & per-round reactions
        self._initiative: List[int] = []
        self._roll_initiative()

        # optional AI controllers per team_id
        self.controllers: Dict[int, BaseController] = {}

        self._push({"type": "round_start", "round": self.round})
        self._reset_reactions_for_round()

    # -------- Public hooks (controllers/UI) --------
    def set_controllers(self, controllers: Dict[int, BaseController]):
        self.controllers = controllers or {}

    def speed(self, actor) -> int:
        return int(getattr(actor, "speed", 4))

    def reach(self, actor) -> int:
        _, _, _, r = _weapon_profile(actor)
        return max(1, int(r))

    def distance(self, a, b) -> int:
        return _chebyshev(self._pos(a), self._pos(b))

    def distance_xy(self, a, xy: Tuple[int, int]) -> int:
        return _chebyshev(self._pos(a), xy)

    def iter_enemies(self, actor):
        tid = _team_id(actor)
        for g in self.fighters:
            if _alive(g) and _team_id(g) != tid:
                yield g

    # 🎯 Patch B: one-shot advantage/disadvantage for next attack
    def grant_advantage(self, f, stacks: int = 1):
        try: setattr(f, "_adv_once", max(0, int(getattr(f, "_adv_once", 0))) + int(stacks))
        except Exception: pass

    def grant_disadvantage(self, f, stacks: int = 1):
        try: setattr(f, "_dis_once", max(0, int(getattr(f, "_dis_once", 0))) + int(stacks))
        except Exception: pass

    # Planner helpers
    def path_step(self, actor, target, *, avoid_oa: bool = True) -> Optional[Tuple[int, int]]:
        ax, ay = self._pos(actor)
        tx, ty = self._pos(target)
        options: List[Tuple[int,int]] = []
        dx = tx - ax; dy = ty - ay
        primary = []
        if abs(dx) >= abs(dy):
            primary = [(1 if dx > 0 else -1, 0)] if dx != 0 else []
            secondary = [(0, 1 if dy > 0 else -1)] if dy != 0 else []
        else:
            primary = [(0, 1 if dy > 0 else -1)] if dy != 0 else []
            secondary = [(1 if dx > 0 else -1, 0)] if dx != 0 else []
        options = primary + secondary + [(1,0), (-1,0), (0,1), (0,-1)]
        best: Optional[Tuple[int,int]] = None
        best_d = 10**9

        for pass_i in (0, 1):  # first try to avoid OA, then allow if blocked
            best = None; best_d = 10**9
            for vx, vy in options:
                nx, ny = ax + vx, ay + vy
                if not self._in_bounds(nx, ny): continue
                if self._occupied(nx, ny): continue
                if avoid_oa and pass_i == 0 and self._would_provoke_oa(actor, (ax, ay), (nx, ny)):  # noqa
                    continue
                d = _chebyshev((nx, ny), (tx, ty))
                if d < best_d:
                    best = (nx, ny); best_d = d
            if best is not None:
                break
        return best

    def path_step_towards(self, actor, xy: Tuple[int, int], *, avoid_oa: bool = True) -> Optional[Tuple[int, int]]:
        ax, ay = self._pos(actor)
        tx, ty = int(xy[0]), int(xy[1])
        dummy = type("T", (), {"x": tx, "y": ty})
        return self.path_step(actor, dummy, avoid_oa=avoid_oa)

    # -------------- main turn --------------
    def take_turn(self):
        if self.winner is not None:
            return

        f_idx = self._next_living_index()
        if f_idx is None:
            self._end_if_finished()
            return

        self.turn_idx = f_idx
        actor = self.fighters[self._initiative[self.turn_idx]]
        if not _alive(actor):
            self._advance_turn_pointer()
            self._end_if_finished()
            return

        self._push({"type": "turn_start", "actor": _name(actor), "actor_id": getattr(actor, "pid", None)})

        ctrl = self.controllers.get(_team_id(actor))
        if ctrl:
            acted = self._execute_controller_turn(ctrl, actor)
            if not acted:
                self._baseline_turn(actor)
        else:
            self._baseline_turn(actor)

        self._advance_turn_pointer()
        self._end_if_finished()

    # -------------- initiative & rounds --------------
    def _roll_initiative(self):
        order = list(range(len(self.fighters)))
        init_scores = []
        for i in order:
            f = self.fighters[i]
            n, eff = _roll_d20(self.rng)
            score = eff + _dex_mod(f)
            init_scores.append((i, score, _dex_mod(f), self.rng.random()))
        init_scores.sort(key=lambda t: (t[1], t[2], t[3]), reverse=True)
        self._initiative = [i for (i, _, __, ___) in init_scores]
        self._reset_reactions_for_round()

    def _reset_reactions_for_round(self):
        for f in self.fighters:
            try: setattr(f, "reaction_ready", True)
            except Exception: pass

    def _advance_turn_pointer(self):
        if len(self._initiative) == 0:
            return
        self.turn_idx = (self.turn_idx + 1) % len(self._initiative)
        if self.turn_idx == 0:
            self.round += 1
            self._push({"type": "round_start", "round": self.round})
            self._reset_reactions_for_round()

    def _next_living_index(self) -> Optional[int]:
        if not self._initiative:
            return None
        n = len(self._initiative)
        for off in range(n):
            idx = (self.turn_idx + off) % n
            f = self.fighters[self._initiative[idx]]
            if _alive(f):
                return idx
        return None

    # -------------- positions & occupancy --------------
    def _pos(self, f) -> Tuple[int,int]:
        return int(getattr(f, "x", getattr(f, "tx", 0))), int(getattr(f, "y", getattr(f, "ty", 0)))

    def _set_pos(self, f, x: int, y: int):
        try: setattr(f, "x", int(x)); setattr(f, "y", int(y))
        except Exception: pass
        try: setattr(f, "tx", int(x)); setattr(f, "ty", int(y))
        except Exception: pass

    def _occupied(self, x: int, y: int) -> Optional[Any]:
        for g in self.fighters:
            if not _alive(g): continue
            gx, gy = self._pos(g)
            if gx == x and gy == y:
                return g
        return None

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.cols and 0 <= y < self.rows

    # -------------- OA helpers & movement --------------
    def _enemies_in_reach_of_pos(self, actor, pos: Tuple[int,int]) -> List[Any]:
        a_team = _team_id(actor)
        out = []
        for e in self.fighters:
            if not _alive(e): continue
            if _team_id(e) == a_team: continue
            ex, ey = self._pos(e)
            if _chebyshev((ex, ey), pos) <= self.reach(e):
                out.append(e)
        return out

    def _would_provoke_oa(self, actor, from_xy: Tuple[int,int], to_xy: Tuple[int,int]) -> bool:
        before = self._enemies_in_reach_of_pos(actor, from_xy)
        after  = self._enemies_in_reach_of_pos(actor, to_xy)
        for e in before:
            if e not in after and getattr(e, "reaction_ready", True) and _alive(e):
                return True
        return False

    def _move_one_step_to(self, actor, nx: int, ny: int) -> bool:
        ax, ay = self._pos(actor)
        if not self._in_bounds(nx, ny): return False
        if self._occupied(nx, ny): return False

        # OA check: leaving reach of any enemy
        provokers = []
        before = self._enemies_in_reach_of_pos(actor, (ax, ay))
        after  = self._enemies_in_reach_of_pos(actor, (nx, ny))
        for e in before:
            if e not in after and getattr(e, "reaction_ready", True) and _alive(e):
                provokers.append(e)

        for e in list(provokers):
            self._opportunity_attack(e, actor)
            try: setattr(e, "reaction_ready", False)
            except Exception: pass
            if not _alive(actor):
                return False

        self._set_pos(actor, nx, ny)
        self._push({"type": "move_step", "actor": _name(actor), "to": (nx, ny)})
        return True

    def _step_towards(self, actor, target) -> bool:
        ax, ay = self._pos(actor)
        tx, ty = self._pos(target)
        options: List[Tuple[int,int]] = []
        dx = tx - ax; dy = ty - ay
        primary = []
        if abs(dx) >= abs(dy):
            primary = [(1 if dx > 0 else -1, 0)] if dx != 0 else []
            secondary = [(0, 1 if dy > 0 else -1)] if dy != 0 else []
        else:
            primary = [(0, 1 if dy > 0 else -1)] if dy != 0 else []
            secondary = [(1 if dx > 0 else -1, 0)] if dx != 0 else []
        options = primary + secondary + [(1,0), (-1,0), (0,1), (0,-1)]

        tried = set()
        for vx, vy in options:
            nx, ny = ax + vx, ay + vy
            if (nx, ny) in tried: continue
            tried.add((nx, ny))
            if self._move_one_step_to(actor, nx, ny):
                return True
        self._push({"type": "blocked", "actor": _name(actor), "at": (ax, ay)})
        return False

    # -------------- Attacking --------------
    def _compute_advantage(self, attacker, defender) -> int:
        """Return -1/0/+1 and consume one-shot stacks if present."""
        adv = 0
        if getattr(attacker, "advantage", False): adv += 1
        if getattr(attacker, "disadvantage", False): adv -= 1
        # consume one-shot stacks (Patch B)
        ao = max(0, int(getattr(attacker, "_adv_once", 0)))
        do = max(0, int(getattr(attacker, "_dis_once", 0)))
        if ao > 0:
            adv += 1
            try: setattr(attacker, "_adv_once", ao - 1)
            except Exception: pass
        if do > 0:
            adv -= 1
            try: setattr(attacker, "_dis_once", do - 1)
            except Exception: pass
        return 1 if adv > 0 else -1 if adv < 0 else 0

    def _attack(self, attacker, defender, *, is_reaction: bool = False):
        if not (_alive(attacker) and _alive(defender)):
            return

        adv = self._compute_advantage(attacker, defender)
        nat, eff = _roll_d20(self.rng, adv=adv)
        num, sides, ability, reach = _weapon_profile(attacker)
        atk_mod = _ability_mod(attacker, ability)
        ac = _ac(defender)
        crit = (nat == 20)
        hit = (eff + atk_mod >= ac) or crit

        self._push({
            "type": "attack",
            "actor": _name(attacker),
            "target": _name(defender),
            "roll": nat,
            "effective": eff,
            "mod": atk_mod,
            "target_ac": ac,
            "hit": hit,
            "critical": crit,
            "opportunity": bool(is_reaction),
        })

        if hit:
            dice_num = num * (2 if crit else 1)
            dmg = _roll_dice(self.rng, dice_num, sides) + atk_mod
            if dmg < 1: dmg = 1
            self._apply_damage(attacker, defender, dmg)

    def _opportunity_attack(self, attacker, mover):
        self._attack(attacker, mover, is_reaction=True)

    def _apply_damage(self, attacker, defender, dmg: int):
        try:
            defender.hp = int(defender.hp) - int(dmg)
        except Exception:
            pass
        self._push({"type": "damage", "actor": _name(attacker), "target": _name(defender), "amount": int(dmg)})
        if getattr(defender, "hp", 0) <= 0 and _alive(defender):
            try: setattr(defender, "alive", False)
            except Exception: pass
            self._push({"type": "down", "name": _name(defender)})

    # -------------- Controller execution --------------
    def _execute_controller_turn(self, ctrl: BaseController, actor) -> bool:
        intents = ctrl.decide(self, actor) or []
        if not intents:
            return False

        steps_left = self.speed(actor)
        acted = False
        attacked = False
        for it in intents:
            typ = (it.get("type") if isinstance(it, dict) else None) or "end"
            if typ == "move" and steps_left > 0:
                to = it.get("to")
                if isinstance(to, (list, tuple)) and len(to) == 2:
                    nx, ny = int(to[0]), int(to[1])
                    if self._move_one_step_to(actor, nx, ny):
                        steps_left -= 1
                        acted = True
                        continue
            elif typ == "attack" and not attacked:
                target = it.get("target")
                if target is not None and _alive(target):
                    if _chebyshev(self._pos(actor), self._pos(target)) <= self.reach(actor):
                        self._attack(actor, target)
                        attacked = True
                        acted = True
                        break
            elif typ == "end":
                break

        return acted or attacked

    # -------------- Baseline AI --------------
    def _baseline_turn(self, actor):
        enemy = self._choose_target(actor)
        if enemy is None:
            return
        if _chebyshev(self._pos(actor), self._pos(enemy)) <= self.reach(actor):
            self._attack(actor, enemy)
            return

        steps = max(0, self.speed(actor))
        for _ in range(steps):
            if _chebyshev(self._pos(actor), self._pos(enemy)) <= self.reach(actor):
                break
            moved = self._step_towards(actor, enemy)
            if not moved:
                break
            if not _alive(enemy):
                break
        if _alive(actor) and _alive(enemy) and _chebyshev(self._pos(actor), self._pos(enemy)) <= self.reach(actor):
            self._attack(actor, enemy)

    def _choose_target(self, actor) -> Optional[Any]:
        best = None
        best_d = 10**9
        ax, ay = self._pos(actor)
        a_team = _team_id(actor)
        for g in self.fighters:
            if not _alive(g): continue
            if _team_id(g) == a_team: continue
            d = _chebyshev((ax, ay), self._pos(g))
            if d < best_d:
                best = g; best_d = d
            elif d == best_d:
                if getattr(g, "hp", 1) < getattr(best, "hp", 1):
                    best = g
        return best

    # -------------- End & events --------------
    def _end_if_finished(self):
        alive0 = any(_alive(f) and _team_id(f) == 0 for f in self.fighters)
        alive1 = any(_alive(f) and _team_id(f) == 1 for f in self.fighters)
        if alive0 and alive1:
            return
        if alive0 and not alive1:
            self.winner = 0
        elif alive1 and not alive0:
            self.winner = 1
        else:
            self.winner = None
        self._push({"type": "end", "winner": self.winner})

    def _push(self, e: Any):
        self.events.append(e)
