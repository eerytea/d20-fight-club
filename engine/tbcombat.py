# engine/tbcombat.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import random

# ... (all your existing imports / constants remain unchanged)

# Utility functions (unchanged where not shown)
def _ability_mod(f, ability: str) -> int:
    try:
        return (int(getattr(f, ability, 10)) - 10) // 2
    except Exception:
        try:
            return (int(f.get(ability, 10)) - 10) // 2
        except Exception:
            return 0

def _prof_for_level(level: int) -> int:
    # Same progression as before
    lvl = int(level)
    if   lvl <= 4:  return 2
    elif lvl <= 8:  return 3
    elif lvl <= 12: return 4
    elif lvl <= 16: return 5
    else:           return 6

def _name(f) -> str:
    return getattr(f, "name", getattr(f, "id", "??"))

def _alive(f) -> bool:
    return bool(getattr(f, "alive", True)) and int(getattr(f, "hp", 1)) > 0

def _roll_d20(rng: random.Random, ctx: int = 0) -> Tuple[Tuple[int,int,int], int]:
    # ctx: -1 disadvantage, 0 normal, +1 advantage
    a = rng.randint(1, 20); b = rng.randint(1, 20)
    if ctx > 0:
        return (a, b, max(a, b)), max(a, b)
    elif ctx < 0:
        return (a, b, min(a, b)), min(a, b)
    else:
        return (a, b, a), a

def _parse_dice(spec: str) -> Tuple[int, int]:
    # "1d8" -> (1, 8)
    n, s = spec.lower().split("d")
    return int(n), int(s)

