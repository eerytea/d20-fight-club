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


@dataclass
class Team:
    tid: int
    name: str
    color: Tuple[int, int, int]


# ------------- small helpers -------------
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
        try:
            return (1, int(s))
        except Exception:
            return (1, 4)
    a, b = s.split("d", 1)
    try:
        n = int(a) if a else 1
        m = int(b)
        return (max(1, n), max(1, m))
    except Exception:
        return (1, 4)


def _roll_dice(rng: random.Random, n: int, sides: int) -> int:
    n = max(1, int(n))
    sides = max(1, int(sides))
    return sum(rng.randint(1, sides) for _ in range(n))


def _roll_d20(rng: random.Random, adv: int = 0) -> Tuple[Any, int]:
    """
    Return (raw, effective). When adv/dis, raw is a (a,b) tuple.
    adv: -1, 0, +1
    """
    a = rng.randint(1, 20)
    if adv > 0:
        b = rng.randint(1, 20)
        return ((a, b), max(a, b))
    if adv < 0:
        b = rng.randint(1, 20)
        return ((a, b), min(a, b))
    return (a, a)


def _dist_xy(ax: int, ay: int, bx: int, by: int) -> int:
    # Chebyshev distance for grid range tests; movement is 4-dir only elsewhere.
    return max(abs(ax - bx), abs(ay - by))


