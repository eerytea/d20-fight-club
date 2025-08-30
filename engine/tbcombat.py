# engine/tbcombat.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import random

from engine.conditions import (
    CONDITION_PRONE, CONDITION_RESTRAINED, CONDITION_STUNNED,
    ensure_bag, has_condition, add_condition, clear_condition, decrement_all_for_turn
)

def _prof_for_level(level: int) -> int:
    L = max(1, int(level))
    return min(6, 2 + (L - 1) // 4)

__all__ = ["TBCombat", "Team"]

@dataclass
class Team:
    tid: int
    name: str
    color: Tuple[int, int, int]

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

class TBCombat:
    """
    Adds:
      - Fighter styles (Archer/Defender/Enforcer/Duelist) — already integrated.
      - Monk:
         * Unarmed off-hand proficiency if both strikes are unarmed; from L15, off-hand prof even with a weapon.
         * Bonus unarmed strike if all main-hand swings this action were unarmed (>=2 swings).
         * Deflect Missiles: reduce ranged weapon damage by 1d10 + DEX mod + level (passive).
         * Evasion (L7): on DEX save, success=0 dmg, fail=half.
         * Global adv on all saves at L14.
         * Poison immunity at L10 (damage=0; also auto-pass poison saves).
      - Two-handed enforcement; no proficiency to damage.
      - Events enriched with roll/prof fields.
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
            if not hasattr(f, "equipped"): setattr(f, "equipped", {})

        # Initiative (Barbarian L7 advantage already supported)
        rolls: List[Tuple[int, int]] = []
        for i, f in enumerate(self.fighters):
            dexmod = _ability_mod(f, "DEX")
            adv = 0
            if str(getattr(f, "class", "")).capitalize() == "Barbarian" and int(getattr(f, "level", 1)) >= 7:
                adv = 1
            _, eff = _roll_d20(self.rng, adv)
            rolls.append((eff + dexmod, i))
        rolls.sort(reverse=True)
        self._initiative = [i for _, i in rolls]
        self.turn_idx = 0

        # Start in Wild Shape if equipped
        for f in self.fighters:
            self._maybe_start_wildshape(f)

        self._push({"type": "round_start", "round": self.round})

    # ---------- utils ----------
    def _push(self, ev: Dict[str, Any]): self.events.append(ev)
    def _team_of(self, f) -> int: return int(getattr(f, "team_id", getattr(f, "tid", 0)))
    def _enemies_of(self, f): tid = self._team_of(f); return [x for x in self.fighters if self._team_of(x) != tid]
    def _friendlies_of(self, f): tid = self._team_of(f); return [x for x in self.fighters if self._team_of(x) == tid and x is not f]
    def distance(self, a, b) -> int: return _dist_xy(getattr(a, "tx", 0), getattr(a, "ty", 0), getattr(b, "tx", 0), getattr(b, "ty", 0))

    # ---------- equipment ----------
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
        main = self._equipped_main(f)
        if isinstance(main, dict) and bool(main.get("two_handed", False)):
            return None
        eq = getattr(f, "equipped", {})
        oid = eq.get("off_hand_id")
        if oid is None: return None
        s = self._inv_lookup(f, "shields", oid)
        if s: return s
        w = self._inv_lookup(f, "weapons", oid)
        if w: return w
        form = self._inv_lookup(f, "forms", oid)
        if form: return form
        return None

    def _weapon_profile_from_item(self, f, w: Optional[Dict[str, Any]]) -> Tuple[int, int, str, int]:
        if w is None:
            ud = getattr(f, "unarmed_dice", None)
            if isinstance(ud, str):
                num, sides = _parse_dice(ud)
                return (num, sides, "FINESSE", 1)  # finesse: uses best of STR/DEX
            return (1, 1, "FINESSE", 1)
        if w.get("unarmed"):
            ud = getattr(f, "unarmed_dice", None)
            if isinstance(ud, str):
                num, sides = _parse_dice(ud)
                return (num, sides, "FINESSE", 1)
            return (1, 1, "FINESSE", 1)
        if w.get("wildshape"):
            return (0, 1, "STR", 1)
        num, sides = _parse_dice(w.get("dice", "1d4"))
        if bool(w.get("versatile", False)) and self._equipped_off(f) is None and w.get("two_handed_dice"):
            num, sides = _parse_dice(w["two_handed_dice"])
        ability = "FINESSE" if bool(w.get("finesse", False)) else str(w.get("ability", "STR")).upper()
        reach = int(w.get("reach", 1))
        return (num, sides, ability, max(1, reach))

    def reach(self, a) -> int:
        main = self._equipped_main(a)
        off = self._equipped_off(a)
        r1 = self._weapon_profile_from_item(a, main)[3]
        r2 = 0
        if off and off.get("type") == "weapon":
            r2 = self._weapon_profile_from_item(a, off)[3]
        return max(r1, r2)

    # ---------- wild shape (unchanged from previous) ----------
    def _maybe_start_wildshape(self, f) -> None:
        main = self._equipped_main(f)
        off = self._equipped_off(f)
        if not isinstance(main, dict) or not main.get("wildshape", False):
            return
        if not (isinstance(off, dict) and off.get("type") == "wild_form"):
            self._push({"type": "wildshape", "actor": _name(f), "started": False, "reason": "no_form_selected"})
            return
        allowed = list(getattr(f, "wildshape_allowed_cr", []))
        if allowed and float(off.get("cr", 100.0)) not in allowed and float(off.get("cr", 100.0)) > max(allowed):
            self._push({"type": "wildshape", "actor": _name(f), "started": False, "reason": "cr_not_allowed"})
            return
        stats = dict(off.get("stats", {}))
        f._humanoid_backup = {
            "hp": int(getattr(f, "hp", 1)),
            "max_hp": int(getattr(f, "max_hp", 1)),
            "ac": int(getattr(f, "ac", 10)),
            "speed": int(getattr(f, "speed", 4)),
            "STR": int(getattr(f, "STR", 10)), "DEX": int(getattr(f, "DEX", 10)), "CON": int(getattr(f, "CON", 10)),
            "INT": int(getattr(f, "INT", 10)), "WIS": int(getattr(f, "WIS", 10)), "CHA": int(getattr(f, "CHA", 10)),
            "armor_bonus": int(getattr(f, "armor_bonus", 0)),
            "shield_bonus": int(getattr(f, "shield_bonus", 0)),
            "weapon": getattr(f, "weapon", None),
            "equipped": getattr(f, "equipped", {}).copy(),
        }
        if "hp" in stats: setattr(f, "hp", int(stats["hp"]))
        if "max_hp" in stats: setattr(f, "max_hp", int(stats["max_hp"]))
        if "ac" in stats: setattr(f, "ac", int(stats["ac"]))
        if "speed" in stats: setattr(f, "speed", int(stats["speed"]))
        for key in ("STR","DEX","CON","INT","WIS","CHA"):
            if key in stats:
                setattr(f, key, int(stats[key])); setattr(f, key.lower(), int(stats[key]))
        nat = stats.get("natural_weapon") or {}
        if nat:
            f.weapon = {"type":"weapon","name": nat.get("name","Natural Attack"),
                        "dice": nat.get("dice","1d6"), "reach": int(nat.get("reach",1)),
                        "finesse": bool(nat.get("finesse", False)), "ability": nat.get("ability","STR")}
        setattr(f, "armor_bonus", 0)
        setattr(f, "shield_bonus", 0)
        setattr(f, "wildshape_active", True)
        setattr(f, "wildshape_form_name", off.get("name", "Form"))
        self._push({"type": "wildshape", "actor": _name(f), "started": True, "form": off.get("name")})

    # ---------- helpers for monk ----------
    def _is_monk(self, f) -> bool:
        return str(getattr(f, "class", "")).capitalize() == "Monk"

    def _both_unarmed(self, f) -> bool:
        m = self._equipped_main(f)
        o = self._equipped_off(f)
        main_un = (m is None) or bool(m.get("unarmed", False))
        off_un  = (o is None) or bool(o.get("unarmed", False))
        return main_un and off_un

    # ---------- main loop ----------
    def take_turn(self):
        if self.winner is not None: return

        if self.turn_idx == 0 and (len(self.events) == 0 or self.events[-1].get("type") != "round_start"):
            self.round += 1
            for f in self.fighters: setattr(f, "reactions_left", 1)
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

        steps_left = int(getattr(actor, "speed", 4))
        try:
            if int(getattr(actor, "level", 1)) >= 5 and int(getattr(actor, "barb_speed_bonus_if_unarmored", 0)) > 0:
                if int(getattr(actor, "armor_bonus", 0)) == 0:
                    steps_left += int(getattr(actor, "barb_speed_bonus_if_unarmored", 0))
        except Exception:
            pass

        for intent in intents:
            t = intent.get("type")

            if t == "attack":
                target = intent.get("target") or self._pick_nearest_enemy(actor)
                if target is None: continue

                # Main-hand swings
                swings = 1 + int(getattr(actor, "barb_extra_attacks", 0)) + int(getattr(actor, "fighter_extra_attacks", 0)) + int(getattr(actor, "monk_extra_attacks", 0))
                unarmed_flags: List[bool] = []
                for _ in range(swings):
                    if not (_alive(actor) and _alive(target)): break
                    used_unarmed = self._do_melee_attack(actor, target, opportunity=False, offhand=False)
                    unarmed_flags.append(bool(used_unarmed))

                # Monk bonus unarmed strike if all main-hand swings this action were unarmed and >=2 swings
                if self._is_monk(actor) and len(unarmed_flags) >= 2 and all(unarmed_flags):
                    # Force an extra unarmed swing
                    if _alive(actor) and _alive(target):
                        self._do_melee_attack(actor, target, opportunity=False, offhand=False, force_unarmed=True)
                        self._push({"type":"attack_bonus_unarmed", "actor": _name(actor)})

                # Off-hand swing: if actual off-hand weapon, do it; if Monk with unarmed main and no off-hand weapon, allow unarmed off-hand
                off = self._equipped_off(actor)
                if off and off.get("type") == "weapon":
                    if _alive(actor) and _alive(target):
                        self._do_melee_attack(actor, target, opportunity=False, offhand=True)
                elif self._is_monk(actor):
                    main = self._equipped_main(actor)
                    if (main is None or main.get("unarmed")) and _alive(actor) and _alive(target):
                        # off-hand unarmed attempt
                        self._do_melee_attack(actor, target, opportunity=False, offhand=True, force_unarmed=True)

            elif t == "move":
                to = tuple(intent.get("to", (getattr(actor, "tx", 0), getattr(actor, "ty", 0))))
                steps_left = self._do_move(actor, to, steps_left)

            elif t == "disengage": setattr(actor, "_status_disengage", True)
            elif t == "dodge": setattr(actor, "_status_dodging", True)
            elif t == "dash": setattr(actor, "_dash_pool", getattr(actor, "_dash_pool", 0) + int(getattr(actor, "speed", 4)))
            elif t == "hide": setattr(actor, "hidden", True)
            elif t == "ready": setattr(actor, "_ready_reaction", True)
            elif t == "rage":
                setattr(actor, "rage_active", True); setattr(actor, "resist_all", True)
                setattr(actor, "rage_bonus_per_level", 1)
                self._push({"type": "status", "actor": _name(actor), "status": "rage_on"})
            elif t == "heal":
                tgt = intent.get("target", actor)
                dice = str(intent.get("dice", "1d4"))
                ability = str(intent.get("ability", "WIS")).upper()
                self._do_heal(actor, tgt, dice, ability)
            elif t == "spell_attack":
                if bool(getattr(actor, "wildshape_active", False)) and not bool(getattr(actor, "wildshape_cast_while_shaped", False)):
                    self._push({"type":"spell_blocked","reason":"wildshape"}); continue
                tgt = intent.get("target"); 
                if tgt is None: continue
                dice = str(intent.get("dice", "1d8"))
                ability = str(intent.get("ability", "CHA")).upper()
                nr = int(intent.get("normal_range", 12)); lr = int(intent.get("long_range", 24))
                dtype = intent.get("damage_type")
                self._cast_spell_attack(actor, tgt, dice=dice, ability=ability, normal_range=nr, long_range=lr, damage_type=dtype)
            elif t == "spell_save":
                if bool(getattr(actor, "wildshape_active", False)) and not bool(getattr(actor, "wildshape_cast_while_shaped", False)):
                    self._push({"type":"spell_blocked","reason":"wildshape"}); continue
                tgt = intent.get("target"); 
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

            if self.winner is not None: break

        decrement_all_for_turn(actor)

        try:
            if bool(getattr(actor, "rage_active", False)) and not bool(getattr(actor, "barb_rage_capstone", False)):
                if not bool(getattr(actor, "_dealt_damage_this_turn", False)):
                    setattr(actor, "rage_active", False); setattr(actor, "resist_all", False)
                    setattr(actor, "rage_bonus_per_level", 0)
                    self._push({"type": "status", "actor": _name(actor), "status": "rage_off"})
        except Exception:
            pass

        self._advance_pointer(actor)

    # ---------- movement (OA etc) ----------
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
                    d_before = self.distance(actor, e)
                    d_after = _dist_xy(nx, ny, getattr(e, "tx", 0), getattr(e, "ty", 0))
                    if d_before <= reach and d_after > reach and int(getattr(e, "reactions_left", 0)) > 0:
                        self._do_melee_attack(e, actor, opportunity=True, offhand=False)
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
                if _dist_xy(ax, ay, getattr(e, "tx", 0), getattr(e, "ty", 0)) <= reach and int(getattr(e, "reactions_left", 0)) > 0:
                    self._do_melee_attack(e, actor, opportunity=True, offhand=False)
                    setattr(e, "reactions_left", int(getattr(e, "reactions_left", 0)) - 1)
                    setattr(e, "_ready_reaction", False)
                    if self.winner is not None: return 0
        used = (steps_left + int(getattr(actor, "_dash_pool", 0))) - pool
        dash = int(getattr(actor, "_dash_pool", 0))
        if used <= dash:
            setattr(actor, "_dash_pool", dash - used); return steps_left
        else:
            used -= dash; setattr(actor, "_dash_pool", 0); return max(0, steps_left - used)

    # ---------- attacks ----------
    def _attack_roll_with_item(self, attacker, defender, weapon_item: Optional[Dict[str, Any]],
                               *, advantage: int = 0, ranged: bool = False,
                               offhand: bool = False) -> Tuple[bool, bool, Any, int, int, int, int]:
        ctx = advantage
        consume_token = False
        try:
            if int(getattr(attacker, "inspiration_tokens", 0)) > 0:
                ctx += 1; consume_token = True
        except Exception: pass
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
        if ability == "FINESSE":
            mod = max(_ability_mod(attacker, "STR"), _ability_mod(attacker, "DEX"))
        else:
            mod = _ability_mod(attacker, "DEX" if ranged else ability)

        base_prof = _prof_for_level(getattr(attacker, "level", getattr(attacker, "lvl", 1)))
        prof = base_prof if not offhand else 0

        # Duelist off-hand proficiency
        if offhand and bool(getattr(attacker, "fighter_duelist_offhand_prof", False)):
            prof = base_prof

        # Monk off-hand proficiency rules
        if offhand and self._is_monk(attacker):
            if bool(getattr(attacker, "monk_offhand_prof_even_with_weapon", False)):
                prof = base_prof
            else:
                if self._both_unarmed(attacker):
                    prof = base_prof

        # Archer ranged +2 to hit
        style_bonus = 2 if (ranged and int(getattr(attacker, "fighter_archery_bonus", 0)) > 0) else 0

        ac = int(getattr(defender, "ac", 12))
        hit = (eff + mod + prof + style_bonus >= ac) or (eff == 20)
        return (hit, eff == 20, raw, eff, mod, prof, style_bonus)

    def _ranged_profile(self, f) -> Optional[Tuple[int, int, str, int, Tuple[int, int]]]:
        w = self._equipped_main(f)
        if isinstance(w, dict) and bool(w.get("ranged", False)):
            num, sides = _parse_dice(w.get("dice", "1d6"))
            ability = str(w.get("ability", "DEX")).upper()
            normal, longr = w.get("range", (8, 16))
            return (num, sides, ability, 1, (int(normal), int(longr)))
        return None

    def _do_melee_attack(self, attacker, defender, *, opportunity: bool, offhand: bool, force_unarmed: bool = False) -> bool:
        """
        Returns True if the strike was 'unarmed' (for Monk bonus logic).
        """
        if not (_alive(attacker) and _alive(defender)): return False

        item = None
        if force_unarmed:
            item = None
        else:
            item = self._equipped_off(attacker) if offhand else self._equipped_main(attacker)

        if offhand and not force_unarmed:
            if item is None or item.get("type") != "weapon":
                return False

        ranged = False; long_dis = False
        if not offhand and not force_unarmed:
            rp = self._ranged_profile(attacker)
            if rp is not None:
                ranged = True
                normal, longr = rp[-1]
                d = self.distance(attacker, defender)
                if d > longr:
                    self._push({"type": "attack", "actor": _name(attacker), "target": _name(defender), "hit": False,
                                "reason": "out_of_range", "ranged": True, "opportunity": opportunity,
                                "advantage": False, "disadvantage": False, "offhand": False})
                    return False
                long_dis = d > normal

        adv = 0
        if ranged:
            if long_dis: adv -= 1
            if self.distance(attacker, defender) <= self.reach(defender):
                adv -= 1

        hit, crit, raw, eff, mod, prof, style_bonus = self._attack_roll_with_item(attacker, defender, item, advantage=adv, ranged=ranged, offhand=offhand)
        self._push({"type": "attack", "actor": _name(attacker), "target": _name(defender), "ranged": ranged,
                    "opportunity": bool(opportunity), "critical": bool(crit), "hit": bool(hit),
                    "offhand": bool(offhand),
                    "advantage": isinstance(raw, tuple) and eff == max(raw) and adv > 0,
                    "disadvantage": isinstance(raw, tuple) and eff == min(raw) and adv < 0,
                    "eff_d20": eff, "mod": mod, "prof": prof, "style_bonus": style_bonus,
                    "total": eff + mod + prof + style_bonus})

        if not hit:
            return (item is None) or bool(item.get("unarmed", False))

        num, sides, ability, _ = self._weapon_profile_from_item(attacker, None if force_unarmed else item)

        # Enforcer two-handed damage advantage (main-hand only, melee, two-handed)
        twohand_item = bool((self._equipped_main(attacker) or {}).get("two_handed", False))
        enforcer = bool(getattr(attacker, "fighter_enforcer_twohand_adv", False))
        dmg_rolls = None
        if (not offhand) and enforcer and twohand_item and not ranged:
            r1 = _roll_dice(self.rng, num * (2 if crit else 1), sides)
            r2 = _roll_dice(self.rng, num * (2 if crit else 1), sides)
            base = max(r1, r2); dmg_rolls = [r1, r2]
        else:
            base = _roll_dice(self.rng, num * (2 if crit else 1), sides)

        if ability == "FINESSE":
            base += max(_ability_mod(attacker, "STR"), _ability_mod(attacker, "DEX"))
        else:
            base += _ability_mod(attacker, ("DEX" if ranged else ability))

        # mark if ranged weapon for Monk Deflect Missiles
        try:
            setattr(attacker, "_last_attack_ranged_weapon", bool(ranged))
        except Exception:
            pass

        if dmg_rolls is not None:
            setattr(attacker, "_dbg_rolls", dmg_rolls)
            setattr(attacker, "_dbg_twohand", True)

        self._apply_damage(attacker, defender, base)
        return (item is None) or bool(item.get("unarmed", False))

    # ---------- healing ----------
    def _do_heal(self, healer, target, dice: str, ability: str):
        num, sides = _parse_dice(dice)
        amt = _roll_dice(self.rng, num, sides) + max(0, _ability_mod(healer, ability))
        try:
            target.hp = min(int(getattr(target, "max_hp", getattr(target, "hp", 0))), int(getattr(target, "hp", 0)) + max(0, amt))
        except Exception: pass
        self._push({"type": "heal", "source": _name(healer), "target": _name(target), "amount": max(0, amt)})

    # ---------- spells ----------
    def _cast_spell_attack(self, caster, target, *, dice: str, ability: str,
                           normal_range: int, long_range: int, damage_type: Optional[str] = None):
        # To-hit roll
        adv = 0
        if self.distance(caster, target) > normal_range:
            if self.distance(caster, target) > long_range:
                self._push({"type":"attack","actor":_name(caster),"target":_name(target),"hit":False,
                            "reason":"out_of_range","ranged":True,"opportunity":False,"advantage":False,"disadvantage":False,"offhand":False})
                return
            adv -= 1
        raw, eff = _roll_d20(self.rng, max(-1, min(1, adv)))
        prof = _prof_for_level(getattr(caster, "level", 1))
        mod = _ability_mod(caster, ability)
        hit = (eff + prof + mod >= int(getattr(target, "ac", 12))) or (eff == 20)
        self._push({"type":"attack","actor":_name(caster),"target":_name(target),"ranged":True,"opportunity":False,
                    "critical": eff==20,"hit":bool(hit),"offhand":False,"eff_d20":eff,"mod":mod,"prof":prof,"style_bonus":0,
                    "total": eff+mod+prof})

        if not hit: return
        num, sides = _parse_dice(dice)
        dmg = _roll_dice(self.rng, num * (2 if eff==20 else 1), sides) + max(0, _ability_mod(caster, ability))
        self._apply_damage(caster, target, dmg, damage_type=damage_type)

    def _cast_spell_save(self, caster, target, *, save: str, dc: int, dice: str, ability: str,
                         half_on_success: bool, tags: Optional[List[str]], damage_type: Optional[str],
                         apply_condition_on_fail: Optional[Tuple[str, int]]):
        # Saving throw (with Monk globals / poison immunity)
        res = self.saving_throw(target, save, dc, tags=(tags or []))
        num, sides = _parse_dice(dice)
        base = _roll_dice(self.rng, num, sides) + max(0, _ability_mod(caster, ability))

        dmg = 0
        if save == "DEX" and bool(getattr(target, "monk_evasion", False)):
            if res["success"]:
                dmg = 0
            else:
                dmg = base // 2
        else:
            if res["success"]:
                dmg = (base // 2) if half_on_success else 0
            else:
                dmg = base

        self._apply_damage(caster, target, dmg, damage_type=damage_type)

        if (not res["success"]) and apply_condition_on_fail:
            cond_name, turns = apply_condition_on_fail
            add_condition(target, cond_name, turns)
            self._push({"type":"condition","target":_name(target),"condition":cond_name,"turns":int(turns)})

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
        if bool(getattr(actor, "monk_global_saves_adv", False)): ctx += 1  # L14

        # Poison immunity: auto success on poison saves
        if ("poison" in tags) and bool(getattr(actor, "poison_immune", False)):
            self._push({"type":"save","target":_name(actor),"ability":a,"roll":"IMMUNE","effective":99,
                        "modifier":0,"dc":int(dc),"success":True,"advantage":False,"disadvantage":False,"tags":tags})
            return {"success": True}

        consume = False
        try:
            if int(getattr(actor, "inspiration_tokens", 0)) > 0:
                ctx += 1; consume = True
        except Exception: pass
        raw, eff = _roll_d20(self.rng, max(-1, min(1, ctx)))
        if consume:
            try: setattr(actor, "inspiration_tokens", int(getattr(actor, "inspiration_tokens", 1)) - 1)
            except Exception: pass
        mod = _ability_mod(actor, a)
        success = eff + mod >= int(dc)
        self._push({"type": "save", "target": _name(actor), "ability": a, "roll": raw, "effective": eff,
                    "modifier": mod, "dc": int(dc), "success": bool(success),
                    "advantage": isinstance(raw, tuple) and eff == max(raw) and ctx > 0,
                    "disadvantage": isinstance(raw, tuple) and eff == min(raw) and ctx < 0,
                    "tags": tags})
        return {"success": success}

    # ---------- damage ----------
    def _apply_damage(self, attacker, defender, dmg: int, *, damage_type: Optional[str] = None):
        # Monk: Deflect Missiles (ranged weapon)
        try:
            if bool(getattr(attacker, "_last_attack_ranged_weapon", False)) and str(getattr(defender, "class", "")).capitalize() == "Monk":
                red = _roll_dice(self.rng, 1, 10) + _ability_mod(defender, "DEX") + int(getattr(defender, "level", 1))
                dmg = max(0, int(dmg) - int(red))
        except Exception:
            pass

        # Goblin bonus damage per level, Barbarian Rage bonus, resistances
        try:
            per_lvl = int(getattr(attacker, "dmg_bonus_per_level", 0))
            lvl = int(getattr(attacker, "level", getattr(attacker, "lvl", 1)))
            if per_lvl > 0 and lvl > 0:
                dmg = int(dmg) + per_lvl * lvl
        except Exception: pass
        try:
            if bool(getattr(attacker, "rage_active", False)) and int(getattr(attacker, "rage_bonus_per_level", 0)) > 0:
                lvl = int(getattr(attacker, "level", getattr(attacker, "lvl", 1)))
                dmg = int(dmg) + lvl * int(getattr(attacker, "rage_bonus_per_level", 0))
        except Exception: pass
        try:
            if bool(getattr(defender, "resist_all", False)):
                dmg = int(dmg) // 2
            elif damage_type and damage_type.lower() == "poison":
                if bool(getattr(defender, "poison_immune", False)):
                    dmg = 0
                elif getattr(defender, "poison_resist", False):
                    dmg = int(dmg) // 2
        except Exception: pass

        try:
            defender.hp = int(defender.hp) - int(dmg)
        except Exception: pass

        ev = {"type": "damage", "actor": _name(attacker), "target": _name(defender), "amount": int(dmg), "dtype": damage_type}
        rolls = getattr(attacker, "_dbg_rolls", None)
        if rolls is not None:
            ev["rolls"] = list(rolls); ev["twohand_adv"] = bool(getattr(attacker, "_dbg_twohand", False))
            try: delattr(attacker, "_dbg_rolls"); delattr(attacker, "_dbg_twohand")
            except Exception: pass
        self._push(ev)

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

    def path_step_towards(self, a, to_xy: Tuple[int, int]) -> Tuple[int, int]:
        ax, ay = getattr(a, "tx", 0), getattr(a, "ty", 0)
        tx, ty = map(int, to_xy)
        dx = 0 if ax == tx else (1 if tx > ax else -1)
        dy = 0 if ay == ty else (1 if ty > ay else -1)
        if dx != 0 and dy != 0:
            if abs(tx - ax) >= abs(ty - ay): dy = 0
            else: dx = 0
        return (ax + dx, ay + dy)