# TBCombat class (only sections shown are changed or nearby)
class TBCombat:
    # ... __init__ unchanged ...

    def _is_monk(self, f) -> bool:
        return str(getattr(f, "class", "")).capitalize() == "Monk"
    def _is_rogue(self, f) -> bool:
        return str(getattr(f, "class", "")).capitalize() == "Rogue"
    def _is_ranger(self, f) -> bool:
        return str(getattr(f, "class", "")).capitalize() == "Ranger"

    def reach(self, a) -> int:
        main = self._equipped_main(a)
        off = self._equipped_off(a)
        r1 = self._weapon_profile_from_item(a, main)[3]
        r2 = 0
        if off and off.get("type") == "weapon":
            r2 = self._weapon_profile_from_item(a, off)[3]
        res = max(r1, r2)
        # Ranger L18: +1 melee reach
        if self._is_ranger(a) and int(getattr(a, "level", 1)) >= 18:
            res = res + 1
        return res

    def _ranged_profile(self, f) -> Optional[Tuple[int, int, str, int, Tuple[int, int]]]:
        w = self._equipped_main(f)
        if isinstance(w, dict) and bool(w.get("ranged", False)):
            num, sides = _parse_dice(w.get("dice", "1d6"))
            ability = str(w.get("ability", "DEX")).upper()
            normal, longr = w.get("range", (8, 16))
            # Ranger L18: unlimited range, no long-range disadvantage
            if self._is_ranger(f) and int(getattr(f, "level", 1)) >= 18:
                return (num, sides, ability, 1, (10**9, 10**9))
            return (num, sides, ability, 1, (int(normal), int(longr)))
        return None

    def _attack_roll_with_item(self, attacker, defender, weapon_item: Optional[Dict[str, Any]],
                               *, advantage: int = 0, ranged: bool = False,
                               offhand: bool = False) -> Tuple[bool, bool, Any, int, int, int, int]:
        ctx = advantage

        # Rogue 18: no advantage against me
        if self._is_rogue(defender) and int(getattr(defender, "level", 1)) >= 18:
            ctx = min(ctx, 0)

        # Inspiration / Dodge / Conditions
        consume_token = False
        try:
            if int(getattr(attacker, "inspiration_tokens", 0)) > 0:
                ctx += 1
                consume_token = True
        except Exception:
            pass
        if getattr(defender, "_status_dodging", False):
            ctx -= 1

        raw, eff = _roll_d20(self.rng, max(-1, min(1, ctx)))
        base_prof = _prof_for_level(getattr(attacker, "level", 1))
        # Off-hand normally does not add proficiency to hit; add for Ranger L2+
        prof = base_prof if not offhand else 0
        if offhand and self._is_ranger(attacker) and int(getattr(attacker, "level", 1)) >= 2:
            prof = base_prof

        # Ability mod
        ability = "DEX" if ranged else (str(weapon_item.get("ability", "STR")).upper() if weapon_item else "STR")
        mod = _ability_mod(attacker, ability)

        # Style / class bonuses: Fighter Archery, plus Ranger perks
        style_bonus = 2 if (ranged and int(getattr(attacker, "fighter_archery_bonus", 0)) > 0) else 0
        # Ranger L2: +2 to all ranged attack rolls
        if ranged and self._is_ranger(attacker) and int(getattr(attacker, "level", 1)) >= 2:
            style_bonus += 2
        # Ranger L20: add WIS mod to attack rolls
        if self._is_ranger(attacker) and int(getattr(attacker, "level", 1)) >= 20:
            style_bonus += _ability_mod(attacker, "WIS")

        # compute target AC
        ac = int(getattr(defender, "ac", getattr(defender, "AC", 10)))

        total = eff + mod + prof + style_bonus
        hit = total >= ac
        crit = (eff == 20)

        # consume inspiration if we used it
        if consume_token and int(getattr(attacker, "inspiration_tokens", 0)) > 0:
            attacker.inspiration_tokens -= 1

        return hit, crit, raw, eff, mod, prof, style_bonus

    def _do_melee_attack(self, attacker, target, *, opportunity=False, offhand=False, force_unarmed=False, ranged=False) -> bool:
        # … snip setup and weapon selection …

        # Attack roll
        hit, crit, raw, eff, mod, prof, style_bonus = self._attack_roll_with_item(attacker, target, weapon,
                                                                                   advantage=adv_ctx,
                                                                                   ranged=ranged, offhand=offhand)

        # Build base damage from weapon dice
        num, sides = _parse_dice(weapon.get("dice", "1d6"))
        base = self.rng.randint(1, sides)
        for _ in range(num - 1):
            base += self.rng.randint(1, sides)

        # Add ability mod to damage (usual rule)
        base += _ability_mod(attacker, "DEX" if ranged or bool(weapon.get("finesse", False)) else "STR")

        # Rogue Sneak Attack (if hidden at start and finesse/ranged)
        base += self._rogue_sneak_bonus(attacker, weapon, ranged=ranged)

        # Global retrofit: add proficiency bonus to weapon damage (main and off-hand)
        base += _prof_for_level(getattr(attacker, "level", getattr(attacker, "lvl", 1)))

        # Apply crit doubling of dice (not modifiers)
        if crit:
            base += self.rng.randint(1, sides) * num

        # … call _apply_damage, push attack event etc. (unchanged except totals include the new pieces) …

        # return whether we used unarmed (existing logic)
        return bool(weapon.get("unarmed", False))

    def take_turn(self) -> None:
        if self.winner is not None:
            return

        actor = self._initiative[self.turn_idx]
        if not _alive(actor):
            self._advance_pointer(actor)
            return

        # Start-of-turn housekeeping
        self._push({"type": "turn_start", "actor": _name(actor)})

        # Clear one-turn statuses
        if getattr(actor, "_status_disengage", False):
            setattr(actor, "_status_disengage", False)
        if getattr(actor, "_status_dodging", False):
            setattr(actor, "_status_dodging", False)

        # NEW: detect hidden enemies at start of this actor’s turn
        # Wisdom check vs each hidden unit's stored hide roll
        for e in list(self._enemies_of(actor)):
            if _alive(e) and bool(getattr(e, "hidden", False)):
                raw, eff = _roll_d20(self.rng, 0)
                mod = _ability_mod(actor, "WIS")
                total = eff + mod
                thr = int(getattr(e, "_hide_roll", 0) or 0)
                success = (thr > 0) and (total >= thr)
                self._push({"type": "detect_hidden",
                            "detector": _name(actor), "target": _name(e),
                            "roll": raw, "effective": eff, "wis_mod": mod,
                            "total": total, "threshold": thr, "success": bool(success)})
                if success:
                    setattr(e, "hidden", False)
                    setattr(e, "_hide_roll", 0)

        # … initiative / AI intent selection unchanged …

        # Intent execution loop (only modified the "hide" branch)
        for intent in intents:
            t = intent.get("type")
            # … other intents …
            if t == "hide":
                # Hide = DEX check against highest enemy passive Perception (10 + WIS)
                enemies = [e for e in self._enemies_of(actor) if _alive(e)]
                dc = max([10 + _ability_mod(e, "WIS") for e in enemies], default=10)
                # Ranger L10: +10 to hide checks
                bonus10 = 10 if (self._is_ranger(actor) and int(getattr(actor, "level", 1)) >= 10) else 0
                raw, eff = _roll_d20(self.rng, 0)
                stealth = eff + _ability_mod(actor, "DEX") + bonus10
                success = stealth >= dc
                setattr(actor, "hidden", bool(success))
                setattr(actor, "_hide_roll", int(stealth if success else 0))
                self._push({"type": "hide_attempt",
                            "actor": _name(actor), "roll": raw, "effective": eff,
                            "dex_mod": _ability_mod(actor, "DEX"), "bonus10": bonus10,
                            "stealth": stealth, "dc": int(dc), "success": bool(success)})
            # … rest of intents unchanged …

        # … end turn, advance pointer, etc. unchanged …
