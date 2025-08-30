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
    Adds equipment handedness:
      - equipped.main_hand_id / off_hand_id / armor_id / shield_id (shield stacks to AC; off-hand weapon enables an extra swing).
      - Versatile weapons (Longsword, Warhammer, Unarmed) auto-upgrade dice when two-handed (off-hand empty, no shield).
      - Dual-wield: off-hand swing gets NO proficiency to-hit or damage.
      - OA uses main hand only; 'reach' uses the best of main/off.
    Keeps all previous features (ranged rules, Barbarian, Bard, proficiency to-hit+damage, etc.).
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

        # Seed defaults
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
            setattr(f, "inspiration_tokens", int(getattr(f, "inspiration_tokens", 0)))
            setattr(f, "inspiration_used", int(getattr(f, "inspiration_used", 0)))
            # legacy compatibility: ensure equipped container exists
            if not hasattr(f, "equipped"): setattr(f, "equipped", {})

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

    # ---------- equipment helpers ----------
    def _inv_lookup(self, f, kind: str, item_id: Optional[str]) -> Optional[Dict[str, Any]]:
        inv = getattr(f, "inventory", {})
        items = inv.get(kind, [])
        for it in items:
            if it.get("id") == item_id:
                return it
        return None

    def _equipped_main(self, f) -> Optional[Dict[str, Any]]:
        eq = getattr(f, "equipped", {})
        wid = eq.get("main_hand_id")
        if wid is None:
            return getattr(f, "weapon", None) if isinstance(getattr(f, "weapon", None), dict) else None
        return self._inv_lookup(f, "weapons", wid)

    def _equipped_off(self, f) -> Optional[Dict[str, Any]]:
        eq = getattr(f, "equipped", {})
        oid = eq.get("off_hand_id")
        if oid is None: return None
        # It could be a shield or a weapon
        s = self._inv_lookup(f, "shields", oid)
        if s: return s
        return self._inv_lookup(f, "weapons", oid)

    def _two_handing(self, f) -> bool:
        """True when no shield and no off-hand weapon."""
        off = self._equipped_off(f)
        if off is None: return True
        # If off-hand is a shield or a weapon, not two-handing
        return False

    def _weapon_profile_from_item(self, f, w: Optional[Dict[str, Any]]) -> Tuple[int, int, str, int]:
        """Translate an explicit weapon item to (num, sides, ability, reach), handling Unarmed & Versatile."""
        if w is None:
            # fallback to unarmed: race may have 'unarmed_dice'; otherwise 1d1 finesse
            ud = getattr(f, "unarmed_dice", None)
            if isinstance(ud, str):
                num, sides = _parse_dice(ud)
                return (num, sides, "STR", 1)
            return (1, 1, "FINESSE", 1)

        # Unarmed weapon entry
        if w.get("unarmed"):
            ud = getattr(f, "unarmed_dice", None)
            if isinstance(ud, str):
                num, sides = _parse_dice(ud)
                return (num, sides, "STR", 1)
            return (1, 1, "FINESSE", 1)

        num, sides = _parse_dice(w.get("dice", "1d4"))
        # Versatile two-handed upgrade if applicable
        if bool(w.get("versatile", False)) and self._two_handing(f) and w.get("two_handed_dice"):
            num, sides = _parse_dice(w["two_handed_dice"])
        ability = str(w.get("ability", "STR")).upper()
        if bool(w.get("finesse", False)):
            ability = "FINESSE"
        reach = int(w.get("reach", 1))
        return (num, sides, ability, max(1, reach))

    def reach(self, a) -> int:
        # Threaten with the best of main/off weapon reaches
        main = self._equipped_main(a)
        off = self._equipped_off(a)
        r1 = self._weapon_profile_from_item(a, main)[3]
        r2 = 0
        if off and off.get("type") == "weapon":
            r2 = self._weapon_profile_from_item(a, off)[3]
        return max(r1, r2)

    def speed_of(self, a) -> int:
        return int(getattr(a, "speed", 4))

    def threatened_in_melee(self, a) -> bool:
        ax, ay = getattr(a, "tx", 0), getattr(a, "ty", 0)
        for e in self._enemies_of(a):
            if not _alive(e): continue
            r = self.reach(e)
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

    # ---------- rolls ----------
    def _attack_roll_with_item(self, attacker, defender, weapon_item: Optional[Dict[str, Any]],
                               *, advantage: int = 0, ranged: bool = False,
                               offhand: bool = False) -> Tuple[bool, bool, Any, int, int, int]:
        ctx = advantage
        # Inspiration token for attacker
        consume_token = False
        try:
            if int(getattr(attacker, "inspiration_tokens", 0)) > 0:
                ctx += 1; consume_token = True
        except Exception:
            pass
        # Defender effects
        if getattr(defender, "_status_dodging", False): ctx -= 1
        if has_condition(defender, CONDITION_RESTRAINED): ctx += 1
        if has_condition(defender, CONDITION_PRONE):
            ctx += (1 if not ranged else 0)
            ctx -= (1 if ranged else 0)

        raw, eff = _roll_d20(self.rng, max(-1, min(1, ctx)))
        if consume_token:
            try: setattr(attacker, "inspiration_tokens", int(getattr(attacker, "inspiration_tokens", 1)) - 1)
            except Exception: pass

        num, sides, ability, _ = self._weapon_profile_from_item(attacker, weapon_item)
        # Ability mod
        if ability == "FINESSE":
            mod = max(_ability_mod(attacker, "STR"), _ability_mod(attacker, "DEX"))
        else:
            mod = _ability_mod(attacker, "DEX" if ranged else ability)

        prof = 0 if offhand else _prof_for_level(getattr(attacker, "level", getattr(attacker, "lvl", 1)))
        ac = int(getattr(defender, "ac", 12))
        hit = (eff + mod + prof >= ac) or (eff == 20)
        return (hit, eff == 20, raw, eff, mod, prof)

    # Ranged profile unchanged (most of our starting kit is melee)
    def _ranged_profile(self, f) -> Optional[Tuple[int, int, str, int, Tuple[int, int]]]:
        w = self._equipped_main(f)
        if isinstance(w, dict) and bool(w.get("ranged", False)):
            num, sides = _parse_dice(w.get("dice", "1d6"))
            ability = str(w.get("ability", "DEX")).upper()
            normal, longr = w.get("range", (8, 16))
            return (num, sides, ability, 1, (int(normal), int(longr)))
        return None

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
            self._advance_pointer(actor); return

        self._push({"type": "turn_start", "actor": _name(actor)})
        setattr(actor, "_status_disengage", False)
        if getattr(actor, "_status_dodging", False): setattr(actor, "_status_dodging", False)
        setattr(actor, "_dash_pool", 0)
        setattr(actor, "_dealt_damage_this_turn", False)

        if has_condition(actor, CONDITION_STUNNED):
            decrement_all_for_turn(actor); self._advance_pointer(actor); return

        intents: List[Dict[str, Any]] = []
        ctrl = self.controllers.get(self._team_of(actor))
        if ctrl is not None and hasattr(ctrl, "decide"):
            try: intents = ctrl.decide(self, actor) or []
            except Exception: intents = []
        if not intents:
            intents = self._baseline_intents(actor)

        # Steps (+2 if Barbarian L5+ unarmored)
        steps_left = int(getattr(actor, "speed", 4))
        try:
            if int(getattr(actor, "level", 1)) >= 5 and int(getattr(actor, "barb_speed_bonus_if_unarmored", 0)) > 0:
                if int(getattr(actor, "armor_bonus", 0)) == 0:
                    steps_left += int(getattr(actor, "barb_speed_bonus_if_unarmored", 0))
        except Exception:
            pass

        for intent in intents:
            t = intent.get("type")

            if t == "disengage": setattr(actor, "_status_disengage", True)
            elif t == "dodge": setattr(actor, "_status_dodging", True)
            elif t == "dash": setattr(actor, "_dash_pool", getattr(actor, "_dash_pool", 0) + int(getattr(actor, "speed", 4)))
            elif t == "hide": setattr(actor, "hidden", True)
            elif t == "ready": setattr(actor, "_ready_reaction", True)
            elif t == "rage":
                setattr(actor, "rage_active", True); setattr(actor, "resist_all", True)
                setattr(actor, "rage_bonus_per_level", 1)
                self._push({"type": "status", "actor": _name(actor), "status": "rage_on"})
            elif t == "inspire":
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
                target = intent.get("target") or self._pick_nearest_enemy(actor)
                if target is None: continue
                # Main-hand swings (Barbarian extra attacks apply here)
                swings = 1 + int(getattr(actor, "barb_extra_attacks", 0))
                for _ in range(swings):
                    if not (_alive(actor) and _alive(target)): break
                    self._do_melee_attack(actor, target, opportunity=False, offhand=False)
                # Off-hand extra swing if a weapon (not shield) is equipped in off-hand
                off = self._equipped_off(actor)
                if off and off.get("type") == "weapon":
                    if _alive(actor) and _alive(target):
                        self._do_melee_attack(actor, target, opportunity=False, offhand=True)

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
                nr = int(intent.get("normal_range", 12)); lr = int(intent.get("long_range", 24))
                dtype = intent.get("damage_type")
                self._cast_spell_attack(actor, tgt, dice=dice, ability=ability, normal_range=nr, long_range=lr, damage_type=dtype)

            elif t == "spell_save":
                tgt = intent.get("target")
                if tgt is None: continue
                save = str(intent.get("save", "DEX")).upper()
                ability = str(intent.get("ability", "CHA")).upper()
                dc = intent.get("dc")
                if dc is None:
                    prof = _prof_for_level(getattr(actor, "level", getattr(actor, "lvl", 1)))
                    dc = 8 + _ability_mod(actor, ability) + prof
                dice = intent.get("dice", "1d8")
                half = bool(intent.get("half_on_success", False))
                tags = intent.get("tags"); dtype = intent.get("damage_type")
                cond = tuple(intent["apply_condition_on_fail"]) if "apply_condition_on_fail" in intent else None
                self._cast_spell_save(actor, tgt, save=save, dc=int(dc), dice=dice, ability=ability,
                                      half_on_success=half, tags=tags, damage_type=dtype, apply_condition_on_fail=cond)

            if self.winner is not None:
                break

        decrement_all_for_turn(actor)

        # Rage auto-end if no damage dealt (L1–14)
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
            # OA if leaving enemy reach (offhand reach considered)
            if not getattr(actor, "_status_disengage", False):
                for e in self._enemies_of(actor):
                    if not _alive(e): continue
                    reach = self.reach(e)
                    d_before = self.distance_coords(ax, ay, getattr(e, "tx", 0), getattr(e, "ty", 0))
                    d_after = self.distance_coords(nx, ny, getattr(e, "tx", 0), getattr(e, "ty", 0))
                    if d_before <= reach and d_after > reach and int(getattr(e, "reactions_left", 0)) > 0:
                        # OA uses main hand only
                        self._do_melee_attack(e, actor, opportunity=True, offhand=False)
                        setattr(e, "reactions_left", int(getattr(e, "reactions_left", 0)) - 1)
                        if self.winner is not None: return 0

            setattr(actor, "tx", nx); setattr(actor, "ty", ny)
            self._push({"type": "move_step", "actor": _name(actor), "to": (nx, ny)})
            ax, ay = nx, ny
            pool -= 1

            # Ready reactions
            for e in self._enemies_of(actor):
                if not _alive(e): continue
                if not getattr(e, "_ready_reaction", False): continue
                reach = self.reach(e)
                if self.distance_coords(ax, ay, getattr(e, "tx", 0), getattr(e, "ty", 0)) <= reach and int(getattr(e, "reactions_left", 0)) > 0:
                    self._do_melee_attack(e, actor, opportunity=True, offhand=False)
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
    def _do_melee_attack(self, attacker, defender, *, opportunity: bool, offhand: bool):
        if not (_alive(attacker) and _alive(defender)): return

        # Choose weapon item: main or off-hand weapon
        item = self._equipped_off(attacker) if offhand else self._equipped_main(attacker)
        if offhand and (item is None or item.get("type") != "weapon"):
            return  # no offhand weapon swing

        # Determine ranged? (main-hand only uses ranged profile; offhand assumed melee here)
        ranged = False; long_dis = False
        if not offhand:
            rp = self._ranged_profile(attacker)
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

        hit, crit, raw, eff, mod, prof = self._attack_roll_with_item(attacker, defender, item, advantage=adv, ranged=ranged, offhand=offhand)
        self._push({"type": "attack", "actor": _name(attacker), "target": _name(defender), "ranged": ranged,
                    "opportunity": bool(opportunity), "critical": bool(crit), "hit": bool(hit),
                    "advantage": isinstance(raw, tuple) and eff == max(raw) and adv > 0,
                    "disadvantage": isinstance(raw, tuple) and eff == min(raw) and adv < 0,
                    "offhand": bool(offhand)})

        if hit:
            # Get dice profile from item (respect versatile)
            num, sides, ability, _ = self._weapon_profile_from_item(attacker, item)
            base = _roll_dice(self.rng, num * (2 if crit else 1), sides)

            # Barbarian brutal crit only on main-hand weapon attacks
            if (not offhand) and crit and int(getattr(attacker, "barb_crit_extra_dice", 0)) > 0:
                base += _roll_dice(self.rng, int(getattr(attacker, "barb_crit_extra_dice", 0)) * num, sides)

            # Ability mod
            if ability == "FINESSE":
                base += max(_ability_mod(attacker, "STR"), _ability_mod(attacker, "DEX"))
            else:
                base += _ability_mod(attacker, ("DEX" if ranged else ability))

            # Proficiency to damage (house rule) – suppressed for off-hand
            if not offhand:
                base += prof

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
        # Inspiration consumed in _spell_attack_roll (we reuse earlier behavior)
        adv = 0
        consume_token = False
        try:
            if int(getattr(caster, "inspiration_tokens", 0)) > 0:
                adv += 1; consume_token = True
        except Exception:
            pass
        d = self.distance(caster, target)
        if d > int(long_range): return
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

        self._push({"type": "spell_attack", "actor": _name(caster), "target": _name(target), "roll": raw, "effective": eff,
                    "critical": bool(crit), "hit": bool(hit)})
        if hit:
            num, sides = _parse_dice(dice)
            dmg = _roll_dice(self.rng, (2 if crit else 1) * num, sides) + max(0, mod) + prof
            self._apply_damage(caster, target, dmg, damage_type=damage_type)

    def _cast_spell_save(self, caster, target, *, save: str = "DEX", dc: int = 12, dice: Optional[str] = "1d8",
                         ability: str = "CHA", half_on_success: bool = False,
                         apply_condition_on_fail: Optional[Tuple[str, int]] = None,
                         tags: Optional[List[str]] = None, damage_type: Optional[str] = None):
        if not (_alive(caster) and _alive(target)): return
        tags = [t.lower() for t in (tags or [])]
        # Bard aura, inspiration, race perks handled inside saving_throw()
        res = self.saving_throw(target, save, dc, tags=tags)
        dmg = 0
        if dice:
            num, sides = _parse_dice(dice)
            base = _roll_dice(self.rng, num, sides) + max(0, _ability_mod(caster, ability))
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

    # ---------- saves & damage ----------
    def saving_throw(self, actor, ability: str, dc: int, *, adv: int = 0, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        a = (ability or "CON").upper()
        tags = [t.lower() for t in (tags or [])]
        ctx = (1 if adv > 0 else -1 if adv < 0 else 0)

        if a == "DEX" and has_condition(actor, CONDITION_RESTRAINED): ctx -= 1
        if a in ("STR", "DEX") and has_condition(actor, CONDITION_STUNNED): ctx -= 1
        if getattr(actor, "adv_vs_poison", False) and ("poison" in tags): ctx += 1
        if getattr(actor, "adv_vs_charm", False) and ("charm" in tags): ctx += 1
        if getattr(actor, "adv_vs_paralysis", False) and ("paralysis" in tags): ctx += 1
        if getattr(actor, "adv_vs_magic_mental", False) and ("magic" in tags) and a in ("INT", "WIS", "CHA"): ctx += 1
        if bool(getattr(actor, "rage_active", False)) and a == "STR": ctx += 1
        # Bard L6 aura: allies within 6 get adv vs charm/fear
        if ("charm" in tags) or ("fear" in tags):
            for ally in self._friendlies_of(actor):
                if not _alive(ally): continue
                if not bool(getattr(ally, "bard_aura_charm_fear", False)): continue
                if self.distance(actor, ally) <= 6:
                    ctx += 1; break
        # Inspiration token
        consume = False
        try:
            if int(getattr(actor, "inspiration_tokens", 0)) > 0:
                ctx += 1; consume = True
        except Exception:
            pass

        raw, eff = _roll_d20(self.rng, max(-1, min(1, ctx)))
        if consume:
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
        try:
            per_lvl = int(getattr(attacker, "dmg_bonus_per_level", 0))
            lvl = int(getattr(attacker, "level", getattr(attacker, "lvl", 1)))
            if per_lvl > 0 and lvl > 0:
                dmg = int(dmg) + per_lvl * lvl
        except Exception:
            pass
        try:
            if bool(getattr(attacker, "rage_active", False)) and int(getattr(attacker, "rage_bonus_per_level", 0)) > 0:
                lvl = int(getattr(attacker, "level", getattr(attacker, "lvl", 1)))
                dmg = int(dmg) + lvl * int(getattr(attacker, "rage_bonus_per_level", 0))
        except Exception:
            pass
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
