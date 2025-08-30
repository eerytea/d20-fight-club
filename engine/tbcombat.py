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

# for proficiency lookups (simple inline to avoid deep coupling)
def _prof_for_level(level: int) -> int:
    L = max(1, int(level))
    return min(6, 2 + (L - 1) // 4)

__all__ = ["TBCombat", "Team"]


@dataclass
class Team:
    tid: int
    name: str
    color: Tuple[int, int, int]


# ---------- helpers ----------
def _name(f) -> str:
    return getattr(f, "name", f"P{getattr(f, 'pid', getattr(f, 'id', '?'))}")

def _alive(f) -> bool:
    try:
        return bool(getattr(f, "alive", True)) and int(getattr(f, "hp", 0)) > 0
    except Exception:
        return False

def _ability_mod(f, ability: str) -> int:
    k = ability.upper()
    val = getattr(f, k, getattr(f, k.lower(), 10))
    try:
        return (int(val) - 10) // 2
    except Exception:
        return 0

def _parse_dice(s: str) -> Tuple[int, int]:
    s = str(s or "1d4").lower().strip()
    if "d" not in s:
        try: return (1, int(s))
        except Exception: return (1, 4)
    a, b = s.split("d", 1)
    try:
        n = int(a) if a else 1
        m = int(b)
        return (max(1, n), max(1, m))
    except Exception:
        return (1, 4)

def _roll_dice(rng: random.Random, n: int, sides: int) -> int:
    n = max(1, int(n)); sides = max(1, int(sides))
    return sum(rng.randint(1, sides) for _ in range(n))

def _roll_d20(rng: random.Random, adv: int = 0) -> Tuple[Any, int]:
    a = rng.randint(1, 20)
    if adv > 0:
        b = rng.randint(1, 20)
        return ((a, b), max(a, b))
    if adv < 0:
        b = rng.randint(1, 20)
        return ((a, b), min(a, b))
    return (a, a)

def _dist_xy(ax: int, ay: int, bx: int, by: int) -> int:
    return max(abs(ax - bx), abs(ay - by))

# ---------- engine ----------
class TBCombat:
    """
    Includes:
      - Patch D–F features from earlier (OA, Dodge/Disengage/Dash/Ready/Hide, ranged rules, conditions, spells scaffold).
      - Barbarian features (rage, extra attacks, crit dice, initiative adv, unarmored speed bonus).
      - Global Proficiency Bonus added to to-hit and damage (weapon & spell), and to spell save DC.
      - Bard features:
         * Inspiration (action): give one-shot advantage token to an ally (once/battle; unlimited at L20).
         * Level-6 aura: allies within 6 cells get advantage on saves vs 'charm' or 'fear'.
    """

    def __init__(self, teamA: Team, teamB: Team, fighters: List[Any], cols: int, rows: int, *, seed: Optional[int] = None):
        self.teams = {0: teamA, 1: teamB}
        self.fighters: List[Any] = list(fighters)
        self.cols, self.rows = int(cols), int(rows)
        self.events: List[Dict[str, Any]] = []
        self.rng = random.Random(seed)
        self.round: int = 1
        self.winner: Optional[int] = None
        self.controllers: Dict[int, Any] = {0: None, 1: None}

        # Ensure minimum fields
        for i, f in enumerate(self.fighters):
            if not hasattr(f, "pid"): setattr(f, "pid", i)
            if not hasattr(f, "team_id"): setattr(f, "team_id", getattr(f, "tid", 0))
            if not hasattr(f, "tx"): setattr(f, "tx", getattr(f, "x", 0))
            if not hasattr(f, "ty"): setattr(f, "ty", getattr(f, "y", 0))
            if not hasattr(f, "alive"): setattr(f, "alive", True)
            if not hasattr(f, "hp"): setattr(f, "hp", 10)
            if not hasattr(f, "max_hp"): setattr(f, "max_hp", getattr(f, "hp", 10))
            if not hasattr(f, "ac"): setattr(f, "ac", 12)
            if not hasattr(f, "speed"): setattr(f, "speed", 4)
            if not hasattr(f, "reactions_left"): setattr(f, "reactions_left", 1)
            # inspiration tokens & usage counter (battle-scoped)
            setattr(f, "inspiration_tokens", 0)
            setattr(f, "inspiration_used", 0)

        # Initiative (Barbarian L7+ advantage)
        rolls: List[Tuple[int, int]] = []
        for i, f in enumerate(self.fighters):
            dexmod = _ability_mod(f, "DEX")
            adv = 1 if (str(getattr(f, "class", "")).capitalize() == "Barbarian" and int(getattr(f, "level", 1)) >= 7) else 0
            _, eff = _roll_d20(self.rng, adv)
            rolls.append((eff + dexmod, i))
        rolls.sort(reverse=True)
        self._initiative = [i for _, i in rolls]
        self.turn_idx = 0

        self._push({"type": "round_start", "round": self.round})

    # ---------- utilities ----------
    def _push(self, ev: Dict[str, Any]): self.events.append(ev)
    def _team_of(self, f) -> int: return int(getattr(f, "team_id", getattr(f, "tid", 0)))
    def _enemies_of(self, f): tid = self._team_of(f); return [x for x in self.fighters if self._team_of(x) != tid]
    def _friendlies_of(self, f): tid = self._team_of(f); return [x for x in self.fighters if self._team_of(x) == tid and x is not f]
    def distance(self, a, b) -> int: return _dist_xy(getattr(a, "tx", 0), getattr(a, "ty", 0), getattr(b, "tx", 0), getattr(b, "ty", 0))
    def distance_coords(self, ax, ay, bx, by) -> int: return _dist_xy(ax, ay, bx, by)

    def reach(self, a) -> int:
        _, _, _, r = self._weapon_profile(a)
        return int(r)

    def speed_of(self, a) -> int:
        return int(getattr(a, "speed", 4))

    def threatened_in_melee(self, a) -> bool:
        ax, ay = getattr(a, "tx", 0), getattr(a, "ty", 0)
        for e in self._enemies_of(a):
            if not _alive(e): continue
            _, _, _, r = self._weapon_profile(e)
            if self.distance_coords(ax, ay, getattr(e, "tx", 0), getattr(e, "ty", 0)) <= r:
                return True
        return False

    def path_step_towards(self, a, to_xy: Tuple[int, int]) -> Tuple[int, int]:
        ax, ay = getattr(a, "tx", 0), getattr(a, "ty", 0)
        tx, ty = map(int, to_xy)
        dx = 0 if ax == tx else (1 if tx > ax else -1)
        dy = 0 if ay == ty else (1 if ty > ay else -1)
        if dx != 0 and dy != 0:
            if abs(tx - ax) >= abs(ty - ay): dy = 0
            else: dx = 0
        return (ax + dx, ay + dy)

    # ---------- profiles & rolls ----------
    def _weapon_profile(self, f) -> Tuple[int, int, str, int]:
        w = getattr(f, "weapon", None)
        if w is None:
            unarmed = getattr(f, "unarmed_dice", None)
            if isinstance(unarmed, str): num, sides = _parse_dice(unarmed)
            else: num, sides = (1, 4)
            return (num, sides, "STR", 1)
        if isinstance(w, dict):
            num, sides = _parse_dice(w.get("dice", w.get("formula", "1d4")))
            reach = int(w.get("reach", 1))
            ability = str(w.get("ability", w.get("mod", "STR"))).upper()
            if bool(w.get("finesse", False)): ability = "FINESSE"
            if ability not in ("STR", "DEX", "FINESSE"): ability = "STR"
            return (num, sides, ability, max(1, reach))
        if isinstance(w, str):
            wl = w.lower()
            reach = 1
            finesse = ("finesse" in wl)
            ability = "FINESSE" if finesse else ("DEX" if any(k in wl for k in ("bow", "javelin", "ranged", "crossbow", "sling", "dart")) else "STR")
            num, sides = _parse_dice(wl.split()[0] if wl.split() else "1d4")
            return (num, sides, ability, max(1, reach))
        return (1, 4, "STR", 1)

    def _ranged_profile(self, f) -> Optional[Tuple[int, int, str, int, Tuple[int, int]]]:
        w = getattr(f, "weapon", None)
        if isinstance(w, dict) and bool(w.get("ranged", False)):
            num, sides = _parse_dice(w.get("dice", "1d6"))
            ability = str(w.get("ability", "DEX")).upper()
            normal, longr = w.get("range", (8, 16))
            return (num, sides, ability, 1, (int(normal), int(longr)))
        return None

    def _attack_roll(self, attacker, defender, *, advantage: int = 0, ranged: bool = False, long_range: bool = False
                     ) -> Tuple[bool, bool, Any, int, int]:
        ctx = advantage
        # Inspiration token (consume for the roller)
        consume_token = False
        try:
            if int(getattr(attacker, "inspiration_tokens", 0)) > 0:
                ctx += 1
                consume_token = True
        except Exception:
            pass
        # Defender conditions
        if getattr(defender, "_status_dodging", False): ctx -= 1
        if has_condition(defender, CONDITION_RESTRAINED): ctx += 1
        if has_condition(defender, CONDITION_PRONE):
            ctx += (1 if not ranged else 0)
            ctx -= (1 if ranged else 0)
        raw, eff = _roll_d20(self.rng, max(-1, min(1, ctx)))
        if consume_token:
            try: setattr(attacker, "inspiration_tokens", int(getattr(attacker, "inspiration_tokens", 1)) - 1)
            except Exception: pass
        crit = (eff == 20)
        num, sides, ability, _ = self._weapon_profile(attacker)
        if ability == "FINESSE":
            mod = max(_ability_mod(attacker, "STR"), _ability_mod(attacker, "DEX"))
        else:
            mod = _ability_mod(attacker, "DEX" if ranged else ability)

        # Proficiency to hit
        prof = _prof_for_level(getattr(attacker, "level", getattr(attacker, "lvl", 1)))
        ac = int(getattr(defender, "ac", 12))
        hit = (eff + mod + prof >= ac) or crit
        return (hit, crit, raw, eff, mod)

    def _spell_attack_roll(self, caster, target, *, ability="CHA", normal_range=12, long_range=24
                           ) -> Tuple[bool, bool, Any, int, int]:
        adv = 0
        # Inspiration token for the roller
        consume_token = False
        try:
            if int(getattr(caster, "inspiration_tokens", 0)) > 0:
                adv += 1
                consume_token = True
        except Exception:
            pass
        d = self.distance(caster, target)
        if d > int(long_range): return (False, False, 1, 1, _ability_mod(caster, ability))
        if d > int(normal_range): adv -= 1
        if self.threatened_in_melee(caster): adv -= 1
        raw, eff = _roll_d20(self.rng, adv)
        if consume_token:
            try: setattr(caster, "inspiration_tokens", int(getattr(caster, "inspiration_tokens", 1)) - 1)
            except Exception: pass
        crit = (eff == 20)
        mod = _ability_mod(caster, ability)
        prof = _prof_for_level(getattr(caster, "level", getattr(caster, "lvl", 1)))
        ac = int(getattr(target, "ac", 12))
        hit = (eff + mod + prof >= ac) or crit
        return (hit, crit, raw, eff, mod)

    # ---------- main turn loop ----------
    def take_turn(self):
        if self.winner is not None:
            return

        if self.turn_idx == 0 and (len(self.events) == 0 or self.events[-1].get("type") != "round_start"):
            self.round += 1
            for f in self.fighters:
                setattr(f, "reactions_left", 1)
            self._push({"type": "round_start", "round": self.round})

        act_i = self._initiative[self.turn_idx % len(self._initiative)]
        actor = self.fighters[act_i]
        if not _alive(actor):
            self._advance_pointer(actor)
            return

        self._push({"type": "turn_start", "actor": _name(actor)})
        setattr(actor, "_status_disengage", False)
        if getattr(actor, "_status_dodging", False): setattr(actor, "_status_dodging", False)
        setattr(actor, "_dash_pool", 0)
        setattr(actor, "_dealt_damage_this_turn", False)

        if has_condition(actor, CONDITION_STUNNED):
            decrement_all_for_turn(actor)
            self._advance_pointer(actor)
            return

        intents: List[Dict[str, Any]] = []
        ctrl = self.controllers.get(self._team_of(actor))
        if ctrl is not None and hasattr(ctrl, "decide"):
            try: intents = ctrl.decide(self, actor) or []
            except Exception: intents = []
        if not intents:
            intents = self._baseline_intents(actor)

        # steps (+2 if Barbarian L5+ and unarmored)
        steps_left = int(getattr(actor, "speed", 4))
        try:
            if int(getattr(actor, "level", 1)) >= 5 and int(getattr(actor, "barb_speed_bonus_if_unarmored", 0)) > 0:
                if int(getattr(actor, "armor_bonus", 0)) == 0:
                    steps_left += int(getattr(actor, "barb_speed_bonus_if_unarmored", 0))
        except Exception:
            pass

        for intent in intents:
            t = intent.get("type")

            if t == "disengage":
                setattr(actor, "_status_disengage", True)

            elif t == "dodge":
                setattr(actor, "_status_dodging", True)

            elif t == "dash":
                setattr(actor, "_dash_pool", getattr(actor, "_dash_pool", 0) + int(getattr(actor, "speed", 4)))

            elif t == "hide":
                setattr(actor, "hidden", True)

            elif t == "ready":
                setattr(actor, "_ready_reaction", True)

            elif t == "rage":
                setattr(actor, "rage_active", True)
                setattr(actor, "resist_all", True)
                setattr(actor, "rage_bonus_per_level", 1)
                self._push({"type": "status", "actor": _name(actor), "status": "rage_on"})

            elif t == "inspire":
                # Bard inspiration
                target = intent.get("target")
                if target is not None and _alive(target):
                    uses = int(getattr(actor, "inspiration_used", 0))
                    per_battle = int(getattr(actor, "bard_inspiration_uses_per_battle", 0))
                    if uses < per_battle:
                        setattr(target, "inspiration_tokens", int(getattr(target, "inspiration_tokens", 0)) + 1)
                        setattr(actor, "inspiration_used", uses + 1)
                        self._push({"type": "inspire", "actor": _name(actor), "target": _name(target)})
                    else:
                        self._push({"type": "inspire", "actor": _name(actor), "target": _name(target), "failed": True, "reason": "no_uses"})

            elif t == "move":
                to = tuple(intent.get("to", (getattr(actor, "tx", 0), getattr(actor, "ty", 0))))
                steps_left = self._do_move(actor, to, steps_left)

            elif t == "attack":
                swings = 1 + int(getattr(actor, "barb_extra_attacks", 0))
                target = intent.get("target") or self._pick_nearest_enemy(actor)
                for s in range(swings):
                    if target is None or not _alive(actor) or not _alive(target): break
                    self._do_attack(actor, target, opportunity=False)

            elif t == "heal":
                tgt = intent.get("target", actor)
                dice = str(intent.get("dice", "1d4"))
                ability = str(intent.get("ability", "WIS")).upper()
                self._do_heal(actor, tgt, dice, ability)

            elif t == "spell_attack":
                tgt = intent.get("target")
                if tgt is None: continue
                dice = str(intent.get("dice", "1d8"))
                ability = str(intent.get("ability", "CHA")).upper()
                nr = int(intent.get("normal_range", 12))
                lr = int(intent.get("long_range", 24))
                dtype = intent.get("damage_type")
                self._cast_spell_attack(actor, tgt, dice=dice, ability=ability, normal_range=nr, long_range=lr, damage_type=dtype)

            elif t == "spell_save":
                tgt = intent.get("target")
                if tgt is None: continue
                save = str(intent.get("save", "DEX")).upper()
                # If dc not provided, compute using caster's spell ability (default CHA)
                dc = intent.get("dc")
                ability = str(intent.get("ability", "CHA")).upper()
                if dc is None:
                    prof = _prof_for_level(getattr(actor, "level", getattr(actor, "lvl", 1)))
                    dc = 8 + _ability_mod(actor, ability) + prof
                dice = intent.get("dice", "1d8")
                half = bool(intent.get("half_on_success", False))
                tags = intent.get("tags")
                dtype = intent.get("damage_type")
                cond = tuple(intent["apply_condition_on_fail"]) if "apply_condition_on_fail" in intent else None
                self._cast_spell_save(actor, tgt, save=save, dc=int(dc), dice=dice, ability=ability,
                                      half_on_success=half, tags=tags, damage_type=dtype, apply_condition_on_fail=cond)

            if self.winner is not None:
                break

        decrement_all_for_turn(actor)

        # Rage auto-end if no damage dealt this turn (L1–14)
        try:
            if bool(getattr(actor, "rage_active", False)) and not bool(getattr(actor, "barb_rage_capstone", False)):
                if not bool(getattr(actor, "_dealt_damage_this_turn", False)):
                    setattr(actor, "rage_active", False)
                    setattr(actor, "resist_all", False)
                    setattr(actor, "rage_bonus_per_level", 0)
                    self._push({"type": "status", "actor": _name(actor), "status": "rage_off"})
        except Exception:
            pass

        self._advance_pointer(actor)

    def _advance_pointer(self, actor):
        if self._team_defeated(0) and self._team_defeated(1):
            self.winner = None; self._push({"type": "end", "winner": None})
        elif self._team_defeated(1):
            self.winner = 0; self._push({"type": "end", "winner": 0})
        elif self._team_defeated(0):
            self.winner = 1; self._push({"type": "end", "winner": 1})

        self.turn_idx = (self.turn_idx + 1) % len(self._initiative)
        if self.turn_idx == 0 and self.winner is None:
            for f in self.fighters:
                setattr(f, "reactions_left", 1)
            self.round += 1
            self._push({"type": "round_start", "round": self.round})

    def _team_defeated(self, tid: int) -> bool:
        return all((not _alive(f)) or self._team_of(f) != tid for f in self.fighters)

    def _baseline_intents(self, actor) -> List[Dict[str, Any]]:
        t = self._pick_nearest_enemy(actor)
        if not t: return []
        if self.distance(actor, t) <= self.reach(actor):
            return [{"type": "attack", "target": t}]
        return [{"type": "move", "to": (getattr(t, "tx", 0), getattr(t, "ty", 0))}]

    def _pick_nearest_enemy(self, actor):
        enemies = [e for e in self._enemies_of(actor) if _alive(e)]
        if not enemies: return None
        enemies.sort(key=lambda e: self.distance(actor, e))
        return enemies[0]

    # ---------- movement & OA ----------
    def _do_move(self, actor, to_xy: Tuple[int, int], steps_left: int) -> int:
        ax, ay = getattr(actor, "tx", 0), getattr(actor, "ty", 0)
        goal = tuple(map(int, to_xy))
        pool = steps_left + int(getattr(actor, "_dash_pool", 0))

        while pool > 0 and (ax, ay) != goal:
            nx, ny = self.path_step_towards(actor, goal)
            if not getattr(actor, "_status_disengage", False):
                for e in self._enemies_of(actor):
                    if not _alive(e): continue
                    reach = self.reach(e)
                    d_before = self.distance_coords(ax, ay, getattr(e, "tx", 0), getattr(e, "ty", 0))
                    d_after = self.distance_coords(nx, ny, getattr(e, "tx", 0), getattr(e, "ty", 0))
                    if d_before <= reach and d_after > reach and int(getattr(e, "reactions_left", 0)) > 0:
                        self._do_attack(e, actor, opportunity=True)
                        setattr(e, "reactions_left", int(getattr(e, "reactions_left", 0)) - 1)
                        if self.winner is not None: return 0
            setattr(actor, "tx", nx); setattr(actor, "ty", ny)
            self._push({"type": "move_step", "actor": _name(actor), "to": (nx, ny)})
            ax, ay = nx, ny
            pool -= 1

            for e in self._enemies_of(actor):
                if not _alive(e): continue
                if not getattr(e, "_ready_reaction", False): continue
                reach = self.reach(e)
                if self.distance_coords(ax, ay, getattr(e, "tx", 0), getattr(e, "ty", 0)) <= reach and int(getattr(e, "reactions_left", 0)) > 0:
                    self._do_attack(e, actor, opportunity=True)
                    setattr(e, "reactions_left", int(getattr(e, "reactions_left", 0)) - 1)
                    setattr(e, "_ready_reaction", False)
                    if self.winner is not None: return 0

        used = (steps_left + int(getattr(actor, "_dash_pool", 0))) - pool
        dash = int(getattr(actor, "_dash_pool", 0))
        if used <= dash:
            setattr(actor, "_dash_pool", dash - used)
            return steps_left
        else:
            used -= dash
            setattr(actor, "_dash_pool", 0)
            return max(0, steps_left - used)

    # ---------- attacks & spells ----------
    def _do_attack(self, attacker, defender, *, opportunity: bool):
        if not (_alive(attacker) and _alive(defender)): return

        ranged = False; long_dis = False
        rp = self._ranged_profile(attacker)
        num, sides, ability, reach = self._weapon_profile(attacker)
        if rp is not None:
            ranged = True
            normal, longr = rp[-1]
            d = self.distance(attacker, defender)
            if d > longr:
                self._push({"type": "attack", "actor": _name(attacker), "target": _name(defender), "hit": False,
                            "reason": "out_of_range", "ranged": True, "opportunity": opportunity,
                            "advantage": False, "disadvantage": False})
                return
            long_dis = d > normal

        adv = 0
        if ranged:
            if long_dis: adv -= 1
            if self.threatened_in_melee(attacker): adv -= 1

        hit, crit, raw, eff, mod = self._attack_roll(attacker, defender, advantage=adv, ranged=ranged, long_range=long_dis)
        self._push({"type": "attack", "actor": _name(attacker), "target": _name(defender), "ranged": ranged,
                    "opportunity": bool(opportunity), "critical": bool(crit), "hit": bool(hit),
                    "advantage": isinstance(raw, tuple) and eff == max(raw) and adv > 0,
                    "disadvantage": isinstance(raw, tuple) and eff == min(raw) and adv < 0})

        if hit:
            if ranged and rp is not None:
                num, sides, ability, _, _ = rp
            base = _roll_dice(self.rng, num * (2 if crit else 1), sides)

            # Barbarian brutal crit extra dice (weapon attacks only)
            if crit and int(getattr(attacker, "barb_crit_extra_dice", 0)) > 0:
                base += _roll_dice(self.rng, int(getattr(attacker, "barb_crit_extra_dice", 0)) * num, sides)

            # Ability mod
            if ability == "FINESSE":
                base += max(_ability_mod(attacker, "STR"), _ability_mod(attacker, "DEX"))
            else:
                base += _ability_mod(attacker, ("DEX" if ranged else ability))

            # Proficiency adds to damage (house rule)
            base += _prof_for_level(getattr(attacker, "level", getattr(attacker, "lvl", 1)))

            self._apply_damage(attacker, defender, base)

    def _do_heal(self, healer, target, dice: str, ability: str):
        num, sides = _parse_dice(dice)
        amt = _roll_dice(self.rng, num, sides) + max(0, _ability_mod(healer, ability))
        try:
            target.hp = min(int(getattr(target, "max_hp", getattr(target, "hp", 0))), int(getattr(target, "hp", 0)) + max(0, amt))
        except Exception:
            pass
        self._push({"type": "heal", "source": _name(healer), "target": _name(target), "amount": max(0, amt)})

    def _cast_spell_attack(self, caster, target, *, dice: str = "1d8", ability: str = "CHA",
                           normal_range: int = 12, long_range: int = 24, damage_type: Optional[str] = None):
        if not (_alive(caster) and _alive(target)): return
        hit, crit, raw, eff, mod = self._spell_attack_roll(caster, target, ability=ability, normal_range=normal_range, long_range=long_range)
        self._push({"type": "spell_attack", "actor": _name(caster), "target": _name(target), "roll": raw, "effective": eff,
                    "critical": bool(crit), "hit": bool(hit)})
        if self.distance(caster, target) > int(long_range): return
        if hit:
            num, sides = _parse_dice(dice)
            dmg = _roll_dice(self.rng, (2 if crit else 1) * num, sides) + max(0, _ability_mod(caster, ability))
            # Proficiency adds to spell damage (house rule)
            dmg += _prof_for_level(getattr(caster, "level", getattr(caster, "lvl", 1)))
            self._apply_damage(caster, target, dmg, damage_type=damage_type)

    def _cast_spell_save(self, caster, target, *, save: str = "DEX", dc: int = 12, dice: Optional[str] = "1d8",
                         ability: str = "CHA", half_on_success: bool = False,
                         apply_condition_on_fail: Optional[Tuple[str, int]] = None,
                         tags: Optional[List[str]] = None, damage_type: Optional[str] = None):
        if not (_alive(caster) and _alive(target)): return
        tags = [t.lower() for t in (tags or [])]
        res = self.saving_throw(target, save, dc, tags=tags)
        dmg = 0
        if dice:
            num, sides = _parse_dice(dice)
            base = _roll_dice(self.rng, num, sides) + max(0, _ability_mod(caster, ability))
            # Proficiency adds to spell damage (house rule)
            base += _prof_for_level(getattr(caster, "level", getattr(caster, "lvl", 1)))
            if res["success"] and half_on_success: dmg = max(0, base // 2)
            elif not res["success"]: dmg = max(0, base)
        if dmg > 0:
            self._apply_damage(caster, target, dmg, damage_type=damage_type)
        if (not res["success"]) and apply_condition_on_fail:
            cname, dur = apply_condition_on_fail
            if cname.lower() == "sleep" and getattr(target, "sleep_immune", False):
                self._push({"type": "condition_ignored", "target": _name(target), "condition": cname, "reason": "immune"})
            else:
                add_condition(target, cname, int(dur))
                self._push({"type": "condition_applied", "source": _name(caster), "target": _name(target),
                            "condition": cname, "duration": int(dur)})

    def _do_spell_line(self, caster, target_xy: Tuple[int, int], length: int, dice: str, ability: str):
        sx, sy = getattr(caster, "tx", 0), getattr(caster, "ty", 0)
        ex, ey = target_xy
        cells = line_aoe_cells((sx, sy), (ex, ey), length)
        self._push({"type": "spell_aoe", "source": _name(caster), "cells": cells})
        num, sides = _parse_dice(dice)
        dmg = _roll_dice(self.rng, num, sides) + max(0, _ability_mod(caster, ability))
        dmg += _prof_for_level(getattr(caster, "level", getattr(caster, "lvl", 1)))
        for f in self._enemies_of(caster):
            if not _alive(f): continue
            if (getattr(f, "tx", 0), getattr(f, "ty", 0)) in cells:
                self._apply_damage(caster, f, dmg)

    # ---------- saves & damage ----------
    def saving_throw(self, actor, ability: str, dc: int, *, adv: int = 0, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        a = (ability or "CON").upper()
        tags = [t.lower() for t in (tags or [])]
        ctx = (1 if adv > 0 else -1 if adv < 0 else 0)

        if a == "DEX" and has_condition(actor, CONDITION_RESTRAINED): ctx -= 1
        if a in ("STR", "DEX") and has_condition(actor, CONDITION_STUNNED): ctx -= 1
        # Race perks
        if getattr(actor, "adv_vs_poison", False) and ("poison" in tags): ctx += 1
        if getattr(actor, "adv_vs_charm", False) and ("charm" in tags): ctx += 1
        if getattr(actor, "adv_vs_paralysis", False) and ("paralysis" in tags): ctx += 1
        if getattr(actor, "adv_vs_magic_mental", False) and ("magic" in tags) and a in ("INT", "WIS", "CHA"): ctx += 1
        # Rage proxy: STR saves get adv while raging
        if bool(getattr(actor, "rage_active", False)) and a == "STR": ctx += 1
        # Bard L6 aura: allies within 6 get adv vs charm/fear saves
        if ("charm" in tags) or ("fear" in tags):
            for ally in self._friendlies_of(actor):
                if not _alive(ally): continue
                if not bool(getattr(ally, "bard_aura_charm_fear", False)): continue
                if self.distance(actor, ally) <= 6:
                    ctx += 1
                    break
        # Inspiration token (consume for the roller)
        consume_token = False
        try:
            if int(getattr(actor, "inspiration_tokens", 0)) > 0:
                ctx += 1
                consume_token = True
        except Exception:
            pass

        raw, eff = _roll_d20(self.rng, max(-1, min(1, ctx)))
        if consume_token:
            try: setattr(actor, "inspiration_tokens", int(getattr(actor, "inspiration_tokens", 1)) - 1)
            except Exception: pass

        mod = _ability_mod(actor, a)
        total = eff + mod
        success = total >= int(dc)
        self._push({"type": "save", "target": _name(actor), "ability": a, "roll": raw, "effective": eff,
                    "modifier": mod, "dc": int(dc), "success": bool(success),
                    "advantage": isinstance(raw, tuple) and eff == max(raw) and ctx > 0,
                    "disadvantage": isinstance(raw, tuple) and eff == min(raw) and ctx < 0,
                    "tags": tags})
        return {"success": success}

    def _apply_damage(self, attacker, defender, dmg: int, *, damage_type: Optional[str] = None):
        # Outgoing: racial per-level
        try:
            per_lvl = int(getattr(attacker, "dmg_bonus_per_level", 0))
            lvl = int(getattr(attacker, "level", getattr(attacker, "lvl", 1)))
            if per_lvl > 0 and lvl > 0:
                dmg = int(dmg) + per_lvl * lvl
        except Exception:
            pass
        # Outgoing: Barbarian rage
        try:
            if bool(getattr(attacker, "rage_active", False)) and int(getattr(attacker, "rage_bonus_per_level", 0)) > 0:
                lvl = int(getattr(attacker, "level", getattr(attacker, "lvl", 1)))
                dmg = int(dmg) + lvl * int(getattr(attacker, "rage_bonus_per_level", 0))
        except Exception:
            pass

        # Incoming: universal resist (rage) or poison resist
        try:
            if bool(getattr(defender, "resist_all", False)):
                dmg = int(dmg) // 2
            elif damage_type and damage_type.lower() == "poison" and getattr(defender, "poison_resist", False):
                dmg = int(dmg) // 2
        except Exception:
            pass

        try:
            defender.hp = int(defender.hp) - int(dmg)
        except Exception:
            pass
        self._push({"type": "damage", "actor": _name(attacker), "target": _name(defender), "amount": int(dmg), "dtype": damage_type})

        # mark for rage persistence
        try: setattr(attacker, "_dealt_damage_this_turn", True)
        except Exception: pass

        if getattr(defender, "concentration", False):
            dc = max(10, int(dmg) // 2)
            res = self.saving_throw(defender, "CON", dc)
            if not res["success"]:
                setattr(defender, "concentration", False)
                self._push({"type": "concentration_broken", "target": _name(defender)})

        if getattr(defender, "hp", 0) <= 0 and _alive(defender):
            setattr(defender, "alive", False)
            self._push({"type": "down", "name": _name(defender)})
