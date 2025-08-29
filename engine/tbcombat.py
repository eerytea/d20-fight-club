# engine/tbcombat.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import random

from engine.conditions import (
    CONDITION_PRONE, CONDITION_RESTRAINED, CONDITION_STUNNED,
    ensure_bag, has_condition, add_condition, clear_condition, decrement_all_for_turn
)
from engine.spells import line_aoe_cells

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
    name: str = "Team"
    color: Tuple[int, int, int] = (200, 200, 200)

# --- Helpers for names/pos ---
def _name(f) -> str:
    try:
        n = getattr(f, "name", None)
        if n: return str(n)
        fn = getattr(f, "first_name", "")
        ln = getattr(f, "last_name", "")
        s = (fn + " " + ln).strip()
        return s or f"F{getattr(f, 'pid', getattr(f, 'id', ''))}"
    except Exception:
        return "Fighter"

def _ensure_xy(f):
    if hasattr(f, "tx") and hasattr(f, "ty"):
        try: setattr(f, "x", int(getattr(f, "tx")))
        except Exception: pass
        try: setattr(f, "y", int(getattr(f, "ty")))
        except Exception: pass
        return
    if hasattr(f, "x") and hasattr(f, "y"):
        return
    try: setattr(f, "x", int(getattr(f, "cx", getattr(f, "grid_x", 0))))
    except Exception: setattr(f, "x", 0)
    try: setattr(f, "y", int(getattr(f, "cy", getattr(f, "grid_y", 0))))
    except Exception: setattr(f, "y", 0)

def _team_id(f) -> int:
    for k in ("team_id", "tid", "team", "side"):
        if hasattr(f, k):
            try: return int(getattr(f, k))
            except Exception: pass
    return 0

def _mod(score: int) -> int:
    try:
        return (int(score) - 10) // 2
    except Exception:
        return 0

def _dex_mod(f) -> int:
    return _mod(getattr(f, "dex", getattr(f, "DEX", 10)))

def _str_mod(f) -> int:
    return _mod(getattr(f, "str", getattr(f, "STR", 10)))

def _con_mod(f) -> int:
    return _mod(getattr(f, "con", getattr(f, "CON", 10)))

def _int_mod(f) -> int:
    return _mod(getattr(f, "int", getattr(f, "INT", 10)))

def _wis_mod(f) -> int:
    return _mod(getattr(f, "wis", getattr(f, "WIS", 10)))

def _cha_mod(f) -> int:
    return _mod(getattr(f, "cha", getattr(f, "CHA", 10)))

def _ability_mod(f, ability: str) -> int:
    a = (ability or "").upper()
    if a == "DEX": return _dex_mod(f)
    if a == "STR": return _str_mod(f)
    if a == "CON": return _con_mod(f)
    if a == "INT": return _int_mod(f)
    if a == "WIS": return _wis_mod(f)
    if a == "CHA": return _cha_mod(f)
    if a == "FINESSE": return max(_dex_mod(f), _str_mod(f))  # Patch B
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

def _as_int(v, default=0) -> int:
    try: return int(v)
    except Exception: return default

# --- Weapon traits ---
def _weapon_profile(f) -> Tuple[int, int, str, int]:
    w = getattr(f, "weapon", None)
    if w is None:
        return (1, 4, "STR", 1)
    if isinstance(w, dict):
        num, sides = _parse_dice(w.get("dice", w.get("formula", "1d4")))
        reach = int(w.get("reach", 1))
        ability = str(w.get("ability", w.get("mod", "STR"))).upper()
        finesse = bool(w.get("finesse", False))
        if finesse: ability = "FINESSE"
        if ability not in ("STR","DEX","FINESSE"): ability = "STR"
        return (num, sides, ability, max(1, reach))
    if isinstance(w, str):
        wl = w.lower()
        reach = 1
        if "reach" in wl:
            import re
            m = re.search(r"reach\s*=?\s*(\d+)", wl)
            if m: reach = int(m.group(1))
        finesse = ("finesse" in wl)
        ability = "FINESSE" if finesse else ("DEX" if any(k in wl for k in ("bow","javelin","ranged","crossbow","sling","dart")) else "STR")
        num, sides = _parse_dice(wl.split()[0] if wl.split() else "1d4")
        return (num, sides, ability, max(1, reach))
    return (1, 4, "STR", 1)