# ------------- main engine -------------
class TBCombat:
    """
    Turn-based D20 combat on a fixed-size grid.

    Supported features (per patch roadmap):
      - Initiative: d20 + DEX mod (fixed for battle).
      - Movement: 4-dir only, opportunity attacks on leaving reach.
      - Weapons: melee (reach), finesse (best of STR/DEX), ranged (normal/long).
      - Advantage/Disadvantage flags and effects.
      - Ranged: disadvantage at long range and when threatened in melee; out-of-range cleanly fails.
      - Actions (Patch D): Dash, Disengage, Dodge, Hide, Ready; reaction pool resets each round.
      - Saves & Conditions (Patch E): save scaffold + Prone/Restrained/Stunned; concentration checks.
      - Healing & Simple Spells (Patch F): heal, spell attack/save, line AoE.
      - Tactics controllers (Patch G): external controllers feed intents.
      - Race perks: unarmed dice, save advantages via tags, poison resistance, sleep immunity,
                    goblin bonus damage per level (dmg_bonus_per_level).
    """

    def __init__(
        self,
        teamA: Team,
        teamB: Team,
        fighters: List[Any],
        cols: int,
        rows: int,
        *,
        seed: Optional[int] = None,
    ):
        self.teams = {0: teamA, 1: teamB}
        self.fighters: List[Any] = list(fighters)
        self.cols, self.rows = int(cols), int(rows)
        self.events: List[Dict[str, Any]] = []
        self.rng = random.Random(seed)
        self.round: int = 1
        self.winner: Optional[int] = None

        # Per-team controllers (AI/tactics)
        self.controllers: Dict[int, Any] = {0: None, 1: None}

        # Ensure minimum fields on fighters
        for i, f in enumerate(self.fighters):
            if not hasattr(f, "pid"):
                try:
                    setattr(f, "pid", i)
                except Exception:
                    pass
            if not hasattr(f, "team_id"):
                try:
                    setattr(f, "team_id", getattr(f, "tid", 0))
                except Exception:
                    pass
            if not hasattr(f, "tx"):
                setattr(f, "tx", getattr(f, "x", 0))
            if not hasattr(f, "ty"):
                setattr(f, "ty", getattr(f, "y", 0))
            if not hasattr(f, "alive"):
                setattr(f, "alive", True)
            if not hasattr(f, "hp"):
                setattr(f, "hp", 10)
            if not hasattr(f, "max_hp"):
                setattr(f, "max_hp", getattr(f, "hp", 10))
            if not hasattr(f, "ac"):
                setattr(f, "ac", 12)
            if not hasattr(f, "speed"):
                setattr(f, "speed", 4)
            if not hasattr(f, "reactions_left"):
                setattr(f, "reactions_left", 1)

        # Initiative: fixed order
        rolls: List[Tuple[int, int]] = []
        for i, f in enumerate(self.fighters):
            dexmod = _ability_mod(f, "DEX")
            _, eff = _roll_d20(self.rng, 0)
            rolls.append((eff + dexmod, i))
        rolls.sort(reverse=True)
        self._initiative = [i for _, i in rolls]
        self.turn_idx = 0

        # First event
        self._push({"type": "round_start", "round": self.round})

    # ---------- world helpers ----------
    def _push(self, ev: Dict[str, Any]):
        self.events.append(ev)

    def _team_of(self, f) -> int:
        return int(getattr(f, "team_id", getattr(f, "tid", 0)))

    def _enemies_of(self, f):
        tid = self._team_of(f)
        return [x for x in self.fighters if self._team_of(x) != tid]

    def _friendlies_of(self, f):
        tid = self._team_of(f)
        return [x for x in self.fighters if self._team_of(x) == tid and x is not f]

    def _get_controller(self, f):
        return self.controllers.get(self._team_of(f))

    def distance(self, a, b) -> int:
        return _dist_xy(getattr(a, "tx", 0), getattr(a, "ty", 0), getattr(b, "tx", 0), getattr(b, "ty", 0))

    def distance_coords(self, ax: int, ay: int, bx: int, by: int) -> int:
        return _dist_xy(ax, ay, bx, by)

    def reach(self, a) -> int:
        _, _, _, r = self._weapon_profile(a)
        return int(r)

    def speed_of(self, a) -> int:
        return int(getattr(a, "speed", 4))

    def threatened_in_melee(self, a) -> bool:
        ax, ay = getattr(a, "tx", 0), getattr(a, "ty", 0)
        for e in self._enemies_of(a):
            if not _alive(e):
                continue
            _, _, _, r = self._weapon_profile(e)
            if self.distance_coords(ax, ay, getattr(e, "tx", 0), getattr(e, "ty", 0)) <= r:
                return True
        return False

    def path_step_towards(self, a, to_xy: Tuple[int, int]) -> Tuple[int, int]:
        """Next 4-dir step towards target cell (no pathfinding/blockers here)."""
        ax, ay = getattr(a, "tx", 0), getattr(a, "ty", 0)
        tx, ty = map(int, to_xy)
        dx = 0 if ax == tx else (1 if tx > ax else -1)
        dy = 0 if ay == ty else (1 if ty > ay else -1)
        # No diagonal movement: choose the larger gap axis
        if dx != 0 and dy != 0:
            if abs(tx - ax) >= abs(ty - ay):
                dy = 0
            else:
                dx = 0
        return (ax + dx, ay + dy)

    # ---------- profiles / rolls ----------
    def _weapon_profile(self, f) -> Tuple[int, int, str, int]:
        """
        Returns (num, sides, ability, reach).
        If no weapon, uses race unarmed (unarmed_dice) or 1d4 STR, reach 1.
        """
        w = getattr(f, "weapon", None)
        if w is None:
            un = getattr(f, "unarmed_dice", None)
            if isinstance(un, str):
                num, sides = _parse_dice(un)
            else:
                num, sides = (1, 4)
            return (num, sides, "STR", 1)

        if isinstance(w, dict):
            num, sides = _parse_dice(w.get("dice", w.get("formula", "1d4")))
            reach = int(w.get("reach", 1))
            ability = str(w.get("ability", w.get("mod", "STR"))).upper()
            finesse = bool(w.get("finesse", False))
            if finesse:
                ability = "FINESSE"
            if ability not in ("STR", "DEX", "FINESSE"):
                ability = "STR"
            return (num, sides, ability, max(1, reach))

        if isinstance(w, str):
            wl = w.lower()
            reach = 1
            finesse = ("finesse" in wl)
            ability = "FINESSE" if finesse else (
                "DEX" if any(k in wl for k in ("bow", "javelin", "ranged", "crossbow", "sling", "dart")) else "STR"
            )
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

    def _attack_roll(
        self, attacker, defender, *, advantage: int = 0, ranged: bool = False, long_range: bool = False
    ) -> Tuple[bool, bool, Any, int, int]:
        ctx = advantage
        # Incoming Dodge
        if getattr(defender, "_status_dodging", False):
            ctx -= 1
        # Restrained target grants advantage
        if has_condition(defender, CONDITION_RESTRAINED):
            ctx += 1
        # Prone: melee adv, ranged dis
        if has_condition(defender, CONDITION_PRONE):
            if ranged:
                ctx -= 1
            else:
                ctx += 1

        raw, eff = _roll_d20(self.rng, max(-1, min(1, ctx)))
        crit = (eff == 20)
        # Ability mod
        num, sides, ability, _ = self._weapon_profile(attacker)
        if ability == "FINESSE":
            mod = max(_ability_mod(attacker, "STR"), _ability_mod(attacker, "DEX"))
        else:
            mod = _ability_mod(attacker, "DEX" if ranged else ability)

        ac = int(getattr(defender, "ac", 12))
        hit = (eff + mod >= ac) or crit
        return (hit, crit, raw, eff, mod)

    def _spell_attack_roll(self, caster, target, *, ability="INT", normal_range=12, long_range=24
                           ) -> Tuple[bool, bool, Any, int, int]:
        adv = 0
        d = self.distance(caster, target)
        if d > int(long_range):
            # Caller will treat as out of range
            return (False, False, 1, 1, _ability_mod(caster, ability))
        if d > int(normal_range):
            adv -= 1
        if self.threatened_in_melee(caster):
            adv -= 1
        raw, eff = _roll_d20(self.rng, adv)
        crit = (eff == 20)
        mod = _ability_mod(caster, ability)
        ac = int(getattr(target, "ac", 12))
        hit = (eff + mod >= ac) or crit
        return (hit, crit, raw, eff, mod)

    # ---------- main loop ----------
    def take_turn(self):
        if self.winner is not None:
            return

        # New round housekeeping when pointer loops
        if self.turn_idx == 0 and (len(self.events) == 0 or self.events[-1].get("type") != "round_start"):
            self.round += 1
            for f in self.fighters:
                try:
                    setattr(f, "reactions_left", 1)
                except Exception:
                    pass
            self._push({"type": "round_start", "round": self.round})

        # Select actor
        if not self._initiative:
            return
        act_i = self._initiative[self.turn_idx % len(self._initiative)]
        actor = self.fighters[act_i]

        # Skip dead
        if not _alive(actor):
            self._advance_pointer(actor)
            return

        self._push({"type": "turn_start", "actor": _name(actor)})

        # Clear/maintain per-turn flags
        setattr(actor, "_status_disengage", False)
        setattr(actor, "_dash_pool", 0)
        # Dodge ends at start of actor's next turn
        if getattr(actor, "_status_dodging", False):
            setattr(actor, "_status_dodging", False)

        # Stunned: skip
        if has_condition(actor, CONDITION_STUNNED):
            decrement_all_for_turn(actor)
            self._advance_pointer(actor)
            return

        # Get intents
        intents: List[Dict[str, Any]] = []
        ctrl = self._get_controller(actor)
        if ctrl is not None and hasattr(ctrl, "decide"):
            try:
                intents = ctrl.decide(self, actor) or []
            except Exception:
                intents = []

        if not intents:
            intents = self._baseline_intents(actor)

        # Execute
        steps_left = int(getattr(actor, "speed", 4))
        for intent in intents:
            if self.winner is not None:
                break
            t = intent.get("type")

            if t == "disengage":
                setattr(actor, "_status_disengage", True)

            elif t == "dodge":
                setattr(actor, "_status_dodging", True)

            elif t == "dash":
                setattr(actor, "_dash_pool", getattr(actor, "_dash_pool", 0) + int(getattr(actor, "speed", 4)))

            elif t == "ready":
                setattr(actor, "_ready_reaction", True)

            elif t == "hide":
                setattr(actor, "hidden", True)

            elif t == "move":
                to = tuple(intent.get("to", (getattr(actor, "tx", 0), getattr(actor, "ty", 0))))
                steps_left = self._do_move(actor, to, steps_left)

            elif t == "attack":
                target = intent.get("target") or self._pick_nearest_enemy(actor)
                if target is not None:
                    self._do_attack(actor, target, opportunity=False)

            elif t == "heal":
                tgt = intent.get("target", actor)
                dice = str(intent.get("dice", "1d4"))
                ability = str(intent.get("ability", "WIS")).upper()
                self._do_heal(actor, tgt, dice, ability)

            elif t == "spell_attack":
                tgt = intent.get("target")
                if tgt is None:
                    continue
                dice = str(intent.get("dice", "1d8"))
                ability = str(intent.get("ability", "INT")).upper()
                nr = int(intent.get("normal_range", 12))
                lr = int(intent.get("long_range", 24))
                dtype = intent.get("damage_type")
                self._cast_spell_attack(actor, tgt, dice=dice, ability=ability, normal_range=nr, long_range=lr, damage_type=dtype)

            elif t == "spell_save":
                tgt = intent.get("target")
                if tgt is None:
                    continue
                save = str(intent.get("save", "DEX")).upper()
                dc = int(intent.get("dc", 12))
                dice = intent.get("dice", "1d8")
                ability = str(intent.get("ability", "INT")).upper()
                half = bool(intent.get("half_on_success", False))
                tags = intent.get("tags")
                dtype = intent.get("damage_type")
                cond = None
                if "apply_condition_on_fail" in intent:
                    cond = tuple(intent["apply_condition_on_fail"])
                self._cast_spell_save(
                    actor,
                    tgt,
                    save=save,
                    dc=dc,
                    dice=dice,
                    ability=ability,
                    half_on_success=half,
                    tags=tags,
                    damage_type=dtype,
                    apply_condition_on_fail=cond,
                )

            elif t == "spell_line":
                target_xy = tuple(intent.get("target_xy", (getattr(actor, "tx", 0), getattr(actor, "ty", 0))))
                length = int(intent.get("length", 6))
                dice = str(intent.get("dice", "1d6"))
                ability = str(intent.get("ability", "INT")).upper()
                self._do_spell_line(actor, target_xy, length, dice, ability)

            elif t == "apply_condition":
                tgt = intent.get("target")
                if tgt is None:
                    continue
                cond = str(intent.get("condition", "prone"))
                save = str(intent.get("save", "CON")).upper()
                dc = int(intent.get("dc", 12))
                dur = int(intent.get("duration", 1))
                res = self.saving_throw(tgt, save, dc)
                if not res["success"]:
                    add_condition(tgt, cond, dur)
                    self._push({
                        "type": "condition_applied",
                        "source": _name(actor),
                        "target": _name(tgt),
                        "condition": cond,
                        "duration": dur,
                    })

        # End-of-turn condition tick
        decrement_all_for_turn(actor)
        # Advance pointer & handle round/win conditions
        self._advance_pointer(actor)

    # ---------- pointer / victory ----------
    def _advance_pointer(self, actor):
        # Victory check
        if self._team_defeated(0) and self._team_defeated(1):
            self.winner = None
            self._push({"type": "end", "winner": None})
        elif self._team_defeated(1):
            self.winner = 0
            self._push({"type": "end", "winner": 0})
        elif self._team_defeated(0):
            self.winner = 1
            self._push({"type": "end", "winner": 1})

        self.turn_idx = (self.turn_idx + 1) % len(self._initiative)
        if self.turn_idx == 0 and self.winner is None:
            for f in self.fighters:
                try:
                    setattr(f, "reactions_left", 1)
                except Exception:
                    pass
            self.round += 1
            self._push({"type": "round_start", "round": self.round})

    def _team_defeated(self, tid: int) -> bool:
        return all((not _alive(f)) or self._team_of(f) != tid for f in self.fighters)

    # ---------- baseline AI ----------
    def _baseline_intents(self, actor) -> List[Dict[str, Any]]:
        t = self._pick_nearest_enemy(actor)
        if not t:
            return []
        if self.distance(actor, t) <= self.reach(actor):
            return [{"type": "attack", "target": t}]
        else:
            return [{"type": "move", "to": (getattr(t, "tx", 0), getattr(t, "ty", 0))}]

    def _pick_nearest_enemy(self, actor):
        enemies = [e for e in self._enemies_of(actor) if _alive(e)]
        if not enemies:
            return None
        enemies.sort(key=lambda e: self.distance(actor, e))
        return enemies[0]

    # ---------- movement & OA ----------
    def _do_move(self, actor, to_xy: Tuple[int, int], steps_left: int) -> int:
        ax, ay = getattr(actor, "tx", 0), getattr(actor, "ty", 0)
        goal = tuple(map(int, to_xy))
        pool = steps_left + int(getattr(actor, "_dash_pool", 0))

        while pool > 0 and (ax, ay) != goal:
            nx, ny = self.path_step_towards(actor, goal)

            # Opportunity attacks: leaving reach
            if not getattr(actor, "_status_disengage", False):
                for e in self._enemies_of(actor):
                    if not _alive(e):
                        continue
                    reach = self.reach(e)
                    d_before = self.distance_coords(ax, ay, getattr(e, "tx", 0), getattr(e, "ty", 0))
                    d_after = self.distance_coords(nx, ny, getattr(e, "tx", 0), getattr(e, "ty", 0))
                    if d_before <= reach and d_after > reach and int(getattr(e, "reactions_left", 0)) > 0:
                        self._do_attack(e, actor, opportunity=True)
                        try:
                            setattr(e, "reactions_left", int(getattr(e, "reactions_left", 0)) - 1)
                        except Exception:
                            pass
                        if self.winner is not None:
                            return 0

            # Step
            setattr(actor, "tx", nx)
            setattr(actor, "ty", ny)
            self._push({"type": "move_step", "actor": _name(actor), "to": (nx, ny)})
            ax, ay = nx, ny
            pool -= 1

            # Ready reactions (entering reach)
            for e in self._enemies_of(actor):
                if not _alive(e):
                    continue
                if not getattr(e, "_ready_reaction", False):
                    continue
                reach = self.reach(e)
                d_now = self.distance_coords(ax, ay, getattr(e, "tx", 0), getattr(e, "ty", 0))
                if d_now <= reach and int(getattr(e, "reactions_left", 0)) > 0:
                    self._do_attack(e, actor, opportunity=True)
                    try:
                        setattr(e, "reactions_left", int(getattr(e, "reactions_left", 0)) - 1)
                    except Exception:
                        pass
                    setattr(e, "_ready_reaction", False)
                    if self.winner is not None:
                        return 0

        # Recompute remaining steps (dash consumed first)
        used = (steps_left + int(getattr(actor, "_dash_pool", 0))) - pool
        dash = int(getattr(actor, "_dash_pool", 0))
        if used <= dash:
            setattr(actor, "_dash_pool", dash - used)
            return steps_left
        else:
            used -= dash
            setattr(actor, "_dash_pool", 0)
            return max(0, steps_left - used)

    # ---------- attacks / heals ----------
    def _do_attack(self, attacker, defender, *, opportunity: bool):
        if not (_alive(attacker) and _alive(defender)):
            return

        ranged = False
        long_dis = False
        rp = self._ranged_profile(attacker)
        num, sides, ability, reach = self._weapon_profile(attacker)
        if rp is not None:
            ranged = True
            normal, longr = rp[-1]
            d = self.distance(attacker, defender)
            if d > longr:
                self._push({
                    "type": "attack",
                    "actor": _name(attacker),
                    "target": _name(defender),
                    "hit": False,
                    "reason": "out_of_range",
                    "ranged": True,
                    "opportunity": opportunity,
                    "advantage": False,
                    "disadvantage": False,
                })
                return
            long_dis = d > normal

        adv = 0
        if ranged:
            if long_dis:
                adv -= 1
            if self.threatened_in_melee(attacker):
                adv -= 1

        hit, crit, raw, eff, mod = self._attack_roll(
            attacker, defender, advantage=adv, ranged=ranged, long_range=long_dis
        )
        log = {
            "type": "attack",
            "actor": _name(attacker),
            "target": _name(defender),
            "ranged": ranged,
            "opportunity": bool(opportunity),
            "critical": bool(crit),
            "hit": bool(hit),
            "advantage": isinstance(raw, tuple) and eff == max(raw) and adv > 0,
            "disadvantage": isinstance(raw, tuple) and eff == min(raw) and adv < 0,
        }
        self._push(log)

        if hit:
            # Damage (double dice on crit)
            if ranged and rp is not None:
                num, sides, ability, _, _ = rp
            base = _roll_dice(self.rng, num * (2 if crit else 1), sides)
            if ability == "FINESSE":
                base += max(_ability_mod(attacker, "STR"), _ability_mod(attacker, "DEX"))
            else:
                base += _ability_mod(attacker, ("DEX" if ranged else ability))
            self._apply_damage(attacker, defender, base)

    def _do_heal(self, healer, target, dice: str, ability: str):
        num, sides = _parse_dice(dice)
        amt = _roll_dice(self.rng, num, sides) + max(0, _ability_mod(healer, ability))
        try:
            target.hp = min(int(getattr(target, "max_hp", getattr(target, "hp", 0))),
                            int(getattr(target, "hp", 0)) + max(0, amt))
        except Exception:
            pass
        self._push({"type": "heal", "source": _name(healer), "target": _name(target), "amount": max(0, amt)})

    # ---------- spells ----------
    def _cast_spell_attack(
        self,
        caster,
        target,
        *,
        dice: str = "1d8",
        ability: str = "INT",
        normal_range: int = 12,
        long_range: int = 24,
        damage_type: Optional[str] = None,
    ):
        if not (_alive(caster) and _alive(target)):
            return
        hit, crit, raw, eff, mod = self._spell_attack_roll(
            caster, target, ability=ability, normal_range=normal_range, long_range=long_range
        )
        log = {
            "type": "spell_attack",
            "actor": _name(caster),
            "target": _name(target),
            "roll": raw,
            "effective": eff,
            "critical": bool(crit),
            "hit": bool(hit),
        }
        self._push(log)

        d = self.distance(caster, target)
        if d > int(long_range):
            # Out of range -> no damage
            return

        if hit:
            num, sides = _parse_dice(dice)
            dmg = _roll_dice(self.rng, (2 if crit else 1) * num, sides) + max(0, _ability_mod(caster, ability))
            self._apply_damage(caster, target, dmg, damage_type=damage_type)

    def _cast_spell_save(
        self,
        caster,
        target,
        *,
        save: str = "DEX",
        dc: int = 12,
        dice: Optional[str] = "1d8",
        ability: str = "INT",
        half_on_success: bool = False,
        apply_condition_on_fail: Optional[Tuple[str, int]] = None,
        tags: Optional[List[str]] = None,
        damage_type: Optional[str] = None,
    ):
        if not (_alive(caster) and _alive(target)):
            return
        tags = [t.lower() for t in (tags or [])]
        res = self.saving_throw(target, save, dc, tags=tags)
        dmg = 0
        if dice:
            num, sides = _parse_dice(dice)
            base = _roll_dice(self.rng, num, sides) + max(0, _ability_mod(caster, ability))
            if res["success"] and half_on_success:
                dmg = max(0, base // 2)
            elif not res["success"]:
                dmg = max(0, base)
        if dmg > 0:
            self._apply_damage(caster, target, dmg, damage_type=damage_type)

        # Apply condition on fail (respect sleep immunity)
        if (not res["success"]) and apply_condition_on_fail:
            cname, dur = apply_condition_on_fail
            if cname.lower() == "sleep" and getattr(target, "sleep_immune", False):
                self._push({"type": "condition_ignored", "target": _name(target), "condition": cname, "reason": "immune"})
            else:
                add_condition(target, cname, int(dur))
                self._push({
                    "type": "condition_applied",
                    "source": _name(caster),
                    "target": _name(target),
                    "condition": cname,
                    "duration": int(dur),
                })

    def _do_spell_line(self, caster, target_xy: Tuple[int, int], length: int, dice: str, ability: str):
        sx, sy = getattr(caster, "tx", 0), getattr(caster, "ty", 0)
        ex, ey = target_xy
        cells = line_aoe_cells((sx, sy), (ex, ey), length)
        self._push({"type": "spell_aoe", "source": _name(caster), "cells": cells})
        # One roll for all targets
        num, sides = _parse_dice(dice)
        dmg = _roll_dice(self.rng, num, sides) + max(0, _ability_mod(caster, ability))
        for f in self._enemies_of(caster):
            if not _alive(f):
                continue
            pos = (getattr(f, "tx", 0), getattr(f, "ty", 0))
            if pos in cells:
                self._apply_damage(caster, f, dmg)

    # ---------- saves / damage ----------
    def saving_throw(
        self, actor, ability: str, dc: int, *, adv: int = 0, tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        a = (ability or "CON").upper()
        tags = [t.lower() for t in (tags or [])]
        ctx = (1 if adv > 0 else -1 if adv < 0 else 0)

        # Conditions
        if a == "DEX" and has_condition(actor, CONDITION_RESTRAINED):
            ctx -= 1
        if a in ("STR", "DEX") and has_condition(actor, CONDITION_STUNNED):
            ctx -= 1

        # Race perks
        if getattr(actor, "adv_vs_poison", False) and ("poison" in tags):
            ctx += 1
        if getattr(actor, "adv_vs_charm", False) and ("charm" in tags):
            ctx += 1
        if getattr(actor, "adv_vs_paralysis", False) and ("paralysis" in tags):
            ctx += 1
        if getattr(actor, "adv_vs_magic_mental", False) and ("magic" in tags) and a in ("INT", "WIS", "CHA"):
            ctx += 1

        raw, eff = _roll_d20(self.rng, max(-1, min(1, ctx)))
        mod = _ability_mod(actor, a)
        total = eff + mod
        success = total >= int(dc)
        payload = {
            "type": "save",
            "target": _name(actor),
            "ability": a,
            "roll": raw,
            "effective": eff,
            "modifier": mod,
            "dc": int(dc),
            "success": bool(success),
            "advantage": isinstance(raw, tuple) and eff == max(raw) and ctx > 0,
            "disadvantage": isinstance(raw, tuple) and eff == min(raw) and ctx < 0,
            "tags": tags,
        }
        self._push(payload)
        return payload

    def _apply_damage(self, attacker, defender, dmg: int, *, damage_type: Optional[str] = None):
        # Outgoing bonus per level (Goblin etc.)
        try:
            per_lvl = int(getattr(attacker, "dmg_bonus_per_level", 0))
            lvl = int(getattr(attacker, "level", getattr(attacker, "lvl", 1)))
            if per_lvl > 0 and lvl > 0:
                dmg = int(dmg) + per_lvl * lvl
        except Exception:
            pass

        # Poison resistance halves poison damage (dwarves, golem, etc.)
        try:
            if damage_type and damage_type.lower() == "poison" and getattr(defender, "poison_resist", False):
                dmg = int(dmg) // 2
        except Exception:
            pass

        try:
            defender.hp = int(defender.hp) - int(dmg)
        except Exception:
            pass
        self._push({"type": "damage", "actor": _name(attacker), "target": _name(defender), "amount": int(dmg), "dtype": damage_type})

        # Concentration check on damage
        if getattr(defender, "concentration", False):
            dc = max(10, int(dmg) // 2)
            res = self.saving_throw(defender, "CON", dc)
            if not res["success"]:
                try:
                    setattr(defender, "concentration", False)
                except Exception:
                    pass
                self._push({"type": "concentration_broken", "target": _name(defender)})

        if getattr(defender, "hp", 0) <= 0 and _alive(defender):
            try:
                setattr(defender, "alive", False)
            except Exception:
                pass
            self._push({"type": "down", "name": _name(defender)})
