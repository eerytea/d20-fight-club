# engine/tbcombat.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import random

# --------------------------------------------------------------------------------------
# Utility helpers
# --------------------------------------------------------------------------------------

def _mod(val: int) -> int:
    return (int(val) - 10) // 2

def _alive(f) -> bool:
    return bool(getattr(f, "alive", True)) and int(getattr(f, "hp", 1)) > 0

def _name(f) -> str:
    return getattr(f, "name", getattr(f, "id", "??"))

def _prof_for_level(level: int) -> int:
    L = max(1, int(level))
    return min(6, 2 + (L - 1) // 4)

def _roll_d20(rng: random.Random, adv_ctx: int = 0) -> Tuple[Tuple[int,int,int], int]:
    """
    adv_ctx: -1 = disadvantage, 0 = normal, +1 = advantage
    returns ((a,b,chosen), chosen)
    """
    a = rng.randint(1, 20)
    b = rng.randint(1, 20)
    if   adv_ctx > 0: return (a, b, max(a, b)), max(a, b)
    elif adv_ctx < 0: return (a, b, min(a, b)), min(a, b)
    else:             return (a, b, a), a

# --------------------------------------------------------------------------------------
# TBCombat
# --------------------------------------------------------------------------------------

class TBCombat:
    """
    Minimal battle loop with hooks for class features. Keep this in sync with your controllers.
    """
    def __init__(self, team_a, team_b, actors: List[Any], width: int, height: int, *, seed: int = 1):
        self.team_a = team_a
        self.team_b = team_b
        self.actors = actors[:]
        self.width = int(width); self.height = int(height)
        self.rng = random.Random(seed)
        self.turn_idx = 0
        self.winner: Optional[int] = None
        self.events: List[Dict[str, Any]] = []
        self.controllers: Dict[int, Any] = {}

    # ---------------------- Identity helpers ----------------------
    def _cls(self, f) -> str:
        return str(getattr(f, "class", getattr(f, "Class", ""))).capitalize()

    def _is_class(self, f, cls_name: str) -> bool:
        return self._cls(f) == cls_name

    def _is_ranger(self, f) -> bool: return self._is_class(f, "Ranger")
    def _is_monk(self, f) -> bool:   return self._is_class(f, "Monk")
    def _is_wizard(self, f) -> bool: return self._is_class(f, "Wizard")
    def _is_paladin(self, f) -> bool:return self._is_class(f, "Paladin")

    # ---------------------- Inventory helpers ----------------------
    def _equipped(self, f) -> Dict[str, Any]:
        return getattr(f, "equipped", {}) or {}

    def _inventory(self, f) -> Dict[str, Any]:
        return getattr(f, "inventory", {}) or {}

    def _equipped_main(self, f) -> Optional[Dict[str, Any]]:
        inv = self._inventory(f)
        weapons = inv.get("weapons", [])
        mid = self._equipped(f).get("main_hand_id")
        for w in weapons:
            if w.get("id") == mid: return w
        w = getattr(f, "weapon", None)
        return w if isinstance(w, dict) else None

    def _equipped_off(self, f) -> Optional[Dict[str, Any]]:
        inv = self._inventory(f)
        weapons = inv.get("weapons", [])
        oid = self._equipped(f).get("off_hand_id")
        for w in weapons:
            if w.get("id") == oid: return w
        return None

    def _has_shield_equipped(self, f) -> bool:
        return bool(self._equipped(f).get("shield_id"))

    def _weapon_profile_from_item(self, item: Optional[Dict[str, Any]]) -> Tuple[str, str, bool, int, bool, bool, str]:
        """
        returns: (dice, ability_stat, is_ranged, reach, finesse, versatile, two_handed_dice)
        """
        if not item:
            return ("1d4", "STR", False, 1, False, False, "")
        dice = str(item.get("dice", "1d4"))
        ability = str(item.get("ability", "STR")).upper()
        is_ranged = bool(item.get("ranged", False))
        reach = int(item.get("reach", 1))
        finesse = bool(item.get("finesse", False))
        versatile = bool(item.get("versatile", False))
        two_handed_dice = str(item.get("two_handed_dice", ""))
        return (dice, ability, is_ranged, reach, finesse, versatile, two_handed_dice)

    def _parse_dice(self, dice: str) -> Tuple[int, int]:
        n, s = str(dice).lower().split("d")
        return int(n), int(s)

    # ---------------------- Distance helpers ----------------------
    def _dist(self, a, b) -> int:
        return abs(getattr(a, "tx", 0) - getattr(b, "tx", 0)) + abs(getattr(a, "ty", 0) - getattr(b, "ty", 0))

    def _dist_to_xy(self, a, xy: Tuple[int,int]) -> int:
        x, y = xy
        return abs(getattr(a, "tx", 0) - x) + abs(getattr(a, "ty", 0) - y)

    # ---------------------- Range / reach ----------------------
    def reach(self, f) -> int:
        main = self._equipped_main(f)
        dice, ability, is_ranged, reach, finesse, versatile, two_handed_dice = self._weapon_profile_from_item(main)
        r = reach
        off = self._equipped_off(f)
        if off:
            _, _, _, r2, *_ = self._weapon_profile_from_item(off)
            r = max(r, r2)
        # Ranger 18: +1 melee reach
        if self._is_ranger(f) and int(getattr(f, "level", 1)) >= 18 and not (main and main.get("ranged")):
            r += 1
        return r

    def ranged_limits(self, f, item) -> Tuple[int, int]:
        if not item or not item.get("ranged"):
            return (1, 1)
        base = item.get("range", (8, 16))
        # Ranger 18: Unlimited range
        if self._is_ranger(f) and int(getattr(f, "level", 1)) >= 18:
            return (10**9, 10**9)
        return (int(base[0]), int(base[1]))

    # ---------------------- Stealth & detection (Ranger rules) ----------------------
    def _highest_enemy_passive_perception(self, f) -> int:
        enemies = [e for e in self.actors if _alive(e) and getattr(e, "team_id", -1) != getattr(f, "team_id", -2)]
        if not enemies: return 10
        return max(10 + _mod(getattr(e, "WIS", 10)) for e in enemies)

    def _attempt_hide(self, actor) -> Dict[str, Any]:
        raw, eff = _roll_d20(self.rng, 0)
        dex_mod = _mod(getattr(actor, "DEX", 10))
        bonus10 = 10 if (self._is_ranger(actor) and int(getattr(actor, "level", 1)) >= 10) else 0
        stealth_total = eff + dex_mod + bonus10
        dc = self._highest_enemy_passive_perception(actor)
        success = stealth_total >= dc
        setattr(actor, "hidden", bool(success))
        setattr(actor, "_hide_roll", int(stealth_total if success else 0))
        return {"type": "hide_attempt", "actor": _name(actor), "d20": eff, "dex_mod": dex_mod,
                "bonus10": bonus10, "stealth": stealth_total, "dc": dc, "success": success}

    def _start_of_turn_detect_hidden(self, detector):
        out = []
        for e in self.actors:
            if not _alive(e): continue
            if getattr(e, "team_id", -1) == getattr(detector, "team_id", -2): continue
            if not bool(getattr(e, "hidden", False)): continue
            raw, eff = _roll_d20(self.rng, 0)
            total = eff + _mod(getattr(detector, "WIS", 10))
            thr = int(getattr(e, "_hide_roll", 0) or 0)
            success = (thr > 0) and (total >= thr)
            out.append({"type": "detect_hidden", "detector": _name(detector), "target": _name(e),
                        "d20": eff, "wis_mod": _mod(getattr(detector, "WIS", 10)),
                        "total": total, "threshold": thr, "success": success})
            if success:
                setattr(e, "hidden", False)
                setattr(e, "_hide_roll", 0)
        return out

    # ---------------------- Paladin aura helpers ----------------------
    def _paladin_wis_aura_bonus(self, target) -> int:
        """
        Sum of CHA mods from friendly Paladins within their aura radius (non-stacking alternative: take max).
        Here we take the MAX, which tends to be cleaner.
        """
        tid = getattr(target, "team_id", -1)
        best = 0
        for p in self.actors:
            if not _alive(p) or not self._is_paladin(p): continue
            if getattr(p, "team_id", -2) != tid: continue
            radius = int(getattr(p, "pal_aura_radius", 0))
            if radius <= 0: continue
            if self._dist(p, target) <= radius:
                best = max(best, int(getattr(p, "pal_aura_wis_bonus", 0)))
        return best

    def _paladin_no_fear_aura_active(self, target) -> bool:
        tid = getattr(target, "team_id", -1)
        for p in self.actors:
            if not _alive(p) or not self._is_paladin(p): continue
            if getattr(p, "team_id", -2) != tid: continue
            if not bool(getattr(p, "pal_aura_no_fear", False)): continue
            if self._dist(p, target) <= int(getattr(p, "pal_aura_radius", 0)):
                return True
        return False

    # ---------------------- Attack roll & damage ----------------------
    def _attack_roll(self, attacker, defender, *, item: Optional[Dict[str, Any]] = None,
                     adv_ctx: int = 0, is_ranged: bool = False, offhand: bool = False) -> Tuple[bool, bool, int]:
        raw, eff = _roll_d20(self.rng, max(-1, min(1, adv_ctx)))

        # ability mod
        finesse = bool(item.get("finesse")) if item else False
        ability = "DEX" if (is_ranged or finesse) else (item.get("ability", "STR") if item else "STR")
        atk_mod = _mod(getattr(attacker, ability, 10))

        # proficiency to-hit
        prof = _prof_for_level(getattr(attacker, "level", 1))
        prof_to_hit = prof
        if offhand:
            prof_to_hit = 0
            # Fighter Duelist or Ranger (L2+) adds prof back to off-hand to-hit
            if getattr(attacker, "fighter_duelist_offhand_prof", False):
                prof_to_hit = prof
            if self._is_ranger(attacker) and int(getattr(attacker, "level", 1)) >= 2:
                prof_to_hit = prof

        # class/style bonuses
        style_bonus = 0
        if is_ranged and int(getattr(attacker, "fighter_archery_bonus", 0)) > 0:
            style_bonus += 2
        if is_ranged and self._is_ranger(attacker) and int(getattr(attacker, "level", 1)) >= 2:
            style_bonus += 2  # Ranger +2 ranged to-hit
        if self._is_ranger(attacker) and int(getattr(attacker, "level", 1)) >= 20:
            style_bonus += _mod(getattr(attacker, "WIS", 10))  # Ranger L20 add WIS to attack

        total = eff + atk_mod + prof_to_hit + style_bonus
        ac = int(getattr(defender, "ac", getattr(defender, "AC", 10)))
        hit = (total >= ac)
        crit = (eff == 20)
        self.events.append({
            "type": "attack_roll",
            "attacker": _name(attacker),
            "defender": _name(defender),
            "d20": eff,
            "ability_mod": atk_mod,
            "prof_to_hit": prof_to_hit,
            "style_bonus": style_bonus,
            "total": total,
            "ac": ac,
            "hit": hit,
            "crit": crit,
        })
        return hit, crit, eff

    def _is_two_handed_in_use(self, attacker, item: Dict[str, Any]) -> bool:
        """
        True if weapon is flagged two_handed OR it is versatile and attacker is not using a shield or off-hand.
        """
        if not item: return False
        if item.get("two_handed", False): return True
        if item.get("versatile", False) and (not self._has_shield_equipped(attacker)) and (self._equipped_off(attacker) is None):
            return True
        return False

    def _roll_damage_once(self, attacker, item: Dict[str, Any], *, is_ranged: bool, crit: bool, versatile_two_handed: bool) -> int:
        dice = str(item.get("dice", "1d6"))
        two_handed_dice = str(item.get("two_handed_dice", "")) if versatile_two_handed else ""
        if two_handed_dice:
            dice = two_handed_dice  # use 2H die for versatile weapons

        n, s = self._parse_dice(dice)
        dmg = 0
        for _ in range(n):
            dmg += self.rng.randint(1, s)
        if crit:
            for _ in range(n):
                dmg += self.rng.randint(1, s)

        # add ability mod
        finesse = bool(item.get("finesse"))
        ability = "DEX" if (is_ranged or finesse) else item.get("ability", "STR")
        dmg += _mod(getattr(attacker, ability, 10))

        # Global: proficiency bonus also adds to damage
        dmg += _prof_for_level(getattr(attacker, "level", 1))
        return max(0, dmg)

    def _weapon_damage_roll(self, attacker, item: Dict[str, Any], *, is_ranged: bool, crit: bool) -> int:
        # Paladin L2: damage-advantage when using two-handed (or versatile as 2H)
        versatile_two_handed = self._is_two_handed_in_use(attacker, item)
        if self._is_paladin(attacker) and int(getattr(attacker, "level", 1)) >= 2 and versatile_two_handed and not is_ranged:
            d1 = self._roll_damage_once(attacker, item, is_ranged=is_ranged, crit=crit, versatile_two_handed=True)
            d2 = self._roll_damage_once(attacker, item, is_ranged=is_ranged, crit=crit, versatile_two_handed=True)
            return max(d1, d2)
        # normal
        return self._roll_damage_once(attacker, item, is_ranged=is_ranged, crit=crit, versatile_two_handed=versatile_two_handed)

    # ---------------------- Spell/AOE helpers (Wizard) ----------------------
    def _apply_aoe_ally_exemptions(self, caster, targets: List[Any], center_xy: Tuple[int,int]) -> List[Any]:
        if not self._is_wizard(caster): return targets
        n = int(getattr(caster, "wiz_aoe_ally_exempt", 0))
        if n <= 0: return targets
        cx, cy = center_xy
        allies = [t for t in targets if getattr(t, "team_id", -1) == getattr(caster, "team_id", -2)]
        if not allies: return targets
        allies_sorted = sorted(allies, key=lambda a: abs(getattr(a,"tx",0)-cx)+abs(getattr(a,"ty",0)-cy))
        exempt = set(allies_sorted[:n])
        return [t for t in targets if t not in exempt]

    # ---------------------- Saving throws (Wizard/Paladin auras) ----------------------
    def _saving_throw(self, target, ability: str, dc: int, *, vs_condition: Optional[str] = None) -> bool:
        # Paladin L10 aura: immunity to frightened (if within radius)
        if vs_condition == "frightened" and self._paladin_no_fear_aura_active(target):
            self.events.append({"type":"saving_throw","target":_name(target),"ability":ability,"dc":dc,"auto":"paladin_no_fear"})
            return True

        adv = 0
        # Wizard L7: advantage on saves *against* blinded/deafened
        if vs_condition in ("blinded", "deafened") and bool(getattr(target, "wiz_adv_vs_blind_deaf", False)):
            adv = 1

        _, eff = _roll_d20(self.rng, adv)
        total = eff + _mod(getattr(target, ability.upper(), 10))

        # Paladin L6 aura: +CHA to WIS saves (use max aura bonus among nearby Paladins)
        if ability.upper() == "WIS":
            total += self._paladin_wis_aura_bonus(target)

        self.events.append({"type":"saving_throw","target":_name(target),"ability":ability,"d20":eff,"total":total,"dc":dc,"success":(total>=dc)})
        return total >= dc

    # ---------------------- Damage application (poison immunity hook) ----------------------
    def _apply_damage(self, target, amount: int, *, dtype: str = "physical") -> int:
        """
        dtype: "physical", "poison", "fire", etc. Paladin has full poison immunity (condition & damage).
        """
        if dtype == "poison" and bool(getattr(target, "poison_immune", False)):
            self.events.append({"type":"damage_ignored","target":_name(target),"dtype":"poison","amount":int(amount)})
            return 0
        new_hp = max(0, int(getattr(target, "hp", 0)) - int(amount))
        target.hp = new_hp
        if new_hp == 0: setattr(target, "alive", False)
        return amount

    # ---------------------- Turn loop ----------------------
    def _enemies_of(self, f):
        tid = getattr(f, "team_id", -1)
        return [e for e in self.actors if getattr(e, "team_id", -2) != tid]

    def take_turn(self) -> None:
        if self.winner is not None: return
        if self.turn_idx >= len(self.actors): self.turn_idx = 0
        actor = self.actors[self.turn_idx]
        if not _alive(actor):
            self.turn_idx += 1
            return

        # Start-of-turn: enemy detection of hidden units
        self.events.extend(self._start_of_turn_detect_hidden(actor))

        # Decide intents
        intents = []
        ctrl = self.controllers.get(getattr(actor, "team_id", 0))
        if ctrl and hasattr(ctrl, "decide"):
            try:
                intents = ctrl.decide(self, actor) or []
            except Exception:
                intents = []
        if not intents:
            intents = [{"type": "wait"}]

        # Execute intents
        for intent in intents:
            itype = intent.get("type")

            # -------------------- Hide --------------------
            if itype == "hide":
                self.events.append(self._attempt_hide(actor))

            # -------------------- Lay on Hands (Paladin) --------------------
            elif itype == "lay_on_hands" and self._is_paladin(actor):
                target = intent.get("target", actor)
                amount = max(0, int(intent.get("amount", 0)))
                pool = int(getattr(actor, "pal_lay_on_hands_current", 0))
                if amount <= 0 or pool <= 0:
                    self.events.append({"type":"loh","actor":_name(actor),"target":_name(target),"healed":0,"reason":"no_pool_or_zero_amount"})
                else:
                    heal = min(amount, pool)
                    target.hp = min(int(getattr(target, "max_hp", getattr(target, "hp", 1))), int(getattr(target, "hp", 0)) + heal)
                    actor.pal_lay_on_hands_current = pool - heal
                    self.events.append({"type":"loh","actor":_name(actor),"target":_name(target),"healed":int(heal),"pool_left":int(actor.pal_lay_on_hands_current)})

            # -------------------- Attack --------------------
            elif itype == "attack":
                target = intent.get("target")
                if not target or not _alive(target): continue
                main = self._equipped_main(actor)
                dice, ability, is_ranged, reach, finesse, versatile, two_handed_dice = self._weapon_profile_from_item(main)

                # Range check for ranged
                if is_ranged:
                    nr, lr = self.ranged_limits(actor, main)
                    dist = self._dist(actor, target)
                    # We allow shots beyond normal; if you want a hard cap, enforce dist <= lr.

                hit, crit, _ = self._attack_roll(actor, target, item=main, adv_ctx=0, is_ranged=is_ranged, offhand=False)
                if hit:
                    dmg = self._weapon_damage_roll(actor, main or {}, is_ranged=is_ranged, crit=crit)

                    # -------------------- Paladin Smite-like Proc --------------------
                    if not is_ranged and self._is_paladin(actor):
                        L = int(getattr(actor, "level", 1))
                        chance = float(getattr(actor, "pal_smite_chance", 0.0))
                        nd6 = int(getattr(actor, "pal_smite_nd6", 0))
                        if nd6 > 0 and self.rng.random() < chance:
                            # roll extra nd6 (NOT doubled on crit)
                            extra = sum(self.rng.randint(1, 6) for _ in range(nd6))
                            dmg += extra
                            self.events.append({"type":"pal_smite","attacker":_name(actor),"defender":_name(target),"nd6":nd6,"extra":int(extra),"chance":chance})

                    dealt = self._apply_damage(target, dmg, dtype="physical")
                    self.events.append({"type":"damage","attacker":_name(actor),"defender":_name(target),"amount":int(dealt),"crit":bool(crit)})

                    # Paladin Extra Attack L5: controller should issue multiple 'attack' intents;
                    # if your controller doesn't, you could auto-queue an extra attack here.
                    # Example (simple auto-extra):
                    if self._is_paladin(actor) and int(getattr(actor, "level", 1)) >= 5:
                        # A very conservative auto second swing at same target (optional).
                        # Comment out if your controller already handles extra attacks.
                        hit2, crit2, _ = self._attack_roll(actor, target, item=main, adv_ctx=0, is_ranged=is_ranged, offhand=False)
                        if hit2 and _alive(target):
                            dmg2 = self._weapon_damage_roll(actor, main or {}, is_ranged=is_ranged, crit=crit2)
                            # Smite proc can trigger on each hit independently
                            if not is_ranged:
                                L = int(getattr(actor, "level", 1))
                                chance = float(getattr(actor, "pal_smite_chance", 0.0))
                                nd6 = int(getattr(actor, "pal_smite_nd6", 0))
                                if nd6 > 0 and self.rng.random() < chance:
                                    extra2 = sum(self.rng.randint(1, 6) for _ in range(nd6))
                                    dmg2 += extra2
                                    self.events.append({"type":"pal_smite","attacker":_name(actor),"defender":_name(target),"nd6":nd6,"extra":int(extra2),"chance":chance})
                            dealt2 = self._apply_damage(target, dmg2, dtype="physical")
                            self.events.append({"type":"damage","attacker":_name(actor),"defender":_name(target),"amount":int(dealt2),"crit":bool(crit2),"extra_attack":True})

            # -------------------- Cast (very lightweight scaffolding) --------------------
            elif itype == "cast":
                spell = intent.get("spell", {})
                target = intent.get("target")
                tag = spell.get("tag", "attack")
                name = spell.get("name", "Spell")
                level = int(spell.get("level", 0))

                # Spend a slot (1..9 only; cantrips are 0)
                if level >= 1:
                    slots = getattr(actor, "spell_slots_current", None)
                    if slots is not None and len(slots) > level and slots[level] > 0:
                        slots[level] -= 1

                if spell.get("attack_roll", False) and target:
                    hit, crit, _ = self._attack_roll(actor, target, item=None, adv_ctx=0, is_ranged=True, offhand=False)
                    if hit and _alive(target):
                        # Cantrip-like scaling via tier
                        tier = int(getattr(actor, "wiz_cantrip_tier", 1))
                        dmg = self.rng.randint(1, 10) * tier
                        dealt = self._apply_damage(target, dmg, dtype="fire")
                        self.events.append({"type":"spell_hit","name":name,"attacker":_name(actor),"defender":_name(target),"dmg":int(dealt),"tier":tier})
                elif spell.get("center"):
                    # crude AOE: affect everyone alive, then exempt allies for Wizards
                    cx, cy = spell["center"]
                    candidates = [t for t in self.actors if _alive(t)]
                    targets = self._apply_aoe_ally_exemptions(actor, candidates, (cx, cy))
                    dc = int(spell.get("dc_override", getattr(actor, "spell_save_dc", 10)))
                    for t in targets:
                        if getattr(t, "team_id", -1) == getattr(actor, "team_id", -2):  # skip allies after exemption
                            continue
                        saved = self._saving_throw(t, "DEX", dc, vs_condition=None)
                        dmg = self.rng.randint(1, 6) * (2 if level >= 3 else 1)
                        if saved: dmg //= 2
                        dealt = self._apply_damage(t, dmg, dtype="fire")
                        self.events.append({"type":"spell_aoe","name":name,"attacker":_name(actor),"defender":_name(t),"dmg":int(dealt),"saved":bool(saved)})
                else:
                    # single-target save/control example
                    if target:
                        dc = int(spell.get("dc_override", getattr(actor, "spell_save_dc", 10)))
                        saved = self._saving_throw(target, "WIS", dc, vs_condition=spell.get("vs_condition"))
                        if not saved:
                            setattr(target, "_controlled", True)
                            self.events.append({"type":"spell_control","name":name,"attacker":_name(actor),"defender":_name(target),"applied":True})

            # -------------------- Other intents (move/wait/etc.) --------------------
            else:
                # keep your original handlers here if you have them
                pass

        # Advance pointer
        self.turn_idx = (self.turn_idx + 1) % len(self.actors)