def _ranged_info(f) -> Tuple[bool, int, int, str]:
    w = getattr(f, "weapon", None)
    if isinstance(w, dict) and w.get("ranged", False):
        rng = w.get("range", (0, 0))
        nr = _as_int(rng[0] if isinstance(rng, (list, tuple)) and len(rng) >= 1 else 0, 0)
        lr = _as_int(rng[1] if isinstance(rng, (list, tuple)) and len(rng) >= 2 else nr, nr)
        ability = str(w.get("ability", "DEX")).upper()
        return True, nr, lr, ability
    if isinstance(w, str) and any(k in w.lower() for k in ("bow","javelin","sling","crossbow","ranged","dart")):
        return True, 12, 24, "DEX"
    return False, 0, 0, "DEX"

class TBCombat:
    """
    Turn-based combat with simple 5e-like rules (scoped).

    Patch D: Dash/Disengage/Dodge/Hide/Ready + reactions pool.
    Patch E: Saving Throws + Conditions (Prone/Restrained/Stunned) + Concentration hook.
    Patch F: Healing + Simple Spells (spell attack, save-based, line AoE).
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
            # Patch D statuses
            try: setattr(f, "_status_hidden", False)
            except Exception: pass
            try: setattr(f, "_status_dodging", False)
            except Exception: pass
            try: setattr(f, "reactions_left", 1)
            except Exception: pass
            # Patch E conditions bag
            ensure_bag(f)

        self.events: List[Any] = []
        self.round = 1
        self.turn_idx = 0
        self._initiative: List[int] = []
        self.winner: Optional[int] = None
        self.controllers: Dict[int, BaseController] = {}

        self._roll_initiative()
        self._push({"type": "round_start", "round": self.round})

    # --- world API for controllers/UI ---
    def speed(self, f) -> int:
        base = int(getattr(f, "speed", 4))
        if has_condition(f, CONDITION_RESTRAINED): return 0
        return base
    def reach(self, f) -> int: return int(_weapon_profile(f)[3])
    def distance(self, a, b) -> int: return _chebyshev(self._pos(a), self._pos(b))
    def distance_xy(self, a, xy: Tuple[int,int]) -> int: return _chebyshev(self._pos(a), xy)
    def path_step(self, actor, target, *, avoid_oa: bool = True) -> Optional[Tuple[int, int]]:
        ax, ay = self._pos(actor); tx, ty = self._pos(target)
        return self.path_step_towards(actor, (tx, ty), avoid_oa=avoid_oa)
    def grant_advantage(self, f, stacks: int = 1):
        try: setattr(f, "_adv_once", max(0, int(getattr(f, "_adv_once", 0))) + int(stacks))
        except Exception: pass
    def grant_disadvantage(self, f, stacks: int = 1):
        try: setattr(f, "_dis_once", max(0, int(getattr(f, "_dis_once", 0))) + int(stacks))
        except Exception: pass

    # --- Saving throws API (Patch E) ---
    def saving_throw(self, actor, ability: str, dc: int, *, adv: int = 0) -> Dict[str, Any]:
        a = (ability or "CON").upper()
        adv_clamped = 1 if adv > 0 else -1 if adv < 0 else 0
        ctx = 0
        if a == "DEX" and has_condition(actor, CONDITION_RESTRAINED):
            ctx -= 1
        if a in ("STR", "DEX") and has_condition(actor, CONDITION_STUNNED):
            ctx -= 1
        n_raw, n_eff = _roll_d20(self.rng, adv_clamped + ctx)
        mod = _ability_mod(actor, a)
        total = n_eff + mod
        success = total >= int(dc)
        payload = {
            "type": "save",
            "target": _name(actor),
            "ability": a,
            "roll": n_raw,
            "effective": n_eff,
            "modifier": mod,
            "dc": int(dc),
            "success": bool(success),
            "advantage": adv_clamped + ctx > 0,
            "disadvantage": adv_clamped + ctx < 0,
        }
        self._push(payload)
        return payload

    # -------------- movement helpers --------------
    def _pos(self, f) -> Tuple[int, int]:
        return int(getattr(f, "x", getattr(f, "tx", 0))), int(getattr(f, "y", getattr(f, "ty", 0)))

    def _set_pos(self, f, x: int, y: int):
        try: setattr(f, "x", int(x)); setattr(f, "y", int(y))
        except Exception: pass
        try: setattr(f, "tx", int(x)); setattr(f, "ty", int(y))
        except Exception: pass

    def _occupied(self, x: int, y: int) -> bool:
        for g in self.fighters:
            if not _alive(g): continue
            gx, gy = self._pos(g)
            if gx == x and gy == y:
                return True
        return False

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
        if getattr(actor, "_turn_disengaged", False):
            return False
        before = self._enemies_in_reach_of_pos(actor, from_xy)
        after  = self._enemies_in_reach_of_pos(actor, to_xy)
        for e in before:
            if e not in after and int(getattr(e, "reactions_left", 1)) > 0 and _alive(e):
                return True
        return False

    def _threatened_in_melee(self, actor) -> bool:
        ax, ay = self._pos(actor)
        for e in self.fighters:
            if not _alive(e): continue
            if _team_id(e) == _team_id(actor): continue
            ex, ey = self._pos(e)
            if _chebyshev((ax, ay), (ex, ey)) <= 1:
                return True
        return False

    def _move_one_step_to(self, actor, nx: int, ny: int) -> bool:
        if has_condition(actor, CONDITION_RESTRAINED) or has_condition(actor, CONDITION_STUNNED):
            return False

        ax, ay = self._pos(actor)
        if not self._in_bounds(nx, ny): return False
        if self._occupied(nx, ny): return False

        provokers = []
        before = self._enemies_in_reach_of_pos(actor, (ax, ay))
        after  = self._enemies_in_reach_of_pos(actor, (nx, ny))
        for e in before:
            if e not in after and int(getattr(e, "reactions_left", 1)) > 0 and _alive(e):
                provokers.append(e)

        for e in list(provokers):
            self._opportunity_attack(e, actor)
            try: setattr(e, "reactions_left", max(0, int(getattr(e, "reactions_left", 1)) - 1))
            except Exception: pass
            if not _alive(actor):
                return False

        # Moving breaks Hide
        if getattr(actor, "_status_hidden", False):
            setattr(actor, "_status_hidden", False)

        self._set_pos(actor, nx, ny)
        self._push({"type": "move_step", "actor": _name(actor), "to": (nx, ny)})

        # Trigger enemy readied reactions on entering reach
        for e in self.fighters:
            if not _alive(e): continue
            if _team_id(e) == _team_id(actor): continue
            if getattr(e, "_ready", None) == "attack_on_enter_reach" and int(getattr(e, "reactions_left", 1)) > 0:
                ex, ey = self._pos(e)
                if _chebyshev((ex, ey), (nx, ny)) <= self.reach(e):
                    self._opportunity_attack(e, actor)
                    try: setattr(e, "reactions_left", max(0, int(getattr(e, "reactions_left", 1)) - 1))
                    except Exception: pass

        return True

    def _step_towards(self, actor, target) -> bool:
        ax, ay = self._pos(actor)
        tx, ty = self._pos(target)
        dx = tx - ax; dy = ty - ay
        if abs(dx) >= abs(dy):
            primary = [(1 if dx > 0 else -1, 0)] if dx != 0 else []
            secondary = [(0, 1 if dy > 0 else -1)] if dy != 0 else []
        else:
            primary = [(0, 1 if dy > 0 else -1)] if dy != 0 else []
            secondary = [(1 if dx > 0 else -1, 0)] if dx != 0 else []
        options = primary + secondary + [(1,0), (-1,0), (0,1), (0,-1)]

        avoid_oa = True
        try: avoid_oa = bool(getattr(actor, "avoid_oa", True))
        except Exception: pass

        best = None; best_d = 10**9
        for pass_i in (0, 1):
            for vx, vy in options:
                nx, ny = ax + vx, ay + vy
                if not self._in_bounds(nx, ny): continue
                if self._occupied(nx, ny): continue
                if avoid_oa and pass_i == 0 and self._would_provoke_oa(actor, (ax, ay), (nx, ny)):
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

    # ---------------- Patch F: Spells & Healing ----------------

    def _spell_attack_roll(self, caster, defender, *, ability: str, normal_range: int = 12, long_range: int = 24) -> Tuple[bool, bool, int, int, int]:
        """Returns (hit, crit, raw, eff, atk_mod); logs are handled by caller."""
        atk_mod = _ability_mod(caster, ability)
        dist = _chebyshev(self._pos(caster), self._pos(defender))
        if long_range <= 0 or dist > long_range:
            return False, False, 0, 0, atk_mod
        ctx_adv = 0
        if normal_range and dist > normal_range:
            ctx_adv -= 1
        if self._threatened_in_melee(caster):
            ctx_adv -= 1
        # Defender context: dodge, hidden (vs ranged), prone, restrained, stunned
        base_adv = self._compute_advantage_like_spell(caster, defender, is_ranged=True)
        n_raw, n_eff = _roll_d20(self.rng, base_adv + ctx_adv)
        crit = (n_eff == 20)
        ac = int(getattr(defender, "ac", getattr(defender, "AC", 10)))
        hit = (n_eff + atk_mod >= ac) or crit
        return hit, crit, n_raw, n_eff, atk_mod

    def _compute_advantage_like_spell(self, attacker, defender, *, is_ranged: bool) -> int:
        adv = 0
        # consume one-shots if caller granted
        ao = max(0, int(getattr(attacker, "_adv_once", 0))); do = max(0, int(getattr(attacker, "_dis_once", 0)))
        if ao > 0: adv += 1; setattr(attacker, "_adv_once", ao - 1)
        if do > 0: adv -= 1; setattr(attacker, "_dis_once", do - 1)
        # defender conditions
        if has_condition(defender, CONDITION_RESTRAINED): adv += 1
        if has_condition(defender, CONDITION_STUNNED): adv += 1
        if has_condition(defender, CONDITION_PRONE):
            if is_ranged: adv -= 1
            else:         adv += 1
        # attacker conditions
        if has_condition(attacker, CONDITION_RESTRAINED): adv -= 1
        # Patch D statuses
        if getattr(defender, "_status_dodging", False): adv -= 1
        if is_ranged and getattr(defender, "_status_hidden", False): adv -= 1
        return 1 if adv > 0 else -1 if adv < 0 else 0

    def _cast_heal(self, caster, target, dice: str = "1d8", ability: str = "WIS"):
        num, sides = _parse_dice(dice)
        heal_amt = _roll_dice(self.rng, num, sides) + max(0, _ability_mod(caster, ability))
        try:
            mhp = int(getattr(target, "max_hp", max(1, int(getattr(target, "hp", 1)))))
            hp0 = int(getattr(target, "hp", 0))
            target.hp = min(mhp, hp0 + int(heal_amt))
        except Exception:
            pass
        self._push({"type": "heal", "source": _name(caster), "target": _name(target), "amount": int(heal_amt)})

    def _cast_spell_attack(self, caster, target, *, dice: str = "1d8", ability: str = "INT", normal_range: int = 12, long_range: int = 24):
        if not (_alive(caster) and _alive(target)): return
        hit, crit, n_raw, n_eff, atk_mod = self._spell_attack_roll(caster, target, ability=ability, normal_range=normal_range, long_range=long_range)
        log = {
            "type": "spell_attack",
            "actor": _name(caster),
            "target": _name(target),
            "roll": n_raw, "effective": n_eff,
            "advantage": False, "disadvantage": False,  # already baked in; UI tags still infer from attack/disadv flags if you want
            "critical": bool(crit),
            "hit": bool(hit),
        }
        self._push(log)
        if hit:
            num, sides = _parse_dice(dice)
            dmg = _roll_dice(self.rng, (2 if crit else 1) * num, sides) + max(0, _ability_mod(caster, ability))
            self._apply_damage(caster, target, dmg)

    def _cast_spell_save(self, caster, target, *, save: str = "DEX", dc: int = 12, dice: Optional[str] = "1d8", ability: str = "INT", half_on_success: bool = False, apply_condition_on_fail: Optional[Tuple[str,int]] = None):
        if not (_alive(caster) and _alive(target)): return
        res = self.saving_throw(target, save, dc)
        dmg = 0
        if dice:
            num, sides = _parse_dice(dice)
            base = _roll_dice(self.rng, num, sides) + max(0, _ability_mod(caster, ability))
            if res["success"] and half_on_success:
                dmg = max(0, base // 2)
            elif not res["success"]:
                dmg = max(0, base)
        if dmg > 0:
            self._apply_damage(caster, target, dmg)
        if (not res["success"]) and apply_condition_on_fail:
            cname, dur = apply_condition_on_fail
            add_condition(target, cname, int(dur))
            self._push({"type": "condition_applied", "source": _name(caster), "target": _name(target), "condition": cname, "duration": int(dur)})

    def _cast_spell_line(self, caster, target_xy: Tuple[int,int], *, length: int = 8, dice: str = "1d6", ability: str = "INT", save: Optional[str] = None, dc: int = 12, half_on_success: bool = False):
        sx, sy = self._pos(caster)
        tx, ty = int(target_xy[0]), int(target_xy[1])
        cells = line_aoe_cells(sx, sy, tx, ty, length, self.cols, self.rows)
        self._push({"type": "spell_aoe", "shape": "line", "source": _name(caster), "cells": cells})
        # hit every creature (enemy or ally—up to your later rules; here we hit enemies only)
        for f in self.fighters:
            if not _alive(f): continue
            if _team_id(f) == _team_id(caster):  # friendly fire off for now
                continue
            fx, fy = self._pos(f)
            if (fx, fy) in cells:
                if save:
                    self._cast_spell_save(caster, f, save=save, dc=dc, dice=dice, ability=ability, half_on_success=half_on_success)
                else:
                    # treat as auto-hit spell attack (no roll)
                    num, sides = _parse_dice(dice)
                    dmg = _roll_dice(self.rng, num, sides) + max(0, _ability_mod(caster, ability))
                    self._apply_damage(caster, f, dmg)

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

        # Start-of-turn condition decrement & cleanup (Patch E)
        ended = decrement_all_for_turn(actor)
        for k in ended.keys():
            self._push({"type": "condition_ended", "target": _name(actor), "condition": k})

        # Reset per-turn flags
        setattr(actor, "_turn_dash_applied", False)
        setattr(actor, "_turn_disengaged", False)
        if getattr(actor, "_status_dodging", False):
            setattr(actor, "_status_dodging", False)  # Dodge lasts until your next turn starts
        if hasattr(actor, "_ready"):
            delattr(actor, "_ready")

        if not _alive(actor):
            self._advance_turn_pointer(); self._end_if_finished(); return

        self._push({"type": "turn_start", "actor": _name(actor), "round": self.round})

        # Stunned: skip your turn
        if has_condition(actor, CONDITION_STUNNED):
            self._advance_turn_pointer()
            self._end_if_finished()
            return

        # Try controller intents
        controller = self.controllers.get(_team_id(actor))
        intents: List[Dict[str, Any]] = []
        if controller:
            try:
                out = controller.decide(self, actor)
                if isinstance(out, list):
                    intents = [x for x in out if isinstance(x, dict)]
            except Exception:
                intents = []

        if intents:
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
                elif typ == "dash":
                    if not getattr(actor, "_turn_dash_applied", False):
                        steps_left += max(0, int(getattr(actor, "speed", 4)))
                        setattr(actor, "_turn_dash_applied", True)
                        acted = True
                        continue
                elif typ == "disengage":
                    setattr(actor, "_turn_disengaged", True)
                    acted = True
                    continue
                elif typ == "dodge":
                    setattr(actor, "_status_dodging", True)
                    acted = True
                    continue
                elif typ == "hide":
                    setattr(actor, "_status_hidden", True)
                    acted = True
                    continue
                elif typ == "ready":
                    setattr(actor, "_ready", "attack_on_enter_reach")
                    acted = True
                    continue
                elif typ == "heal":
                    target = it.get("target", actor)
                    dice = it.get("dice", "1d8")
                    ability = it.get("ability", "WIS")
                    if target is None: target = actor
                    self._cast_heal(actor, target, dice=dice, ability=ability)
                    acted = True
                    continue
                elif typ == "spell_attack":
                    target = it.get("target")
                    dice = it.get("dice", "1d8")
                    ability = it.get("ability", "INT")
                    nr = int(it.get("normal_range", 12))
                    lr = int(it.get("long_range", 24))
                    if target is not None and _alive(target):
                        self._cast_spell_attack(actor, target, dice=dice, ability=ability, normal_range=nr, long_range=lr)
                        attacked = True
                        acted = True
                        continue
                elif typ == "spell_save":
                    target = it.get("target")
                    save = str(it.get("save", "DEX"))
                    dc = int(it.get("dc", 12))
                    dice = it.get("dice", "1d8")
                    ability = it.get("ability", "INT")
                    half_on_success = bool(it.get("half_on_success", False))
                    apply_cond = it.get("apply_condition_on_fail")  # e.g., ("restrained", 1)
                    if target is not None and _alive(target):
                        self._cast_spell_save(actor, target, save=save, dc=dc, dice=dice, ability=ability, half_on_success=half_on_success, apply_condition_on_fail=apply_cond)
                        attacked = True
                        acted = True
                        continue
                elif typ == "spell_line":
                    target_xy = it.get("target_xy")
                    length = int(it.get("length", 8))
                    dice = it.get("dice", "1d6")
                    ability = it.get("ability", "INT")
                    save = it.get("save")  # or None
                    dc = int(it.get("dc", 12))
                    half_on_success = bool(it.get("half_on_success", False))
                    if isinstance(target_xy, (list, tuple)) and len(target_xy) == 2:
                        self._cast_spell_line(actor, (int(target_xy[0]), int(target_xy[1])), length=length, dice=dice, ability=ability, save=save, dc=dc, half_on_success=half_on_success)
                        attacked = True
                        acted = True
                        continue
                elif typ == "attack" and not attacked:
                    target = it.get("target")
                    if target is not None and _alive(target):
                        dist = _chebyshev(self._pos(actor), self._pos(target))
                        _, _, _, reach = _weapon_profile(actor)
                        is_ranged, _, lr, _ = _ranged_info(actor)
                        can_attack = (is_ranged and dist <= max(1, lr)) or (dist <= reach)
                        if can_attack:
                            self._attack(actor, target)
                            attacked = True
                            acted = True
                            break
                elif typ == "end":
                    break
            return acted or attacked

        # Baseline if no controller returns intents (unchanged melee/ranged baseline)
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
            try: setattr(f, "reactions_left", 1)
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

    # -------------- attack (martial) --------------
    def _compute_advantage(self, attacker, defender, *, is_ranged: bool) -> int:
        adv = 0
        if getattr(attacker, "advantage", False): adv += 1
        if getattr(attacker, "disadvantage", False): adv -= 1
        ao = max(0, int(getattr(attacker, "_adv_once", 0)))
        do = max(0, int(getattr(attacker, "_dis_once", 0)))
        if ao > 0:
            adv += 1; setattr(attacker, "_adv_once", ao - 1)
        if do > 0:
            adv -= 1; setattr(attacker, "_dis_once", do - 1)
        if has_condition(defender, CONDITION_RESTRAINED): adv += 1
        if has_condition(defender, CONDITION_STUNNED): adv += 1
        if has_condition(defender, CONDITION_PRONE):
            if is_ranged: adv -= 1
            else:         adv += 1
        if has_condition(attacker, CONDITION_RESTRAINED): adv -= 1
        if getattr(defender, "_status_dodging", False): adv -= 1
        if is_ranged and getattr(defender, "_status_hidden", False): adv -= 1
        return 1 if adv > 0 else -1 if adv < 0 else 0

    def _attack(self, attacker, defender, *, is_reaction: bool = False):
        if not (_alive(attacker) and _alive(defender)):
            return
        if has_condition(attacker, CONDITION_STUNNED):
            return  # stunned cannot attack

        if getattr(attacker, "_status_hidden", False):
            setattr(attacker, "_status_hidden", False)

        num, sides, ability_melee, reach = _weapon_profile(attacker)
        is_ranged, nr, lr, ability_ranged = _ranged_info(attacker)
        ability = ability_ranged if is_ranged else ability_melee
        atk_mod = _ability_mod(attacker, ability)

        dist = _chebyshev(self._pos(attacker), self._pos(defender))
        if is_ranged:
            if lr <= 0 or dist > lr:
                self._push({
                    "type": "attack", "actor": _name(attacker), "target": _name(defender),
                    "hit": False, "reason": "out_of_range", "ranged": True,
                    "opportunity": bool(is_reaction),
                })
                return

        ctx_adv = 0
        if is_ranged:
            if nr > 0 and dist > nr:
                ctx_adv -= 1
            if self._threatened_in_melee(attacker):
                ctx_adv -= 1
            if has_condition(attacker, CONDITION_PRONE):
                ctx_adv -= 1

        base_adv = self._compute_advantage(attacker, defender, is_ranged=is_ranged)
        n_raw, n_eff = _roll_d20(self.rng, base_adv + ctx_adv)
        crit = (n_eff == 20)
        ac = int(getattr(defender, "ac", getattr(defender, "AC", 10)))
        hit = (n_eff + atk_mod >= ac) or crit

        log = {
            "type": "attack",
            "actor": _name(attacker),
            "target": _name(defender),
            "roll": n_raw,
            "effective": n_eff,
            "advantage": (base_adv + ctx_adv > 0),
            "disadvantage": (base_adv + ctx_adv < 0),
            "critical": bool(crit),
            "hit": bool(hit),
            "opportunity": bool(is_reaction),
            "ranged": bool(is_ranged),
        }
        self._push(log)

        if hit:
            dice = 2 if crit else 1
            dmg = _roll_dice(self.rng, dice * num, sides) + max(0, atk_mod)
            self._apply_damage(attacker, defender, dmg)

    def _opportunity_attack(self, attacker, mover):
        self._attack(attacker, mover, is_reaction=True)

    def _apply_damage(self, attacker, defender, dmg: int):
        try:
            defender.hp = int(defender.hp) - int(dmg)
        except Exception:
            pass
        self._push({"type": "damage", "actor": _name(attacker), "target": _name(defender), "amount": int(dmg)})

        # Concentration check hook (Patch E)
        if getattr(defender, "concentration", False):
            dc = max(10, int(dmg) // 2)
            res = self.saving_throw(defender, "CON", dc)
            if not res["success"]:
                try: setattr(defender, "concentration", False)
                except Exception: pass
                self._push({"type": "concentration_broken", "target": _name(defender)})

        if getattr(defender, "hp", 0) <= 0 and _alive(defender):
            try: setattr(defender, "alive", False)
            except Exception: pass
            self._push({"type": "down", "name": _name(defender)})

    # -------------- Baseline AI --------------
    def _choose_target(self, actor):
        best = None; best_score = (10**9, 10**9)
        for e in self.fighters:
            if not _alive(e): continue
            if _team_id(e) == _team_id(actor): continue
            d = _chebyshev(self._pos(actor), self._pos(e))
            score = (d, -_as_int(getattr(e, "ovr", getattr(e, "OVR", 50)), 50))
            if score < best_score:
                best_score = score; best = e
        return best

    def _baseline_turn(self, actor):
        # Minimal baseline remains martial/ranged; spells are controller-driven.
        enemy = self._choose_target(actor)
        if enemy is None:
            return
        dist = _chebyshev(self._pos(actor), self._pos(enemy))
        _, _, _, reach = _weapon_profile(actor)
        is_ranged, nr, lr, _ = _ranged_info(actor)

        if is_ranged:
            if dist <= max(1, lr):
                if dist <= 1:
                    step = self.path_step_towards(actor, (self.cols - 1 if _team_id(actor) == 0 else 0, self._pos(actor)[1]), avoid_oa=True)
                    if step: self._move_one_step_to(actor, *step)
                self._attack(actor, enemy)
            else:
                moves = max(1, self.speed(actor) * 2 if dist > lr else self.speed(actor))
                for _ in range(moves):
                    step = self.path_step(actor, enemy, avoid_oa=True)
                    if not step: break
                    self._move_one_step_to(actor, *step)
                if _chebyshev(self._pos(actor), self._pos(enemy)) <= max(1, lr):
                    self._attack(actor, enemy)
        else:
            for _ in range(self.speed(actor)):
                if _chebyshev(self._pos(actor), self._pos(enemy)) <= reach: break
                step = self.path_step(actor, enemy, avoid_oa=True)
                if not step: break
                self._move_one_step_to(actor, *step)
            if _chebyshev(self._pos(actor), self._pos(enemy)) <= reach:
                self._attack(actor, enemy)

    # -------------- end-of-battle --------------
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
